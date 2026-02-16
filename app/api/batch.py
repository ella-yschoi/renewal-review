import asyncio
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.adaptor.storage.memory import InMemoryHistoryStore, InMemoryJobStore, InMemoryReviewStore
from app.application.batch import process_batch
from app.data_loader import load_pairs, total_count
from app.domain.models.review import BatchSummary
from app.domain.ports.result_writer import ResultWriter
from app.infra.deps import get_history_store, get_job_store, get_result_writer, get_review_store

router = APIRouter(prefix="/batch", tags=["batch"])


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@router.get("/total-count")
def get_total_count() -> dict:
    return {"total": total_count()}


@router.post("/run")
async def run_batch(
    sample: int | None = Query(None, ge=1),
    store: InMemoryReviewStore = Depends(get_review_store),
    history: InMemoryHistoryStore = Depends(get_history_store),
    jobs: InMemoryJobStore = Depends(get_job_store),
    writer: ResultWriter = Depends(get_result_writer),
) -> dict:
    pairs = load_pairs(sample)
    if not pairs:
        raise HTTPException(status_code=404, detail="No data found. Run data/generate.py first.")

    job_id = str(uuid.uuid4())[:8]
    jobs.set(
        job_id,
        {
            "status": JobStatus.RUNNING,
            "summary": None,
            "error": None,
            "processed": 0,
            "total": len(pairs),
        },
    )

    async def _process():
        try:
            job = jobs.get(job_id)

            def on_progress(processed, total):
                job["processed"] = processed

            loop = asyncio.get_event_loop()
            results, summary = await loop.run_in_executor(
                None, lambda: process_batch(pairs, on_progress=on_progress)
            )
            jobs.last_summary = summary

            now = datetime.now(ZoneInfo("America/Vancouver"))
            store.clear()
            for r in results:
                r.reviewed_at = now
                store[r.policy_number] = r
                writer.save_rule_result(job_id, r)

            job["status"] = JobStatus.COMPLETED
            job["summary"] = summary.model_dump()

            from app.domain.models.analytics import BatchRunRecord

            record = BatchRunRecord(
                job_id=job_id,
                total=summary.total,
                no_action_needed=summary.no_action_needed,
                review_recommended=summary.review_recommended,
                action_required=summary.action_required,
                urgent_review=summary.urgent_review,
                processing_time_ms=summary.processing_time_ms,
                created_at=now,
            )
            history.append(record)
        except Exception as e:
            job = jobs.get(job_id)
            job["status"] = JobStatus.FAILED
            job["error"] = str(e)

    asyncio.create_task(_process())

    return {"job_id": job_id, "status": JobStatus.RUNNING, "total": len(pairs)}


@router.post("/review-selected")
async def review_selected(
    policy_numbers: Annotated[list[str], Body(embed=True)],
    store: InMemoryReviewStore = Depends(get_review_store),
    jobs: InMemoryJobStore = Depends(get_job_store),
    writer: ResultWriter = Depends(get_result_writer),
) -> dict:
    all_pairs = load_pairs()
    target = set(policy_numbers)
    pairs = [p for p in all_pairs if p.prior.policy_number in target]
    if not pairs:
        raise HTTPException(status_code=404, detail="No matching policies found.")

    job_id = str(uuid.uuid4())[:8]
    jobs.set(
        job_id,
        {
            "status": JobStatus.RUNNING,
            "summary": None,
            "error": None,
            "processed": 0,
            "total": len(pairs),
        },
    )

    async def _process():
        try:
            job = jobs.get(job_id)

            def on_progress(processed, total):
                job["processed"] = processed

            loop = asyncio.get_event_loop()
            results, summary = await loop.run_in_executor(
                None, lambda: process_batch(pairs, on_progress=on_progress)
            )
            jobs.last_summary = summary

            now = datetime.now(ZoneInfo("America/Vancouver"))
            for r in results:
                r.reviewed_at = now
                store[r.policy_number] = r
                writer.save_rule_result(job_id, r)

            job["status"] = JobStatus.COMPLETED
            job["summary"] = summary.model_dump()
        except Exception as e:
            job = jobs.get(job_id)
            job["status"] = JobStatus.FAILED
            job["error"] = str(e)

    asyncio.create_task(_process())

    return {"job_id": job_id, "status": JobStatus.RUNNING, "total": len(pairs)}


@router.get("/status/{job_id}")
def get_job_status(
    job_id: str,
    jobs: InMemoryJobStore = Depends(get_job_store),
) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"job_id": job_id, **job}


@router.get("/summary", response_model=BatchSummary | None)
def get_summary(
    jobs: InMemoryJobStore = Depends(get_job_store),
) -> BatchSummary | None:
    return jobs.last_summary
