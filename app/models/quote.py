from pydantic import BaseModel


class CoverageAdjustment(BaseModel):
    field: str
    original_value: str
    proposed_value: str
    strategy: str


class QuoteRecommendation(BaseModel):
    quote_id: str
    adjustments: list[CoverageAdjustment]
    estimated_savings_pct: float
    estimated_savings_dollar: float
    trade_off: str
