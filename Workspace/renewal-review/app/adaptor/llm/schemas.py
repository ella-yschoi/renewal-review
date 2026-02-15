from pydantic import BaseModel


class RiskSignal(BaseModel):
    signal_type: str
    description: str
    severity: str


class RiskSignalExtractorResponse(BaseModel):
    signals: list[RiskSignal]
    confidence: float
    summary: str


class EndorsementComparisonResponse(BaseModel):
    material_change: bool
    change_type: str
    confidence: float
    reasoning: str


class ReviewSummaryResponse(BaseModel):
    summary: str


class PersonalizedQuote(BaseModel):
    quote_id: str
    trade_off: str
    broker_tip: str


class QuotePersonalizationResponse(BaseModel):
    quotes: list[PersonalizedQuote]
