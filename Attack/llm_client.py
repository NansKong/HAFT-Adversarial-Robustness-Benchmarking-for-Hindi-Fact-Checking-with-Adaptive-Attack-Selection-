"""Provider-agnostic LLM client for attack generation and verification.

Configured entirely through environment variables so the same code runs
against Groq, OpenAI, Replicate, or any OpenAI-compatible endpoint:

    LLM_BASE_URL   e.g. https://api.groq.com/openai/v1  (or https://api.replicate.com/v1)
    LLM_API_KEY    API key
    LLM_MODEL      e.g. llama-3.1-8b-instant (Groq) or openai/gpt-4o-mini (Replicate)
    LLM_TIMEOUT    seconds per request (default 120)
    LLM_MAX_RETRIES attempts after a failure (default 3)

Every raw request/response pair is appended to a JSONL audit log (the
project's "Logger" role) so each call is auditable.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Load .env into os.environ (env vars already set always win).
try:
    from dotenv_loader import load_dotenv
    load_dotenv()
except Exception:  # noqa: BLE001 — .env is best-effort convenience
    pass


class LLMClientError(RuntimeError):
    pass


class _ReplicateMessage:
    def __init__(self, content: str):
        self.content = content


class _ReplicateChoice:
    def __init__(self, content: str):
        self.message = _ReplicateMessage(content)


class ReplicateResponse:
    def __init__(self, content: str, id_str: str = ""):
        self.id = id_str
        self.choices = [_ReplicateChoice(content)]


def _require_openai():
    if OpenAI is None:
        raise LLMClientError(
            "openai package not installed; run: pip install openai"
        )


class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None,
                 timeout=None, max_retries=None, log_path=None,
                 mock=False, mock_fn=None, temperature=0.7):
        self.base_url = base_url or os.environ.get("LLM_BASE_URL")
        self.api_key = api_key or os.environ.get("LLM_API_KEY")
        self.model = model or os.environ.get("LLM_MODEL")
        self.timeout = float(timeout or os.environ.get("LLM_TIMEOUT", "120"))
        self.max_retries = int(max_retries or os.environ.get("LLM_MAX_RETRIES", "3"))
        self.log_path = log_path or os.environ.get("LLM_AUDIT_LOG", "llm_audit.jsonl")
        self.mock = mock
        self.mock_fn = mock_fn  # callable(prompt, system) -> str, used in mock mode
        self.temperature = temperature
        self._client = None
        self.is_replicate = False
        self._log_lock = threading.Lock()

        if not self.mock:
            if not self.base_url or not self.api_key or not self.model:
                raise LLMClientError(
                    "LLM_BASE_URL, LLM_API_KEY and LLM_MODEL must be set "
                    "(or pass base_url/api_key/model explicitly)"
                )
            self.is_replicate = "replicate.com" in self.base_url.lower()
            if not self.is_replicate:
                _require_openai()
                self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    # -- public API ---------------------------------------------------------

    def complete(self, prompt, system=None, max_tokens=None, temperature=None):
        """Run one chat completion with retry/backoff. Returns the text.

        Raises LLMClientError after self.max_retries failed attempts.
        """
        request = {
            "model": self.model,
            "messages": [],
        }
        if system:
            request["messages"].append({"role": "system", "content": system})
        request["messages"].append({"role": "user", "content": prompt})
        if max_tokens:
            request["max_tokens"] = max_tokens
        request["temperature"] = temperature if temperature is not None else self.temperature

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._do_call(request)
                self._audit(request, response, ok=True)
                return self._extract_text(response)
            except Exception as exc:  # noqa: BLE001 — retry any transport/API error
                self._audit(request, None, ok=False, error=str(exc))
                exc_str = str(exc).lower()
                if "rate_limit" in exc_str or "rate limit" in exc_str or "429" in exc_str or "tpd" in exc_str:
                    # Rate limit hit: wait 60s without consuming standard attempt limit
                    print(f"[llm] Rate limit hit ({exc}); waiting 60s before retry...", file=sys.stderr)
                    time.sleep(60)
                elif attempt >= self.max_retries:
                    raise LLMClientError(f"LLM call failed after {attempt} attempts: {exc}")
                else:
                    delay = min(2 ** attempt, 30)
                    print(f"[llm] attempt {attempt} failed ({exc}); retrying in {delay}s",
                          file=sys.stderr)
                    time.sleep(delay)

    # -- internals ----------------------------------------------------------

    def _do_call(self, request):
        if self.mock:
            content = (
                self.mock_fn(request["messages"][-1]["content"])
                if self.mock_fn
                else "MOCK: " + request["messages"][-1]["content"]
            )
            return {
                "id": "mock-" + uuid.uuid4().hex[:8],
                "choices": [{"message": {"content": content}}],
            }
        if self.is_replicate:
            return self._do_replicate_call(request)
        return self._client.chat.completions.create(**request)

    def _do_replicate_call(self, request):
        url = f"https://api.replicate.com/v1/models/{self.model}/predictions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait=60",
        }

        prompt_text = request["messages"][-1]["content"] if request.get("messages") else ""
        system_text = ""
        for m in request.get("messages", []):
            if m.get("role") == "system":
                system_text = m.get("content", "")

        input_data = {
            "messages": request["messages"],
            "prompt": prompt_text,
            "temperature": request.get("temperature", 0.7),
        }
        if system_text:
            input_data["system_prompt"] = system_text
        if request.get("max_tokens"):
            input_data["max_tokens"] = request["max_tokens"]
            input_data["max_completion_tokens"] = request["max_tokens"]

        payload = json.dumps({"input": input_data}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"Replicate HTTP {exc.code}: {err_body}") from exc

        # Handle polling if prediction is still processing/starting
        status = res_data.get("status")
        get_url = res_data.get("urls", {}).get("get")
        start_time = time.time()

        while status in ("starting", "processing"):
            if time.time() - start_time > self.timeout:
                raise LLMClientError("Replicate prediction timed out")
            time.sleep(0.2)
            if not get_url:
                break
            poll_req = urllib.request.Request(
                get_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                method="GET",
            )
            try:
                with urllib.request.urlopen(poll_req, timeout=self.timeout) as presp:
                    res_data = json.loads(presp.read().decode("utf-8"))
                    status = res_data.get("status")
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode("utf-8", errors="replace")
                raise LLMClientError(f"Replicate polling HTTP {exc.code}: {err_body}") from exc

        if res_data.get("status") == "failed" or res_data.get("error"):
            raise LLMClientError(f"Replicate prediction failed: {res_data.get('error')}")

        output = res_data.get("output", "")
        if isinstance(output, list):
            text = "".join(str(chunk) for chunk in output)
        else:
            text = str(output or "")

        return ReplicateResponse(content=text, id_str=res_data.get("id", ""))

    @staticmethod
    def _strip_thinking(text):
        """Reasoning models (e.g. Qwen) wrap their chain-of-thought in
        <think>...</think>. Keep only the final answer after the block."""
        if not text:
            return text
        if "</think>" in text:
            return text.split("</think>", 1)[1].strip()
        if "<think>" in text:
            return ""  # truncated reasoning, no final answer yet
        return text

    @staticmethod
    def _extract_text(response):
        try:
            content = response.choices[0].message.content
            return LLMClient._strip_thinking(content or "")
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMClientError(f"malformed response: {exc}")

    def _audit(self, request, response, ok, error=None):
        entry = {
            "ts": time.time(),
            "request_id": uuid.uuid4().hex,
            "provider": "mock" if self.mock else (self.base_url or "unknown"),
            "model": self.model,
            "request": request,
            "response": response,
            "ok": ok,
            "error": error,
        }
        try:
            with self._log_lock:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass  # audit log must never break the pipeline

