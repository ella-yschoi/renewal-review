from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.analytics import router as analytics_router
from app.api.batch import router as batch_router
from app.api.eval import router as eval_router
from app.api.portfolio import router as portfolio_router
from app.api.quotes import router as quotes_router
from app.api.reviews import router as reviews_router
from app.api.ui import router as ui_router
from app.infra.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Renewal Review",
    description="Insurance renewal review pipeline — rule-based + LLM hybrid",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(ui_router)
app.include_router(reviews_router)
app.include_router(batch_router)
app.include_router(eval_router)
app.include_router(analytics_router)
app.include_router(quotes_router)
app.include_router(portfolio_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
