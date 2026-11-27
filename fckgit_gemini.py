"""Gemini configuration shared by the CLI and MCP tools."""

import os
from functools import lru_cache

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class GeminiConfigurationError(RuntimeError):
    pass


def get_client():
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not key.strip():
        raise GeminiConfigurationError(
            "Set GEMINI_API_KEY in the environment or .env to generate commit messages."
        )
    return _client_for_key(key)


@lru_cache(maxsize=1)
def _client_for_key(key):
    try:
        from google import genai
    except ImportError as exc:
        raise GeminiConfigurationError("Install google-genai to generate commit messages.") from exc
    return genai.Client(api_key=key)
