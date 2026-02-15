from app.config import settings
from app.domain.models.diff import DiffFlag, DiffResult, FieldChange
from app.domain.models.policy import RenewalPair

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
    cfg = settings.rules
    if pct >= cfg.premium_critical_pct:
        flags.append(DiffFlag.PREMIUM_INCREASE_CRITICAL)
    elif pct >= cfg.premium_high_pct:
        flags.append(DiffFlag.PREMIUM_INCREASE_HIGH)
    if pct < 0:
        flags.append(DiffFlag.PREMIUM_DECREASE)
    return flags


def _flag_carrier(pair: RenewalPair) -> list[DiffFlag]:
    if pair.prior.carrier != pair.renewal.carrier:
        return [DiffFlag.CARRIER_CHANGE]
    return []


def _detect_flag(c: FieldChange) -> DiffFlag | None:
    if c.field in LIABILITY_FIELDS:
        if _parse_limit(c.renewal_value) < _parse_limit(c.prior_value):
            return DiffFlag.LIABILITY_LIMIT_DECREASE

    elif c.field in DEDUCTIBLE_FIELDS:
        try:
            if float(c.renewal_value) > float(c.prior_value):
                return DiffFlag.DEDUCTIBLE_INCREASE
        except ValueError:
            pass

    elif c.field in COVERAGE_DROP_FIELDS:
        try:
            if float(c.renewal_value) < float(c.prior_value):
                return DiffFlag.COVERAGE_DROPPED
        except ValueError:
            pass

    elif c.field == "vehicle_added":
        return DiffFlag.VEHICLE_ADDED
    elif c.field == "vehicle_removed":
        return DiffFlag.VEHICLE_REMOVED
    elif c.field == "driver_added":
        return DiffFlag.DRIVER_ADDED
    elif c.field == "driver_removed":
        return DiffFlag.DRIVER_REMOVED
    elif c.field == "endorsement_added":
        return DiffFlag.ENDORSEMENT_ADDED
    elif c.field == "endorsement_removed":
        return DiffFlag.ENDORSEMENT_REMOVED
    elif c.field == "notes":
        return DiffFlag.NOTES_CHANGED

    # boolean coverage drops (True→False)
    elif (
        c.prior_value == "True"
        and c.renewal_value == "False"
        and c.field in {"water_backup", "replacement_cost", "rental_reimbursement"}
    ):
        return DiffFlag.COVERAGE_DROPPED

    # boolean coverage adds (False→True)
    elif (
        c.prior_value == "False"
        and c.renewal_value == "True"
        and c.field
        in {"water_backup", "replacement_cost", "rental_reimbursement", "roadside_assistance"}
    ):
        return DiffFlag.COVERAGE_ADDED

    return None


def _flag_changes(changes: list[FieldChange]) -> tuple[list[DiffFlag], list[FieldChange]]:
    flags: list[DiffFlag] = []
    updated: list[FieldChange] = []
    for c in changes:
        detected = _detect_flag(c)
        if detected is not None:
            flags.append(detected)
            updated.append(c.model_copy(update={"flag": detected}))
        else:
            updated.append(c)
    return flags, updated


def flag_diff(diff: DiffResult, pair: RenewalPair) -> DiffResult:
    flags: list[DiffFlag] = []
    flags.extend(_flag_premium(pair))
    flags.extend(_flag_carrier(pair))
    change_flags, updated_changes = _flag_changes(diff.changes)
    flags.extend(change_flags)

    # premium flags also annotate the premium change
    premium_flags = {
        DiffFlag.PREMIUM_INCREASE_HIGH,
        DiffFlag.PREMIUM_INCREASE_CRITICAL,
        DiffFlag.PREMIUM_DECREASE,
    }
    final_changes: list[FieldChange] = []
    for c in updated_changes:
        if c.field == "premium" and c.flag is None:
            premium_flag = next((f for f in flags if f in premium_flags), None)
            if premium_flag is not None:
                final_changes.append(c.model_copy(update={"flag": premium_flag}))
                continue
        final_changes.append(c)

    return DiffResult(
        policy_number=diff.policy_number,
        changes=final_changes,
        flags=list(set(flags)),
    )
