from enum import StrEnum

from pydantic import BaseModel

from app.models.diff import DiffResult
from app.models.policy import RenewalPair


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LLMInsight(BaseModel):
    analysis_type: str
    finding: str
    confidence: float
    reasoning: str = ""


class ReviewResult(BaseModel):
    policy_number: str
    risk_level: RiskLevel
    diff: DiffResult
    llm_insights: list[LLMInsight] = []
    summary: str = ""
    pair: RenewalPair | None = None


class BatchSummary(BaseModel):
    total: int
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0
    llm_analyzed: int = 0
    processing_time_ms: float = 0.0
