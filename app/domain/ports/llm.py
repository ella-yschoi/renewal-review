from typing import Any, Protocol


class LLMPort(Protocol):
    def complete(self, prompt: str, trace_name: str) -> dict[str, Any]: ...
