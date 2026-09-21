"""List the models your configured API key can access."""

from llm_client import LLMClient


def main():
    c = LLMClient()
    if c.mock:
        print("client is in mock mode; cannot list models")
        return
    try:
        models = c._client.models.list()
        ids = sorted(m.id for m in models.data)
        for mid in ids:
            print(mid)
        print(f"\n{len(ids)} models available to this key")
    except Exception as exc:  # noqa: BLE001
        print(f"error listing models: {exc}")


if __name__ == "__main__":
    main()
