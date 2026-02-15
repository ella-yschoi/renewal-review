from pydantic import BaseModel


class CrossPolicyFlag(BaseModel):
    flag_type: str
    severity: str
    description: str
    affected_policies: list[str]


class BundleAnalysis(BaseModel):
    has_auto: bool
    has_home: bool
    is_bundle: bool
    bundle_discount_eligible: bool
    carrier_mismatch: bool
    unbundle_risk: str


class PortfolioSummary(BaseModel):
    client_policies: list[str]
    total_premium: float
    total_prior_premium: float
    premium_change_pct: float
    risk_breakdown: dict[str, int]
    bundle_analysis: BundleAnalysis
    cross_policy_flags: list[CrossPolicyFlag]
    llm_verdict: str = ""
    llm_recommendations: list[str] = []
    llm_action_items: list[str] = []
    llm_enriched: bool = False
