from typing import Any

from app.config import settings
from app.domain.ports.llm import LLMPort

_MODEL_KEY_TO_PROVIDER = {
    "sonnet": "anthropic",
    "haiku": "anthropic",
    "openai": "openai",
}


def _resolve_model(key: str) -> tuple[str, str]:
    cfg = settings.llm
    model_map = {
        "sonnet": cfg.sonnet_model,
        "haiku": cfg.haiku_model,
        "openai": cfg.openai_model,
    }
    provider = _MODEL_KEY_TO_PROVIDER.get(key, "anthropic")
    model = model_map.get(key, cfg.haiku_model)
    return provider, model


def _create_client(provider: str, model: str) -> LLMPort:
    if provider == "anthropic":
        from app.adaptor.llm.anthropic import AnthropicClient

        return AnthropicClient(model=model)

    from app.adaptor.llm.openai import OpenAIClient

    return OpenAIClient(model=model)


class LLMClient:
    def __init__(self):
        self._clients: dict[tuple[str, str], LLMPort] = {}

    def _get_client(self, provider: str, model: str) -> LLMPort:
        key = (provider, model)
        if key not in self._clients:
            self._clients[key] = _create_client(provider, model)
        return self._clients[key]

    def complete(self, prompt: str, trace_name: str) -> dict[str, Any]:
        model_key = settings.llm.task_models.get(trace_name, "haiku")
        provider, model = _resolve_model(model_key)
        return self._get_client(provider, model).complete(prompt, trace_name)


def create_llm_client() -> LLMPort:
    return LLMClient()
