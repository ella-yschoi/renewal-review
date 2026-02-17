from collections.abc import Callable, Sequence
from typing import TypeVar

from app.domain.models.diff import DiffResult, FieldChange
from app.domain.models.policy import (
    AutoCoverages,
    HomeCoverages,
    PolicySnapshot,
    RenewalPair,
)

T = TypeVar("T")


def _pct_change(prior: float, renewal: float) -> float | None:
    if prior == 0:
        return None
    return round((renewal - prior) / prior * 100, 2)


def _str_change(field: str, prior: str, renewal: str) -> FieldChange | None:
    if prior == renewal:
        return None
    return FieldChange(field=field, prior_value=prior, renewal_value=renewal)


def _num_change(field: str, prior: float, renewal: float) -> FieldChange | None:
    if prior == renewal:
        return None
    return FieldChange(
        field=field,
        prior_value=str(prior),
        renewal_value=str(renewal),
        change_pct=_pct_change(prior, renewal),
    )


def _bool_change(field: str, prior: bool, renewal: bool) -> FieldChange | None:
    if prior == renewal:
        return None
    return FieldChange(field=field, prior_value=str(prior), renewal_value=str(renewal))


def _diff_entities[T](
    prior_items: Sequence[T],
    renewal_items: Sequence[T],
    key_fn: Callable[[T], str],
    label_fn: Callable[[T], str],
    added_field: str,
    removed_field: str,
) -> list[FieldChange]:
    prior_keys = {key_fn(x) for x in prior_items}
    renewal_keys = {key_fn(x) for x in renewal_items}
    changes: list[FieldChange] = []
    for k in renewal_keys - prior_keys:
        item = next(x for x in renewal_items if key_fn(x) == k)
        label = label_fn(item)
        changes.append(FieldChange(field=added_field, prior_value="", renewal_value=label))
    for k in prior_keys - renewal_keys:
        item = next(x for x in prior_items if key_fn(x) == k)
        label = label_fn(item)
        changes.append(FieldChange(field=removed_field, prior_value=label, renewal_value=""))
    return changes


def diff_universal_fields(prior: PolicySnapshot, renewal: PolicySnapshot) -> list[FieldChange]:
    changes: list[FieldChange] = []

    if c := _num_change("premium", prior.premium, renewal.premium):
        changes.append(c)
    if c := _str_change("carrier", prior.carrier, renewal.carrier):
        changes.append(c)
    if c := _str_change("notes", prior.notes, renewal.notes):
        changes.append(c)

    return changes


def diff_auto_coverages(
    prior: AutoCoverages | None, renewal: AutoCoverages | None
) -> list[FieldChange]:
    if prior is None or renewal is None:
        return []

    changes: list[FieldChange] = []
    field_pairs = [
        ("bodily_injury_limit", prior.bodily_injury_limit, renewal.bodily_injury_limit),
        ("property_damage_limit", prior.property_damage_limit, renewal.property_damage_limit),
        ("uninsured_motorist", prior.uninsured_motorist, renewal.uninsured_motorist),
    ]
    for field, p, r in field_pairs:
        if c := _str_change(field, p, r):
            changes.append(c)

    num_pairs = [
        ("collision_deductible", prior.collision_deductible, renewal.collision_deductible),
        (
            "comprehensive_deductible",
            prior.comprehensive_deductible,
            renewal.comprehensive_deductible,
        ),
        ("medical_payments", prior.medical_payments, renewal.medical_payments),
    ]
    for field, p, r in num_pairs:
        if c := _num_change(field, p, r):
            changes.append(c)

    for field, p, r in [
        ("rental_reimbursement", prior.rental_reimbursement, renewal.rental_reimbursement),
        ("roadside_assistance", prior.roadside_assistance, renewal.roadside_assistance),
    ]:
        if c := _bool_change(field, p, r):
            changes.append(c)

    return changes


