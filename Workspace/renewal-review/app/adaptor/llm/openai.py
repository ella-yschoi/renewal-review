import json
import os
from typing import Any

from app.config import settings


class OpenAIClient:
    def __init__(self, model: str | None = None):
        self._model = model or settings.llm.openai_model
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
            from openai import OpenAI

            self._client = OpenAI()
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
                metadata={"provider": "openai"},
            )

        try:
            client = self._get_client()
            resp = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=cfg.temperature,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content
            result = json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            result = {"error": str(e), "raw_response": raw if "raw" in dir() else ""}

        if generation:
            generation.update(output=result)
            generation.end()

        return result
