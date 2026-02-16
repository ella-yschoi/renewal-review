import os
from typing import Any

from app.domain.models.enums import LLMTaskName


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
        if trace_name == LLMTaskName.RISK_SIGNAL_EXTRACTOR:
            return {
                "signals": [
                    {
                        "signal_type": "claims_history",
                        "description": "Prior water damage claim noted in file",
                        "severity": "high",
                    },
                    {
                        "signal_type": "property_risk",
                        "description": "Aging roof mentioned — replacement overdue",
                        "severity": "medium",
                    },
                    {
                        "signal_type": "regulatory",
                        "description": (
                            "SR-22 filing active — state-mandated proof "
                            "of insurance required for continued compliance"
                        ),
                        "severity": "high",
                    },
                ],
                "confidence": 0.88,
                "summary": "Multiple risk indicators found in policy notes",
            }

        if trace_name == LLMTaskName.ENDORSEMENT_COMPARISON:
            return {
                "material_change": True,
                "change_type": "restriction",
                "confidence": 0.8,
                "reasoning": (
                    "Water backup endorsement (HO 04 95) removed in renewal "
                    "— sewer/drain coverage dropped, material for property "
                    "with prior water damage claim"
                ),
            }

        if trace_name == LLMTaskName.REVIEW_SUMMARY:
            return {
                "summary": (
                    "This renewal shows a 23% premium increase from $2,400 to $2,952 "
                    "with water backup coverage dropped and deductible unchanged. "
                    "Prior water damage claim and aging roof noted — recommend "
                    "urgent broker review before binding."
                ),
            }

        if trace_name == LLMTaskName.QUOTE_PERSONALIZATION:
            return {
                "quotes": [
                    {
                        "quote_id": "Quote 1",
                        "trade_off": (
                            "This option raises the home deductible from $1,000 to $2,500, "
                            "saving approximately $607/year (12.5%). If a covered event like "
                            "a storm or fire occurs, the client would pay the first $2,500 "
                            "out of pocket before insurance covers the rest. Given the prior "
                            "water damage claim and aging roof noted in this policy, the risk "
                            "of needing to file a claim is above average. Best suited for "
                            "clients with strong emergency savings who rarely file claims."
                        ),
                        "broker_tip": (
                            "Ask the client whether they have at least $2,500 in liquid savings "
                            "set aside for emergencies. With the aging roof and prior water "
                            "damage history on this property, a claim in the near term is "
                            "plausible — confirm they're comfortable absorbing that cost before "
                            "binding."
                        ),
                    },
                    {
                        "quote_id": "Quote 2",
                        "trade_off": (
                            "Removing water backup coverage saves about $146/year (3%). "
                            "This means the client loses protection for sewer backup, sump "
                            "pump failure, and foundation seepage damage. A typical water "
                            "backup claim averages $7,000–$10,000 in restoration costs. "
                            "This policy already has a prior water damage claim on file, "
                            "making this a higher-risk removal. Not recommended for "
                            "properties with known water issues or older plumbing."
                        ),
                        "broker_tip": (
                            "Before removing this coverage, ask the client about the age "
                            "and condition of their sump pump, plumbing, and drainage system. "
                            "Given the prior water damage claim, discuss whether they've "
                            "made repairs since — if not, dropping this endorsement could "
                            "leave them exposed to a repeat loss."
                        ),
                    },
                ],
            }

        return {"error": "unknown prompt"}
