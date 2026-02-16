from enum import StrEnum

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings

load_dotenv()


class ModelKey(StrEnum):
    SONNET = "sonnet"
    HAIKU = "haiku"


class NotesKeywords(BaseModel):
    claims_history: list[str] = [
        "claim",
        "loss",
        "accident",
        "incident",
        "damage report",
    ]
    property_risk: list[str] = [
        "roof",
        "foundation",
        "mold",
        "flood zone",
        "sinkhole",
        "brush area",
    ]
    regulatory: list[str] = [
        "non-renewal",
        "cancellation",
        "compliance",
        "surplus lines",
        "state filing",
    ]
    driver_risk: list[str] = [
        "DUI",
        "DWI",
        "suspended license",
        "reckless driving",
        "at-fault",
    ]


class RuleThresholds(BaseModel):
    premium_high_pct: float = 10.0
    premium_critical_pct: float = 20.0
    youthful_operator_age: int = 25
    um_uim_min_limit: str = "50/100"


class QuoteConfig(BaseModel):
    auto_collision_deductible: float = 1000.0
    auto_comprehensive_deductible: float = 500.0
    auto_medical_min: float = 2000.0
    home_deductible: float = 2500.0
    home_personal_property_ratio: float = 0.5
    savings_raise_deductible_auto: float = 10.0
    savings_drop_optional: float = 4.0
    savings_reduce_medical: float = 2.5
    savings_raise_deductible_home: float = 12.5
    savings_drop_water_backup: float = 3.0
    savings_reduce_personal_property: float = 4.0


class PortfolioThresholds(BaseModel):
    high_liability: float = 500_000
    low_liability: float = 200_000
    concentration_pct: float = 0.70
    portfolio_change_pct: float = 15.0


class LLMConfig(BaseModel):
    sonnet_model: str = "claude-sonnet-4-5-20250929"
    haiku_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 1024
    comparison_sample_size: int = 100
    task_models: dict[str, str] = {
        "risk_signal_extractor": ModelKey.SONNET,
        "endorsement_comparison": ModelKey.HAIKU,
        "review_summary": ModelKey.HAIKU,
        "quote_personalization": ModelKey.HAIKU,
    }


class Settings(BaseSettings):
    model_config = {"env_prefix": "RR_", "env_nested_delimiter": "__"}

    llm_enabled: bool = False
    data_path: str = "data/renewals.json"
    db_url: str = ""

    rules: RuleThresholds = RuleThresholds()
    notes_keywords: NotesKeywords = NotesKeywords()
    quotes: QuoteConfig = QuoteConfig()
    portfolio: PortfolioThresholds = PortfolioThresholds()
    llm: LLMConfig = LLMConfig()


settings = Settings()
