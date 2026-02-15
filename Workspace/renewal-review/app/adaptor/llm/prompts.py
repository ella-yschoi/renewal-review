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

REVIEW_SUMMARY = (
    "You are an insurance renewal analyst writing a brief summary for a broker.\n"
    "\n"
    "Policy: {policy_number} ({policy_type})\n"
    "Premium: ${prior_premium} → ${renewal_premium} ({premium_change})\n"
    "Risk Level: {risk_level} | Flags: {flags}\n"
    "\n"
    "Key changes:\n"
    "{key_changes}\n"
    "\n"
    "{llm_insights_section}\n"
    "\n"
    "Write a 2-3 sentence natural language summary highlighting the most important\n"
    "findings for a broker reviewing this renewal. Focus on actionable information.\n"
    "\n"
    "Respond with ONLY valid JSON:\n"
    '{{"summary": "Your 2-3 sentence summary here"}}'
)

QUOTE_PERSONALIZATION = (
    "You are an insurance advisor personalizing quote recommendations for a broker.\n"
    "\n"
    "Policy context:\n"
    "{policy_context}\n"
    "\n"
    "Quotes to personalize:\n"
    "{quotes_json}\n"
    "\n"
    "For each quote, rewrite the trade_off to be specific to this client's situation,\n"
    "and add a broker_tip with actionable advice based on the policy context.\n"
    "Keep each under 2 sentences.\n"
    "\n"
    "Respond with ONLY valid JSON:\n"
    '{{"quotes": [{{"quote_id": "Q1", "trade_off": "...", "broker_tip": "..."}}]}}'
)

PROMPT_MAP = {
    "endorsement_comparison": ENDORSEMENT_COMPARISON,
    "risk_signal_extractor": RISK_SIGNAL_EXTRACTOR,
    "review_summary": REVIEW_SUMMARY,
    "quote_personalization": QUOTE_PERSONALIZATION,
}
