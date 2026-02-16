import json
import os
from typing import Any

from app.config import settings


class AnthropicClient:
    def __init__(self, model: str | None = None):
        self._model = model or settings.llm.sonnet_model
        self._client = None
        self._langfuse = None
        self._init_langfuse()

    def _init_langfuse(self):
        if os.getenv("LANGFUSE_PUBLIC_KEY"):
            try:
                from langfuse import Langfuse

                self._langfuse = Langfuse()
            except ImportError:
                pass

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic()
        return self._client

    def complete(self, prompt: str, trace_name: str) -> dict[str, Any]:
        cfg = settings.llm
        generation = None
        if self._langfuse:
            generation = self._langfuse.start_observation(
                as_type="generation",
                name=trace_name,
                input=prompt,
                model=self._model,
                metadata={"provider": "anthropic"},
            )

        try:
            client = self._get_client()
            resp = client.messages.create(
                model=self._model,
                max_tokens=cfg.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text
            result = json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            result = {"error": str(e), "raw_response": raw if "raw" in dir() else ""}

        if generation:
            generation.update(output=result)
            generation.end()

        return result
