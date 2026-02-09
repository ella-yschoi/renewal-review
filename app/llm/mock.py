from typing import Any


class MockLLMClient:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def complete(self, prompt: str, trace_name: str) -> dict[str, Any]:
        self.calls.append((prompt, trace_name))

        if trace_name == "risk_signal_extractor":
            return {
                "signals": [
                    {
                        "signal_type": "claims_history",
                        "description": "Water damage claim noted",
                        "severity": "medium",
                    }
                ],
                "confidence": 0.85,
                "summary": "Moderate risk due to recent claim history",
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
