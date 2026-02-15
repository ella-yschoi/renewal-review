"""Langfuse Dataset 생성 스크립트.

3개 Dataset을 Langfuse에 등록한다:
  - risk-signal-benchmark (notes → risk signals)
  - endorsement-benchmark (prior/renewal endorsement → material change)
  - coverage-benchmark (prior/renewal coverage → equivalence)

Usage:
    uv run python scripts/langfuse_datasets.py
"""

import os
import sys

from dotenv import load_dotenv
from langfuse import Langfuse


def _check_env():
    load_dotenv()
    required = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 1. risk-signal-benchmark
# ---------------------------------------------------------------------------
RISK_SIGNAL_ITEMS = [
    {
        "input": {"notes": "Premium increase due to regional rate adjustment"},
        "expected_output": {
            "signals": [
                {
                    "signal_type": "other",
                    "description": "Regional rate adjustment causing premium increase",
                    "severity": "low",
                }
            ],
            "confidence": 0.7,
            "summary": (
                "Minor risk — routine regional rate adjustment"
                " with no specific underwriting concerns."
            ),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-AUTO-001"},
    },
    {
        "input": {"notes": ("Claim filed last year for water damage — monitor for rate impact")},
        "expected_output": {
            "signals": [
                {
                    "signal_type": "claims_history",
                    "description": "Recent water damage claim filed",
                    "severity": "high",
                },
                {
                    "signal_type": "property_risk",
                    "description": ("Water damage history indicates ongoing property risk"),
                    "severity": "medium",
                },
            ],
            "confidence": 0.85,
            "summary": (
                "High risk — recent water damage claim requires"
                " rate monitoring and property assessment."
            ),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-HOME-001"},
    },
    {
        "input": {"notes": "New teen driver added — high risk profile"},
        "expected_output": {
            "signals": [
                {
                    "signal_type": "driver_risk",
                    "description": ("Teen driver added to policy with high risk profile"),
                    "severity": "high",
                }
            ],
            "confidence": 0.9,
            "summary": (
                "High risk — teen driver addition significantly increases accident probability."
            ),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-AUTO-002"},
    },
    {
        "input": {"notes": "Inflation guard applied to dwelling coverage"},
        "expected_output": {
            "signals": [
                {
                    "signal_type": "other",
                    "description": ("Inflation guard adjustment to dwelling coverage"),
                    "severity": "low",
                }
            ],
            "confidence": 0.75,
            "summary": (
                "Low risk — standard inflation guard adjustment, no underwriting concerns."
            ),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-HOME-002"},
    },
    {
        "input": {
            "notes": ("Two at-fault accidents in past 12 months. SR-22 filing required by state.")
        },
        "expected_output": {
            "signals": [
                {
                    "signal_type": "claims_history",
                    "description": ("Two at-fault accidents in the past year"),
                    "severity": "high",
                },
                {
                    "signal_type": "driver_risk",
                    "description": (
                        "SR-22 filing required — indicates serious driving violations"
                    ),
                    "severity": "high",
                },
            ],
            "confidence": 0.95,
            "summary": (
                "Critical risk — multiple at-fault accidents"
                " with SR-22 requirement demands immediate review."
            ),
        },
        "metadata": {"source": "synthetic", "policy": "SYNTH-AUTO-001"},
    },
]

# ---------------------------------------------------------------------------
# 2. endorsement-benchmark
# ---------------------------------------------------------------------------
ENDORSEMENT_ITEMS = [
    {
        "input": {
            "prior_endorsement": "Scheduled personal property",
            "renewal_endorsement": ("Scheduled personal property — updated valuations"),
        },
        "expected_output": {
            "material_change": False,
            "change_type": "neutral",
            "confidence": 0.8,
            "reasoning": ("Valuation update is routine and does not change coverage scope."),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-HOME-002"},
    },
    {
        "input": {
            "prior_endorsement": ("Water backup and sump overflow coverage"),
            "renewal_endorsement": "",
        },
        "expected_output": {
            "material_change": True,
            "change_type": "restriction",
            "confidence": 0.95,
            "reasoning": (
                "Water backup coverage completely removed — significant gap in protection."
            ),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-HOME-001"},
    },
    {
        "input": {
            "prior_endorsement": "Uninsured motorist enhancement",
            "renewal_endorsement": "Uninsured motorist enhancement",
        },
        "expected_output": {
            "material_change": False,
            "change_type": "none",
            "confidence": 0.95,
            "reasoning": "Endorsement unchanged between terms.",
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-AUTO-001"},
    },
    {
        "input": {
            "prior_endorsement": ("Standard liability coverage $300,000"),
            "renewal_endorsement": (
                "Enhanced liability coverage $500,000 with umbrella extension"
            ),
        },
        "expected_output": {
            "material_change": True,
            "change_type": "expansion",
            "confidence": 0.9,
            "reasoning": (
                "Liability limit increased from $300K to $500K"
                " with umbrella extension — broadened coverage."
            ),
        },
        "metadata": {"source": "synthetic", "policy": "SYNTH-HOME-001"},
    },
    {
        "input": {
            "prior_endorsement": ("Earthquake coverage endorsement — full replacement cost"),
            "renewal_endorsement": (
                "Earthquake coverage endorsement — actual cash value, 15% deductible"
            ),
        },
        "expected_output": {
            "material_change": True,
            "change_type": "restriction",
            "confidence": 0.9,
            "reasoning": (
                "Downgraded from replacement cost to ACV"
                " with higher deductible — material reduction"
                " in coverage quality."
            ),
        },
        "metadata": {"source": "synthetic", "policy": "SYNTH-HOME-002"},
    },
]

# ---------------------------------------------------------------------------
# 3. coverage-benchmark
# ---------------------------------------------------------------------------
COVERAGE_ITEMS = [
    {
        "input": {
            "prior_coverage": "water_backup: active",
            "renewal_coverage": "water_backup: removed",
        },
        "expected_output": {
            "equivalent": False,
            "confidence": 0.95,
            "reasoning": (
                "Water backup coverage was active and has been"
                " removed — significant gap in flood protection."
            ),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-HOME-001"},
    },
    {
        "input": {
            "prior_coverage": "replacement_cost: active",
            "renewal_coverage": "replacement_cost: active",
        },
        "expected_output": {
            "equivalent": True,
            "confidence": 0.95,
            "reasoning": ("Both terms include replacement cost — no change."),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-HOME-001"},
    },
    {
        "input": {
            "prior_coverage": (
                "Dwelling $400,000; Personal Property $200,000;"
                " Liability $300,000; Deductible $1,000"
            ),
            "renewal_coverage": (
                "Dwelling $420,000; Personal Property $210,000;"
                " Liability $300,000; Deductible $2,500"
            ),
        },
        "expected_output": {
            "equivalent": False,
            "confidence": 0.85,
            "reasoning": (
                "Dwelling and personal property limits increased"
                " (inflation guard), but deductible raised from"
                " $1K to $2.5K — net change may reduce"
                " effective coverage."
            ),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-HOME-001"},
    },
    {
        "input": {
            "prior_coverage": (
                "Bodily Injury 250/500; Property Damage 100; UM 250/500; Medical 10,000"
            ),
            "renewal_coverage": (
                "Bodily Injury 100/300; Property Damage 50; UM 100/300; Medical 5,000"
            ),
        },
        "expected_output": {
            "equivalent": False,
            "confidence": 0.95,
            "reasoning": (
                "All liability limits significantly reduced"
                " — BI from 250/500 to 100/300, PD from 100K"
                " to 50K, UM and medical also reduced."
            ),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-AUTO-002"},
    },
    {
        "input": {
            "prior_coverage": (
                "Bodily Injury 50/100; Property Damage 50; Collision $500 ded; Comp $250 ded"
            ),
            "renewal_coverage": (
                "Bodily Injury 50/100; Property Damage 50; Collision $500 ded; Comp $250 ded"
            ),
        },
        "expected_output": {
            "equivalent": True,
            "confidence": 0.95,
            "reasoning": ("All coverage limits and deductibles identical between terms."),
        },
        "metadata": {"source": "golden_eval", "policy": "EVAL-AUTO-003"},
    },
]

# ---------------------------------------------------------------------------
# Create datasets + items
# ---------------------------------------------------------------------------
DATASETS = {
    "risk-signal-benchmark": RISK_SIGNAL_ITEMS,
    "endorsement-benchmark": ENDORSEMENT_ITEMS,
    "coverage-benchmark": COVERAGE_ITEMS,
}


def main():
    _check_env()
    langfuse = Langfuse()

    for ds_name, items in DATASETS.items():
        dataset = langfuse.create_dataset(name=ds_name)
        print(f"Created dataset: {ds_name} (id={dataset.id})")

        for i, item in enumerate(items):
            langfuse.create_dataset_item(
                dataset_name=ds_name,
                input=item["input"],
                expected_output=item["expected_output"],
                metadata=item.get("metadata", {}),
            )
            policy = item.get("metadata", {}).get("policy", "N/A")
            print(f"  [{i + 1}/{len(items)}] item added — {policy}")

    langfuse.flush()
    print("\nDone. 3 datasets registered in Langfuse.")


if __name__ == "__main__":
    main()
