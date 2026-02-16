import asyncio
import json
import random
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.adaptor.storage.memory import InMemoryReviewStore
from app.application.batch import process_pair, risk_distribution
from app.domain.models.review import RiskLevel
from app.domain.ports.result_writer import ResultWriter
from app.domain.services.parser import parse_pair
from app.infra.deps import get_llm_client, get_result_writer, get_review_store

router = APIRouter(tags=["eval"])

_migration_jobs: dict[str, dict] = {}
_last_comparison: dict | None = None

GOLDEN_PATH = Path(__file__).parent.parent.parent / "data" / "samples" / "golden_eval.json"
RISK_ORDER = [
    RiskLevel.NO_ACTION_NEEDED,
    RiskLevel.REVIEW_RECOMMENDED,
    RiskLevel.ACTION_REQUIRED,
    RiskLevel.URGENT_REVIEW,
]


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
    return risk_distribution(results)


@router.get("/migration/latest")
def get_latest_comparison(
    writer: ResultWriter = Depends(get_result_writer),
) -> dict:
    global _last_comparison
    if _last_comparison is None:
        saved = writer.load_latest_comparison()
        if saved is not None:
            _last_comparison = saved
    if _last_comparison is None:
        return {"status": "none"}
    return _last_comparison


@router.post("/migration/comparison")
async def migration_comparison(
    store: InMemoryReviewStore = Depends(get_review_store),
    writer: ResultWriter = Depends(get_result_writer),
) -> dict:
    global _last_comparison

    from app.config import settings

    review_recommended = [
        r
        for r in store.values()
        if r.risk_level == RiskLevel.REVIEW_RECOMMENDED and r.pair and r.reviewed_at is not None
    ]
    if not review_recommended:
        raise HTTPException(
            status_code=404,
            detail="No reviewed Review Recommended policies found. Run batch review first.",
        )

    total_eligible = len(review_recommended)
    sample_size = settings.llm.comparison_sample_size
    if len(review_recommended) > sample_size:
        review_recommended = random.sample(review_recommended, sample_size)

    pairs = [r.pair for r in review_recommended]
    llm_client = get_llm_client()

    job_id = str(uuid.uuid4())[:8]
    total_steps = len(pairs) * 2
    _migration_jobs[job_id] = {
        "status": "running",
        "processed": 0,
        "total": total_steps,
        "phase": "basic",
        "result": None,
        "error": None,
    }

    async def _process():
        global _last_comparison
        try:
            loop = asyncio.get_event_loop()

            def do_work():
                from app.adaptor.llm.mock import MockLLMClient

                client = llm_client or MockLLMClient()
                n = len(pairs)

                basic_start = time.perf_counter()
                basic_results = []
                for i, p in enumerate(pairs):
                    basic_results.append(process_pair(p, llm_client=None))
                    _migration_jobs[job_id]["processed"] = i + 1
                basic_time = (time.perf_counter() - basic_start) * 1000

                _migration_jobs[job_id]["phase"] = "llm"
                llm_start = time.perf_counter()
                llm_results = []
                for i, p in enumerate(pairs):
                    llm_results.append(process_pair(p, llm_client=client))
                    _migration_jobs[job_id]["processed"] = n + i + 1
                llm_time = (time.perf_counter() - llm_start) * 1000

                return basic_results, basic_time, llm_results, llm_time

            basic_results, basic_time, llm_results, llm_time = await loop.run_in_executor(
                None, do_work
            )

            for r in llm_results:
                existing = store.get(r.policy_number)
                if existing:
                    r.reviewed_at = existing.reviewed_at
                    r.broker_contacted = existing.broker_contacted
                    r.quote_generated = existing.quote_generated
                store[r.policy_number] = r
                writer.save_llm_result(job_id, r)

            examples = []
            all_compared = []
            risk_changes = 0
            llm_analyzed = sum(1 for r in llm_results if r.llm_insights)
            new_insights = sum(len(r.llm_insights) for r in llm_results)

            for basic, llm in zip(basic_results, llm_results, strict=True):
                risk_changed = basic.risk_level != llm.risk_level
                if risk_changed:
                    risk_changes += 1
                insights_data = [
                    {
                        "type": i.analysis_type,
                        "finding": i.finding,
                        "confidence": i.confidence,
                    }
                    for i in llm.llm_insights
                ]
                row = {
                    "policy_number": basic.policy_number,
                    "basic_risk": basic.risk_level.value,
                    "llm_risk": llm.risk_level.value,
                    "risk_changed": risk_changed,
                    "llm_insights": insights_data,
                    "flags": [f.value for f in llm.diff.flags],
                    "summary": llm.summary,
                }
                all_compared.append(row)
                if risk_changed:
                    examples.append(row)

            result = {
                "status": "completed",
                "sample_size": len(pairs),
                "total_eligible": total_eligible,
                "basic": {
                    "processing_time_ms": round(basic_time, 1),
                    "distribution": _risk_dist(basic_results),
                },
                "llm": {
                    "processing_time_ms": round(llm_time, 1),
                    "distribution": _risk_dist(llm_results),
                    "llm_analyzed": llm_analyzed,
                    "llm_analyzed_pct": round(llm_analyzed / len(pairs) * 100, 1),
                    "total_insights": new_insights,
                },
                "delta": {
                    "risk_level_changes": risk_changes,
                    "new_llm_insights": new_insights,
                    "latency_overhead_ms": round(llm_time - basic_time, 1),
                },
                "examples": examples,
                "all_compared": all_compared,
            }

            _migration_jobs[job_id]["status"] = "completed"
            _migration_jobs[job_id]["result"] = result
            _last_comparison = result
            writer.save_comparison_result(job_id, result)
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
