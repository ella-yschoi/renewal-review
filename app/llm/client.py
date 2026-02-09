import json
import os
from typing import Any, Protocol

from app.config import settings


class LLMClientProtocol(Protocol):
    def complete(self, prompt: str, trace_name: str) -> dict[str, Any]: ...


class LLMClient:
    def __init__(self):
        self.provider = settings.llm_provider
        self._openai_client = None
        self._anthropic_client = None
        self._langfuse = None
        self._init_langfuse()

    def _init_langfuse(self):
        if os.getenv("LANGFUSE_PUBLIC_KEY"):
            try:
                from langfuse import Langfuse

                self._langfuse = Langfuse()
            except ImportError:
                pass

    def _get_openai(self):
        if self._openai_client is None:
            from openai import OpenAI

            self._openai_client = OpenAI()
        return self._openai_client

    def _get_anthropic(self):
        if self._anthropic_client is None:
            from anthropic import Anthropic

            self._anthropic_client = Anthropic()
        return self._anthropic_client

    def complete(self, prompt: str, trace_name: str) -> dict[str, Any]:
        trace = None
        generation = None
        if self._langfuse:
            trace = self._langfuse.trace(name=trace_name)
            generation = trace.generation(name=trace_name, input=prompt)

        try:
            raw = self._call_provider(prompt)
            result = json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            result = {"error": str(e), "raw_response": raw if "raw" in dir() else ""}

        if generation:
            generation.end(output=result)
        if self._langfuse:
            self._langfuse.flush()

        return result

    def _call_provider(self, prompt: str) -> str:
        if self.provider == "anthropic":
            client = self._get_anthropic()
            resp = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text

        client = self._get_openai()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content
