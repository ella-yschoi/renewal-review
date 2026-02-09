import json
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.data_loader import load_pairs
from app.engine.batch import process_pair
from app.engine.parser import parse_pair
from app.models.review import RiskLevel

router = APIRouter(tags=["eval"])

GOLDEN_PATH = Path(__file__).parent.parent.parent / "data" / "samples" / "golden_eval.json"
RISK_ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]


def _risk_ge(actual: RiskLevel, expected: RiskLevel) -> bool:
    return RISK_ORDER.index(actual) >= RISK_ORDER.index(expected)


@router.post("/eval/run")
def run_eval() -> dict:
    if not GOLDEN_PATH.exists():
        raise HTTPException(status_code=404, detail="Golden eval file not found")

    cases = json.loads(GOLDEN_PATH.read_text())
    results = []

    for case in cases:
        pair = parse_pair(case["pair"])
        review = process_pair(pair)

        expected_min = RiskLevel(case["expected_min_risk"])
        expected_flags = set(case["expected_flags"])
        actual_flags = set(f.value for f in review.diff.flags)

        risk_pass = _risk_ge(review.risk_level, expected_min)
        flags_pass = expected_flags.issubset(actual_flags)

        results.append(
            {
                "policy_number": review.policy_number,
                "description": case["description"],
                "risk_pass": risk_pass,
                "flags_pass": flags_pass,
                "expected_risk": expected_min.value,
                "actual_risk": review.risk_level.value,
                "missing_flags": list(expected_flags - actual_flags),
                "extra_flags": list(actual_flags - expected_flags),
            }
        )

    passed = sum(1 for r in results if r["risk_pass"] and r["flags_pass"])
    return {
        "total": len(results),
        "passed": passed,
        "accuracy": round(passed / len(results) * 100, 1) if results else 0,
        "details": results,
    }


def _risk_dist(results: list) -> dict[str, int]:
    return {
        "low": sum(1 for r in results if r.risk_level == RiskLevel.LOW),
        "medium": sum(1 for r in results if r.risk_level == RiskLevel.MEDIUM),
        "high": sum(1 for r in results if r.risk_level == RiskLevel.HIGH),
        "critical": sum(1 for r in results if r.risk_level == RiskLevel.CRITICAL),
    }


@router.post("/migration/comparison")
def migration_comparison(sample: int = Query(50, ge=1)) -> dict:
    pairs = load_pairs(sample)
    if not pairs:
        raise HTTPException(status_code=404, detail="No data found. Run data/generate.py first.")

    # V1 results (no LLM)
    v1_start = time.perf_counter()
    v1_results = [process_pair(p, llm_client=None) for p in pairs]
    v1_time = (time.perf_counter() - v1_start) * 1000

    # V2 results (with mock LLM for comparison without real API calls)
    from app.llm.mock import MockLLMClient

    mock_client = MockLLMClient()
    v2_start = time.perf_counter()
    v2_results = [process_pair(p, llm_client=mock_client) for p in pairs]
    v2_time = (time.perf_counter() - v2_start) * 1000

    risk_changes = sum(
        1
        for v1, v2 in zip(v1_results, v2_results, strict=True)
        if v1.risk_level != v2.risk_level
    )
    llm_analyzed = sum(1 for r in v2_results if r.llm_insights)
    new_insights = sum(len(r.llm_insights) for r in v2_results)

    return {
        "sample_size": len(pairs),
        "v1": {
            "processing_time_ms": round(v1_time, 1),
            "distribution": _risk_dist(v1_results),
        },
        "v2": {
            "processing_time_ms": round(v2_time, 1),
            "distribution": _risk_dist(v2_results),
            "llm_analyzed": llm_analyzed,
            "llm_analyzed_pct": round(llm_analyzed / len(pairs) * 100, 1),
            "total_insights": new_insights,
        },
        "delta": {
            "risk_level_changes": risk_changes,
            "new_llm_insights": new_insights,
            "latency_overhead_ms": round(v2_time - v1_time, 1),
        },
    }
