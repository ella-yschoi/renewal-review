from enum import StrEnum


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class UnbundleRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QuoteStrategy(StrEnum):
    RAISE_DEDUCTIBLE = "raise_deductible"
    DROP_OPTIONAL = "drop_optional"
    REDUCE_MEDICAL = "reduce_medical"
    DROP_WATER_BACKUP = "drop_water_backup"
    REDUCE_PERSONAL_PROPERTY = "reduce_personal_property"


class AnalysisType(StrEnum):
    RISK_SIGNAL_EXTRACTOR = "risk_signal_extractor"
    ENDORSEMENT_COMPARISON = "endorsement_comparison"
    COVERAGE_SIMILARITY = "coverage_similarity"


class FlagType(StrEnum):
    DUPLICATE_MEDICAL = "duplicate_medical"
    DUPLICATE_ROADSIDE = "duplicate_roadside"
    HIGH_LIABILITY_EXPOSURE = "high_liability_exposure"
    LOW_LIABILITY_EXPOSURE = "low_liability_exposure"
    PREMIUM_CONCENTRATION = "premium_concentration"
    HIGH_PORTFOLIO_INCREASE = "high_portfolio_increase"
