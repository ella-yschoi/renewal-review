from fastapi import FastAPI

from app.routes.batch import router as batch_router
from app.routes.eval import router as eval_router
from app.routes.reviews import router as reviews_router

app = FastAPI(
    title="Renewal Review",
    description="Insurance renewal review pipeline — rule-based + LLM hybrid",
    version="0.1.0",
)

app.include_router(reviews_router)
app.include_router(batch_router)
app.include_router(eval_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
