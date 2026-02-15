from pydantic import BaseModel

from app.domain.models.enums import FlagType, Severity, UnbundleRisk


class CrossPolicyFlag(BaseModel):
    flag_type: FlagType
    severity: Severity
    description: str
    affected_policies: list[str]


class BundleAnalysis(BaseModel):
    has_auto: bool
    has_home: bool
    is_bundle: bool
    bundle_discount_eligible: bool
    carrier_mismatch: bool
    unbundle_risk: UnbundleRisk


class PortfolioSummary(BaseModel):
    client_policies: list[str]
    total_premium: float
    total_prior_premium: float
    premium_change_pct: float
    risk_breakdown: dict[str, int]
    bundle_analysis: BundleAnalysis
    cross_policy_flags: list[CrossPolicyFlag]
