from enum import StrEnum

from pydantic import BaseModel

from app.models.diff import DiffResult
from app.models.policy import RenewalPair


class RiskLevel(StrEnum):
    NO_ACTION_NEEDED = "no_action_needed"
    REVIEW_RECOMMENDED = "review_recommended"
    ACTION_REQUIRED = "action_required"
    URGENT_REVIEW = "urgent_review"


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
    llm_summary_generated: bool = False
    pair: RenewalPair | None = None


class BatchSummary(BaseModel):
    total: int
    no_action_needed: int = 0
    review_recommended: int = 0
    action_required: int = 0
    urgent_review: int = 0
    llm_analyzed: int = 0
    processing_time_ms: float = 0.0
