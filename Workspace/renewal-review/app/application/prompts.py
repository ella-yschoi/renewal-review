ENDORSEMENT_COMPARISON = """You are an insurance endorsement analyst \
reviewing personal lines (Auto PP / Homeowners HO).

Compare these two endorsement descriptions from the same policy's prior and renewal terms.
Identify any material changes in coverage scope, conditions, or exclusions.

ACORD endorsement change types: Add (new coverage), Change (modified terms), Delete (removed).
Standard forms: HO 04 xx (homeowners), PP 03 xx (auto). Reference form numbers if identifiable.

Rules:
- If either endorsement is empty or missing, treat it as coverage removed or added.
- Empty renewal endorsement = coverage dropped = "restriction", material_change=true.
- Changes affecting liability limits (BI, PD, Coverage E) or legally
  mandated coverages are always material.
- Deductible-only changes are typically "neutral" unless the increase is substantial (>2x).

Prior endorsement: {prior_endorsement}
Renewal endorsement: {renewal_endorsement}

Respond with ONLY valid JSON — no markdown, no code blocks, no extra text:
{{
  "material_change": true/false,
  "change_type": "expansion" | "restriction" | "neutral" | "none",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of what changed and its impact"
}}"""

RISK_SIGNAL_EXTRACTOR = """You are an insurance risk analyst \
reviewing personal lines (Auto PP / Homeowners HO).

Analyze the following renewal notes for risk signals that may require underwriter attention.

Signal categories (ACORD-aligned):
- claims_history: Prior losses (ACORD 80/90 Loss History section). Frequency and severity matter.
- property_risk: Dwelling condition, roof age, electrical/plumbing issues, proximity to hazards.
- driver_risk: MVR violations, SR-22 filings, youthful operators, license suspensions.
- coverage_gap: Missing state-mandated coverages (UM/UIM, PIP), inadequate limits vs exposure.
- regulatory: State filing requirements, SR-22 mandates, minimum limit compliance.
- other: Signals that don't fit above categories.

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
      "signal_type": "claims_history" | "property_risk" | "driver_risk"
        | "coverage_gap" | "regulatory" | "other",
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
    "Write a 2-3 sentence summary for the broker. Prioritize:\n"
    "1. Liability limit changes (BI, PD, Coverage E) — flag any reduction.\n"
    "2. Coverage dropped or added — especially state-mandated coverages.\n"
    "3. Premium change drivers — claims history, risk factors, endorsement shifts.\n"
    "Use specific dollar amounts and percentages. End with a clear action recommendation.\n"
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
    "Quotes to personalize (each includes adjustments with from/to values and savings):\n"
    "{quotes_json}\n"
    "\n"
    "For each quote, write:\n"
    "\n"
    "trade_off (3-4 sentences):\n"
    "- Explain what the adjustment changes (use exact dollar amounts from the adjustments).\n"
    "- Describe the real-world impact: what happens if the client has a claim?\n"
    "  Give a concrete scenario (e.g., 'If a pipe bursts, you would pay the first $2,500').\n"
    "- Reference the client's specific risk factors (claims history, property condition,\n"
    "  driver record, notes) to explain why this trade-off matters for THIS client.\n"
    "- State who this option is best suited for (e.g., 'Best for clients with emergency\n"
    "  savings who rarely file claims').\n"
    "\n"
    "broker_tip (2-3 sentences):\n"
    "- Actionable conversation starter for the broker to discuss with the client.\n"
    "- Include a specific question or check the broker should perform.\n"
    "- Reference relevant policy details (deductible amounts, coverage limits, claim history).\n"
    "\n"
    "Protected fields — NEVER suggest reducing these in any quote:\n"
    "- Bodily Injury (BI) / Property Damage (PD) limits\n"
    "- Uninsured Motorist (UM) limits\n"
    "- Coverage A (Dwelling) / Coverage E (Liability)\n"
    "If a quote involves these, flag it as requiring broker confirmation.\n"
    "\n"
    "Respond with ONLY valid JSON — no markdown, no code blocks:\n"
    '{{"quotes": [{{"quote_id": "Quote 1", "trade_off": "...", "broker_tip": "..."}}]}}'
)
