from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class PolicyType(StrEnum):
    AUTO = "auto"
    HOME = "home"


class Endorsement(BaseModel):
    code: str
    description: str
    premium: float = 0.0


class Vehicle(BaseModel):
    vin: str
    year: int
    make: str
    model: str
    usage: str = "personal"


class Driver(BaseModel):
    license_number: str
    name: str
    age: int
    violations: int = 0
    sr22: bool = False


class AutoCoverages(BaseModel):
    bodily_injury_limit: str = "100/300"
    property_damage_limit: str = "100"
    collision_deductible: float = 500.0
    comprehensive_deductible: float = 250.0
    uninsured_motorist: str = "100/300"
    medical_payments: float = 5000.0
    rental_reimbursement: bool = False
    roadside_assistance: bool = False


class HomeCoverages(BaseModel):
    coverage_a_dwelling: float = 300000.0
    coverage_b_other_structures: float = 30000.0
    coverage_c_personal_property: float = 150000.0
    coverage_d_loss_of_use: float = 60000.0
    coverage_e_liability: float = 100000.0
    coverage_f_medical: float = 5000.0
    deductible: float = 1000.0
    wind_hail_deductible: float | None = None
    water_backup: bool = False
    replacement_cost: bool = True


class PolicySnapshot(BaseModel):
    policy_number: str
    policy_type: PolicyType
    carrier: str
    effective_date: date
    expiration_date: date
    premium: float
    state: str = "CA"
    notes: str = ""

    auto_coverages: AutoCoverages | None = None
    home_coverages: HomeCoverages | None = None
    vehicles: list[Vehicle] = []
    drivers: list[Driver] = []
    endorsements: list[Endorsement] = []


class RenewalPair(BaseModel):
    prior: PolicySnapshot
    renewal: PolicySnapshot
