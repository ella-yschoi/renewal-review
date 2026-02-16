from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings

load_dotenv()


class RuleThresholds(BaseModel):
    premium_high_pct: float = 10.0
    premium_critical_pct: float = 20.0


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
    openai_model: str = "gpt-4o-mini"
    sonnet_model: str = "claude-sonnet-4-5-20250929"
    haiku_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 1024
    temperature: float = 0.1
    task_models: dict[str, str] = {
        "risk_signal_extractor": "sonnet",
        "endorsement_comparison": "haiku",
        "review_summary": "haiku",
        "quote_personalization": "haiku",
    }


class Settings(BaseSettings):
    model_config = {"env_prefix": "RR_"}

    llm_enabled: bool = False
    data_path: str = "data/renewals.json"
    db_url: str = ""

    rules: RuleThresholds = RuleThresholds()
    quotes: QuoteConfig = QuoteConfig()
    portfolio: PortfolioThresholds = PortfolioThresholds()
    llm: LLMConfig = LLMConfig()


settings = Settings()
