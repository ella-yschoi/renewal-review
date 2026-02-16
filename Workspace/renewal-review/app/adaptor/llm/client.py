from typing import Any

from app.config import settings
from app.domain.ports.llm import LLMPort


def create_llm_client() -> LLMPort:
    if settings.llm_provider == "anthropic":
        from app.adaptor.llm.anthropic import AnthropicClient

        return AnthropicClient()

    from app.adaptor.llm.openai import OpenAIClient

    return OpenAIClient()


class LLMClient:
    def __init__(self):
        self._delegate = create_llm_client()

    def complete(self, prompt: str, trace_name: str) -> dict[str, Any]:
        return self._delegate.complete(prompt, trace_name)
