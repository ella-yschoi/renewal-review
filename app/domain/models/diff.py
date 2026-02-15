from enum import StrEnum

from pydantic import BaseModel


class DiffFlag(StrEnum):
    PREMIUM_INCREASE_HIGH = "premium_increase_high"
    PREMIUM_INCREASE_CRITICAL = "premium_increase_critical"
    PREMIUM_DECREASE = "premium_decrease"
    CARRIER_CHANGE = "carrier_change"
    LIABILITY_LIMIT_DECREASE = "liability_limit_decrease"
    DEDUCTIBLE_INCREASE = "deductible_increase"
    COVERAGE_DROPPED = "coverage_dropped"
    COVERAGE_ADDED = "coverage_added"
    VEHICLE_ADDED = "vehicle_added"
    VEHICLE_REMOVED = "vehicle_removed"
    DRIVER_ADDED = "driver_added"
    DRIVER_REMOVED = "driver_removed"
    ENDORSEMENT_ADDED = "endorsement_added"
    ENDORSEMENT_REMOVED = "endorsement_removed"
    NOTES_CHANGED = "notes_changed"


class FieldChange(BaseModel):
    field: str
    prior_value: str
    renewal_value: str
    change_pct: float | None = None
    flag: DiffFlag | None = None


class DiffResult(BaseModel):
    policy_number: str
    changes: list[FieldChange] = []
    flags: list[DiffFlag] = []
