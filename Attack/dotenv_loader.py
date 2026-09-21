"""Minimal .env loader — no external dependencies.

Reads KEY=VALUE pairs from the project's .env file into os.environ if the
variable isn't already set (real env vars always win). Lines starting with
# are comments; inline # comments and quotes are stripped.
"""

from __future__ import annotations

import os

_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def load_dotenv(path=None):
    path = path or _ENV_PATH
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            else:
                value = value.split("#", 1)[0].strip()
            if key and key not in os.environ:
                os.environ[key] = value
    return True
