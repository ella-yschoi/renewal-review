from typing import Any

from app.config import ModelKey, settings
from app.domain.ports.llm import LLMPort


class LLMClient:
    def __init__(self):
        self._clients: dict[str, LLMPort] = {}

    def _get_client(self, model: str) -> LLMPort:
        if model not in self._clients:
            from app.adaptor.llm.anthropic import AnthropicClient

            self._clients[model] = AnthropicClient(model=model)
        return self._clients[model]

    def complete(self, prompt: str, trace_name: str) -> dict[str, Any]:
        cfg = settings.llm
        model_key = cfg.task_models.get(trace_name, ModelKey.HAIKU)
        model_map = {
            ModelKey.SONNET: cfg.sonnet_model,
            ModelKey.HAIKU: cfg.haiku_model,
        }
        model = model_map.get(model_key, cfg.haiku_model)
        return self._get_client(model).complete(prompt, trace_name)
