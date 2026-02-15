from pydantic import BaseModel

from app.domain.models.enums import QuoteStrategy


class CoverageAdjustment(BaseModel):
    field: str
    original_value: str
    proposed_value: str
    strategy: QuoteStrategy


class QuoteRecommendation(BaseModel):
    quote_id: str
    adjustments: list[CoverageAdjustment]
    estimated_savings_pct: float
    estimated_savings_dollar: float
    trade_off: str
    broker_tip: str = ""
