import asyncio
import json
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.data_loader import load_pairs
from app.engine.batch import process_pair
from app.engine.parser import parse_pair
from app.models.review import RiskLevel
from app.routes.reviews import get_results_store

router = APIRouter(tags=["eval"])

_migration_jobs: dict[str, dict] = {}

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
async def migration_comparison(sample: int = Query(50, ge=1)) -> dict:
    pairs = load_pairs(sample)
    if not pairs:
        raise HTTPException(status_code=404, detail="No data found. Run data/generate.py first.")

    job_id = str(uuid.uuid4())[:8]
    total_steps = len(pairs) * 2
    _migration_jobs[job_id] = {
        "status": "running",
        "processed": 0,
        "total": total_steps,
        "phase": "V1",
        "result": None,
        "error": None,
    }

    async def _process():
        try:
            loop = asyncio.get_event_loop()

            def do_work():
                from app.llm.mock import MockLLMClient

                n = len(pairs)

                v1_start = time.perf_counter()
                v1_results = []
                for i, p in enumerate(pairs):
                    v1_results.append(process_pair(p, llm_client=None))
                    _migration_jobs[job_id]["processed"] = i + 1
                v1_time = (time.perf_counter() - v1_start) * 1000

                _migration_jobs[job_id]["phase"] = "V2"
                mock_client = MockLLMClient()
                v2_start = time.perf_counter()
                v2_results = []
                for i, p in enumerate(pairs):
                    v2_results.append(process_pair(p, llm_client=mock_client))
                    _migration_jobs[job_id]["processed"] = n + i + 1
                v2_time = (time.perf_counter() - v2_start) * 1000

                return v1_results, v1_time, v2_results, v2_time

            v1_results, v1_time, v2_results, v2_time = await loop.run_in_executor(None, do_work)

            store = get_results_store()
            for r in v2_results:
                store[r.policy_number] = r

            examples = []
            risk_changes = 0
            llm_analyzed = sum(1 for r in v2_results if r.llm_insights)
            new_insights = sum(len(r.llm_insights) for r in v2_results)

            for v1, v2 in zip(v1_results, v2_results, strict=True):
                if v1.risk_level != v2.risk_level:
                    risk_changes += 1
                    examples.append(
                        {
                            "policy_number": v1.policy_number,
                            "v1_risk": v1.risk_level.value,
                            "v2_risk": v2.risk_level.value,
                            "v2_insights": [
                                {
                                    "type": i.analysis_type,
                                    "finding": i.finding,
                                    "confidence": i.confidence,
                                }
                                for i in v2.llm_insights
                            ],
                            "flags": [f.value for f in v2.diff.flags],
                        }
                    )

            _migration_jobs[job_id]["status"] = "completed"
            _migration_jobs[job_id]["result"] = {
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
                "examples": examples[:10],
            }
        except Exception as e:
            _migration_jobs[job_id]["status"] = "failed"
            _migration_jobs[job_id]["error"] = str(e)

    asyncio.create_task(_process())
    return {"job_id": job_id, "status": "running", "total": total_steps}


@router.get("/migration/status/{job_id}")
def migration_status(job_id: str) -> dict:
    job = _migration_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"job_id": job_id, **job}
