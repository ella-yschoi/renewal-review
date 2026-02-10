import os
from typing import Any


class MockLLMClient:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self._langfuse = None
        if os.getenv("LANGFUSE_PUBLIC_KEY"):
            try:
                from langfuse import Langfuse

                self._langfuse = Langfuse()
            except ImportError:
                pass

    def complete(self, prompt: str, trace_name: str) -> dict[str, Any]:
        self.calls.append((prompt, trace_name))
        result = self._mock_response(trace_name)

        if self._langfuse:
            gen = self._langfuse.start_observation(
                as_type="generation",
                name=trace_name,
                input=prompt,
                model="mock",
                metadata={"provider": "mock"},
            )
            gen.update(output=result)
            gen.end()

        return result

    def _mock_response(self, trace_name: str) -> dict[str, Any]:
        if trace_name == "risk_signal_extractor":
            return {
                "signals": [
                    {
                        "signal_type": "claims_history",
                        "description": "Prior water damage claim noted in file",
                        "severity": "high",
                    },
                    {
                        "signal_type": "property_condition",
                        "description": "Aging roof mentioned — replacement overdue",
                        "severity": "medium",
                    },
                ],
                "confidence": 0.88,
                "summary": "Multiple risk indicators found in policy notes",
            }

        if trace_name == "endorsement_comparison":
            return {
                "material_change": True,
                "change_type": "restriction",
                "confidence": 0.8,
                "reasoning": "Coverage scope narrowed in renewal",
            }

        if trace_name == "coverage_similarity":
            return {
                "equivalent": False,
                "confidence": 0.9,
                "reasoning": "Coverage removed entirely",
            }

        return {"error": "unknown prompt"}
