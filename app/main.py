from fastapi import FastAPI

from app.routes.analytics import router as analytics_router
from app.routes.batch import router as batch_router
from app.routes.eval import router as eval_router
from app.routes.portfolio import router as portfolio_router
from app.routes.quotes import router as quotes_router
from app.routes.reviews import router as reviews_router
from app.routes.ui import router as ui_router

app = FastAPI(
    title="Renewal Review",
    description="Insurance renewal review pipeline — rule-based + LLM hybrid",
    version="0.1.0",
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