def diff_home_coverages(
    prior: HomeCoverages | None, renewal: HomeCoverages | None
) -> list[FieldChange]:
    if prior is None or renewal is None:
        return []

    changes: list[FieldChange] = []
    num_fields = [
        ("coverage_a_dwelling", prior.coverage_a_dwelling, renewal.coverage_a_dwelling),
        (
            "coverage_b_other_structures",
            prior.coverage_b_other_structures,
            renewal.coverage_b_other_structures,
        ),
        (
            "coverage_c_personal_property",
            prior.coverage_c_personal_property,
            renewal.coverage_c_personal_property,
        ),
        ("coverage_d_loss_of_use", prior.coverage_d_loss_of_use, renewal.coverage_d_loss_of_use),
        ("coverage_e_liability", prior.coverage_e_liability, renewal.coverage_e_liability),
        ("coverage_f_medical", prior.coverage_f_medical, renewal.coverage_f_medical),
        ("deductible", prior.deductible, renewal.deductible),
    ]
    for field, p, r in num_fields:
        if c := _num_change(field, p, r):
            changes.append(c)

    p_whd = prior.wind_hail_deductible or 0
    r_whd = renewal.wind_hail_deductible or 0
    if c := _num_change("wind_hail_deductible", p_whd, r_whd):
        changes.append(c)

    for field, p, r in [
        ("water_backup", prior.water_backup, renewal.water_backup),
        ("replacement_cost", prior.replacement_cost, renewal.replacement_cost),
    ]:
        if c := _bool_change(field, p, r):
            changes.append(c)

    return changes


def diff_vehicles(prior: PolicySnapshot, renewal: PolicySnapshot) -> list[FieldChange]:
    return _diff_entities(
        prior.vehicles,
        renewal.vehicles,
        key_fn=lambda v: v.vin,
        label_fn=lambda v: f"{v.year} {v.make} {v.model} ({v.vin})",
        added_field="vehicle_added",
        removed_field="vehicle_removed",
    )


def diff_drivers(prior: PolicySnapshot, renewal: PolicySnapshot) -> list[FieldChange]:
    return _diff_entities(
        prior.drivers,
        renewal.drivers,
        key_fn=lambda d: d.license_number,
        label_fn=lambda d: f"{d.name} ({d.license_number})",
        added_field="driver_added",
        removed_field="driver_removed",
    )


def diff_endorsements(prior: PolicySnapshot, renewal: PolicySnapshot) -> list[FieldChange]:
    prior_codes = {e.code for e in prior.endorsements}
    renewal_codes = {e.code for e in renewal.endorsements}

    changes: list[FieldChange] = []
    for code in renewal_codes - prior_codes:
        e = next(x for x in renewal.endorsements if x.code == code)
        changes.append(
            FieldChange(
                field="endorsement_added", prior_value="", renewal_value=f"{code}: {e.description}"
            )
        )
    for code in prior_codes - renewal_codes:
        e = next(x for x in prior.endorsements if x.code == code)
        changes.append(
            FieldChange(
                field="endorsement_removed",
                prior_value=f"{code}: {e.description}",
                renewal_value="",
            )
        )

    for code in prior_codes & renewal_codes:
        pe = next(x for x in prior.endorsements if x.code == code)
        re = next(x for x in renewal.endorsements if x.code == code)
        if pe.description != re.description:
            changes.append(
                FieldChange(
                    field=f"endorsement_description_{code}",
                    prior_value=pe.description,
                    renewal_value=re.description,
                )
            )
        if pe.premium != re.premium:
            changes.append(
                FieldChange(
                    field=f"endorsement_premium_{code}",
                    prior_value=str(pe.premium),
                    renewal_value=str(re.premium),
                    change_pct=_pct_change(pe.premium, re.premium),
                )
            )

    return changes


def compute_diff(pair: RenewalPair) -> DiffResult:
    prior, renewal = pair.prior, pair.renewal
    all_changes: list[FieldChange] = []

    all_changes.extend(diff_universal_fields(prior, renewal))
    all_changes.extend(diff_auto_coverages(prior.auto_coverages, renewal.auto_coverages))
    all_changes.extend(diff_home_coverages(prior.home_coverages, renewal.home_coverages))
    all_changes.extend(diff_vehicles(prior, renewal))
    all_changes.extend(diff_drivers(prior, renewal))
    all_changes.extend(diff_endorsements(prior, renewal))

    return DiffResult(policy_number=prior.policy_number, changes=all_changes)
