from app.models.diff import DiffFlag, DiffResult, FieldChange
from app.models.policy import RenewalPair

PREMIUM_THRESHOLD_HIGH = 10.0
PREMIUM_THRESHOLD_CRITICAL = 20.0

LIABILITY_FIELDS = {
    "bodily_injury_limit",
    "property_damage_limit",
    "coverage_e_liability",
    "uninsured_motorist",
}

DEDUCTIBLE_FIELDS = {
    "collision_deductible",
    "comprehensive_deductible",
    "deductible",
    "wind_hail_deductible",
}

COVERAGE_DROP_FIELDS = {
    "coverage_a_dwelling",
    "coverage_b_other_structures",
    "coverage_c_personal_property",
    "coverage_d_loss_of_use",
    "coverage_f_medical",
    "medical_payments",
}


def _parse_limit(val: str) -> float:
    parts = val.replace(",", "").split("/")
    return sum(float(p) for p in parts)


def _flag_premium(pair: RenewalPair) -> list[DiffFlag]:
    prior_p, renewal_p = pair.prior.premium, pair.renewal.premium
    if prior_p == 0:
        return []
    pct = (renewal_p - prior_p) / prior_p * 100
    flags: list[DiffFlag] = []
    if pct >= PREMIUM_THRESHOLD_CRITICAL:
        flags.append(DiffFlag.PREMIUM_INCREASE_CRITICAL)
    elif pct >= PREMIUM_THRESHOLD_HIGH:
        flags.append(DiffFlag.PREMIUM_INCREASE_HIGH)
    if pct < 0:
        flags.append(DiffFlag.PREMIUM_DECREASE)
    return flags


def _flag_carrier(pair: RenewalPair) -> list[DiffFlag]:
    if pair.prior.carrier != pair.renewal.carrier:
        return [DiffFlag.CARRIER_CHANGE]
    return []


def _flag_changes(changes: list[FieldChange]) -> list[DiffFlag]:
    flags: list[DiffFlag] = []
    for c in changes:
        if c.field in LIABILITY_FIELDS:
            prior_val = _parse_limit(c.prior_value)
            renewal_val = _parse_limit(c.renewal_value)
            if renewal_val < prior_val:
                c.flag = DiffFlag.LIABILITY_LIMIT_DECREASE
                flags.append(DiffFlag.LIABILITY_LIMIT_DECREASE)

        elif c.field in DEDUCTIBLE_FIELDS:
            try:
                if float(c.renewal_value) > float(c.prior_value):
                    c.flag = DiffFlag.DEDUCTIBLE_INCREASE
                    flags.append(DiffFlag.DEDUCTIBLE_INCREASE)
            except ValueError:
                pass

        elif c.field in COVERAGE_DROP_FIELDS:
            try:
                if float(c.renewal_value) < float(c.prior_value):
                    c.flag = DiffFlag.COVERAGE_DROPPED
                    flags.append(DiffFlag.COVERAGE_DROPPED)
            except ValueError:
                pass

        elif c.field == "vehicle_added":
            c.flag = DiffFlag.VEHICLE_ADDED
            flags.append(DiffFlag.VEHICLE_ADDED)
        elif c.field == "vehicle_removed":
            c.flag = DiffFlag.VEHICLE_REMOVED
            flags.append(DiffFlag.VEHICLE_REMOVED)
        elif c.field == "driver_added":
            c.flag = DiffFlag.DRIVER_ADDED
            flags.append(DiffFlag.DRIVER_ADDED)
        elif c.field == "driver_removed":
            c.flag = DiffFlag.DRIVER_REMOVED
            flags.append(DiffFlag.DRIVER_REMOVED)
        elif c.field == "endorsement_added":
            c.flag = DiffFlag.ENDORSEMENT_ADDED
            flags.append(DiffFlag.ENDORSEMENT_ADDED)
        elif c.field == "endorsement_removed":
            c.flag = DiffFlag.ENDORSEMENT_REMOVED
            flags.append(DiffFlag.ENDORSEMENT_REMOVED)
        elif c.field == "notes":
            c.flag = DiffFlag.NOTES_CHANGED
            flags.append(DiffFlag.NOTES_CHANGED)

        # boolean coverage drops (True→False)
        elif c.prior_value == "True" and c.renewal_value == "False":
            if c.field in {"water_backup", "replacement_cost", "rental_reimbursement"}:
                c.flag = DiffFlag.COVERAGE_DROPPED
                flags.append(DiffFlag.COVERAGE_DROPPED)

        # boolean coverage adds (False→True)
        elif c.prior_value == "False" and c.renewal_value == "True":
            if c.field in {
                "water_backup",
                "replacement_cost",
                "rental_reimbursement",
                "roadside_assistance",
            }:
                c.flag = DiffFlag.COVERAGE_ADDED
                flags.append(DiffFlag.COVERAGE_ADDED)

    return flags


def flag_diff(diff: DiffResult, pair: RenewalPair) -> DiffResult:
    flags: list[DiffFlag] = []
    flags.extend(_flag_premium(pair))
    flags.extend(_flag_carrier(pair))
    flags.extend(_flag_changes(diff.changes))

    # premium flags also annotate the premium change
    premium_flags = {
        DiffFlag.PREMIUM_INCREASE_HIGH,
        DiffFlag.PREMIUM_INCREASE_CRITICAL,
        DiffFlag.PREMIUM_DECREASE,
    }
    for c in diff.changes:
        if c.field == "premium" and c.flag is None:
            for f in flags:
                if f in premium_flags:
                    c.flag = f
                    break

    diff.flags = list(set(flags))
    return diff
