from typing import Any

from app.models.policy import (
    AutoCoverages,
    Driver,
    Endorsement,
    HomeCoverages,
    PolicySnapshot,
    PolicyType,
    RenewalPair,
    Vehicle,
)


def _normalize_date(val: str) -> str:
    return val.strip().replace("/", "-")


def _parse_vehicles(raw_list: list[dict[str, Any]]) -> list[Vehicle]:
    return [
        Vehicle(
            vin=v["vin"].strip().upper(),
            year=int(v["year"]),
            make=v["make"].strip(),
            model=v["model"].strip(),
            usage=v.get("usage", "personal"),
        )
        for v in raw_list
    ]


def _parse_drivers(raw_list: list[dict[str, Any]]) -> list[Driver]:
    return [
        Driver(
            license_number=d["license_number"].strip().upper(),
            name=d["name"].strip(),
            age=int(d["age"]),
            violations=int(d.get("violations", 0)),
            sr22=bool(d.get("sr22", False)),
        )
        for d in raw_list
    ]


def _parse_endorsements(raw_list: list[dict[str, Any]]) -> list[Endorsement]:
    return [
        Endorsement(
            code=e["code"].strip().upper(),
            description=e.get("description", "").strip(),
            premium=float(e.get("premium", 0)),
        )
        for e in raw_list
    ]


def parse_snapshot(raw: dict[str, Any]) -> PolicySnapshot:
    policy_type = PolicyType(raw["policy_type"].lower())

    auto_coverages = None
    home_coverages = None

    if policy_type == PolicyType.AUTO and "auto_coverages" in raw:
        ac = raw["auto_coverages"]
        auto_coverages = AutoCoverages(
            bodily_injury_limit=str(ac.get("bodily_injury_limit", "100/300")),
            property_damage_limit=str(ac.get("property_damage_limit", "100")),
            collision_deductible=float(ac.get("collision_deductible", 500)),
            comprehensive_deductible=float(ac.get("comprehensive_deductible", 250)),
            uninsured_motorist=str(ac.get("uninsured_motorist", "100/300")),
            medical_payments=float(ac.get("medical_payments", 5000)),
            rental_reimbursement=bool(ac.get("rental_reimbursement", False)),
            roadside_assistance=bool(ac.get("roadside_assistance", False)),
        )

    if policy_type == PolicyType.HOME and "home_coverages" in raw:
        hc = raw["home_coverages"]
        home_coverages = HomeCoverages(
            coverage_a_dwelling=float(hc.get("coverage_a_dwelling", 300000)),
            coverage_b_other_structures=float(hc.get("coverage_b_other_structures", 30000)),
            coverage_c_personal_property=float(hc.get("coverage_c_personal_property", 150000)),
            coverage_d_loss_of_use=float(hc.get("coverage_d_loss_of_use", 60000)),
            coverage_e_liability=float(hc.get("coverage_e_liability", 100000)),
            coverage_f_medical=float(hc.get("coverage_f_medical", 5000)),
            deductible=float(hc.get("deductible", 1000)),
            wind_hail_deductible=(
                float(hc["wind_hail_deductible"]) if hc.get("wind_hail_deductible") else None
            ),
            water_backup=bool(hc.get("water_backup", False)),
            replacement_cost=bool(hc.get("replacement_cost", True)),
        )

    return PolicySnapshot(
        policy_number=raw["policy_number"].strip(),
        policy_type=policy_type,
        carrier=raw["carrier"].strip(),
        effective_date=_normalize_date(raw["effective_date"]),
        expiration_date=_normalize_date(raw["expiration_date"]),
        premium=float(raw["premium"]),
        state=raw.get("state", "CA").strip().upper(),
        notes=raw.get("notes", "").strip(),
        auto_coverages=auto_coverages,
        home_coverages=home_coverages,
        vehicles=_parse_vehicles(raw.get("vehicles", [])),
        drivers=_parse_drivers(raw.get("drivers", [])),
        endorsements=_parse_endorsements(raw.get("endorsements", [])),
    )


def parse_pair(raw: dict[str, Any]) -> RenewalPair:
    return RenewalPair(
        prior=parse_snapshot(raw["prior"]),
        renewal=parse_snapshot(raw["renewal"]),
    )
