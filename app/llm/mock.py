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

        if trace_name == "review_summary":
            return {
                "summary": (
                    "This renewal shows a 23% premium increase from $2,400 to $2,952 "
                    "with water backup coverage dropped and deductible unchanged. "
                    "Prior water damage claim and aging roof noted — recommend "
                    "urgent broker review before binding."
                ),
            }

        if trace_name == "quote_personalization":
            return {
                "quotes": [
                    {
                        "quote_id": "Q1",
                        "trade_off": (
                            "Raising the deductible to $2,500 saves 12.5% but means higher "
                            "out-of-pocket costs given the prior water damage claim history."
                        ),
                        "broker_tip": (
                            "Verify the client has emergency savings above $2,500 before "
                            "recommending this option, especially with the aging roof."
                        ),
                    },
                    {
                        "quote_id": "Q2",
                        "trade_off": (
                            "Dropping water backup saves 3% but removes sewer/drain coverage "
                            "on a property with known prior water damage."
                        ),
                        "broker_tip": (
                            "Given the claim history, discuss plumbing condition with the client "
                            "before removing this coverage."
                        ),
                    },
                ],
            }

        return {"error": "unknown prompt"}
