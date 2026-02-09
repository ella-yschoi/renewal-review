import asyncio
import uuid
from enum import StrEnum

from fastapi import APIRouter, HTTPException, Query

from app.data_loader import load_pairs
from app.engine.batch import process_batch
from app.models.review import BatchSummary
from app.routes.reviews import get_results_store

router = APIRouter(prefix="/batch", tags=["batch"])


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


_jobs: dict[str, dict] = {}
_last_summary: BatchSummary | None = None


@router.post("/run")
async def run_batch(sample: int | None = Query(None, ge=1)) -> dict:
    pairs = load_pairs(sample)
    if not pairs:
        raise HTTPException(status_code=404, detail="No data found. Run data/generate.py first.")

    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": JobStatus.RUNNING, "summary": None, "error": None}

    async def _process():
        global _last_summary
        try:
            loop = asyncio.get_event_loop()
            results, summary = await loop.run_in_executor(None, process_batch, pairs)
            _last_summary = summary

            store = get_results_store()
            for r in results:
                store[r.policy_number] = r

            _jobs[job_id]["status"] = JobStatus.COMPLETED
            _jobs[job_id]["summary"] = summary.model_dump()
        except Exception as e:
            _jobs[job_id]["status"] = JobStatus.FAILED
            _jobs[job_id]["error"] = str(e)

    asyncio.create_task(_process())

    return {"job_id": job_id, "status": JobStatus.RUNNING}


@router.get("/status/{job_id}")
def get_job_status(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"job_id": job_id, **job}


@router.get("/summary", response_model=BatchSummary | None)
def get_summary() -> BatchSummary | None:
    return _last_summary
