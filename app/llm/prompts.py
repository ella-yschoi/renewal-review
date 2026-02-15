COVERAGE_SIMILARITY = """You are an insurance coverage analyst.

Compare the two coverage descriptions below and determine if they provide equivalent protection.

Prior coverage: {prior_coverage}
Renewal coverage: {renewal_coverage}

Respond with ONLY valid JSON — no markdown, no code blocks, no extra text:
{{
  "equivalent": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of differences or equivalence"
}}"""

ENDORSEMENT_COMPARISON = """You are an insurance endorsement analyst.

Compare these two endorsement descriptions from the same policy's prior and renewal terms.
Identify any material changes in coverage scope, conditions, or exclusions.

Rules:
- If either endorsement is empty or missing, treat it as coverage removed or added.
- Empty renewal endorsement = coverage dropped = "restriction", material_change=true.

Prior endorsement: {prior_endorsement}
Renewal endorsement: {renewal_endorsement}

Respond with ONLY valid JSON — no markdown, no code blocks, no extra text:
{{
  "material_change": true/false,
  "change_type": "expansion" | "restriction" | "neutral" | "none",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of what changed and its impact"
}}"""

RISK_SIGNAL_EXTRACTOR = """You are an insurance risk analyst.

Analyze the following renewal notes for risk signals that may require underwriter attention.
Look for: claims history, property condition issues, driver risk factors,
coverage adequacy concerns, regulatory requirements, and any red flags.

Signal grouping rules:
- Each signal must have a distinct, independent root cause.
- Multiple consequences of the same event = ONE signal
  (e.g., "water damage claim" + "rate impact from that claim" = one signal).
- Separate signals only when root causes are independent
  (e.g., "prior claim" + "new teen driver" = two signals).

Notes: {notes}

Respond with ONLY valid JSON — no markdown, no code blocks, no extra text:
{{
  "signals": [
    {{
      "signal_type": "claims_history" | "property_risk" | "driver_risk" | "coverage_gap" | "other",
      "description": "Brief description of the risk signal",
      "severity": "low" | "medium" | "high"
    }}
  ],
  "confidence": 0.0-1.0,
  "summary": "One-sentence summary of overall risk assessment"
}}"""

PROMPT_MAP = {
    "coverage_similarity": COVERAGE_SIMILARITY,
    "endorsement_comparison": ENDORSEMENT_COMPARISON,
    "risk_signal_extractor": RISK_SIGNAL_EXTRACTOR,
}
