"""Generate 8,000 mock renewal pairs for demo."""

import json
import random
from datetime import date, timedelta
from pathlib import Path

CARRIERS = [
    "StateFarm",
    "Allstate",
    "GEICO",
    "Progressive",
    "USAA",
    "Liberty Mutual",
    "Farmers",
    "Nationwide",
    "Travelers",
    "American Family",
]

ENDORSEMENT_CODES_AUTO = [
    ("UM100", "Uninsured motorist coverage enhancement"),
    ("RSA01", "Roadside assistance package"),
    ("GAP01", "Gap insurance coverage"),
    ("RNT01", "Rental reimbursement"),
    ("ACC01", "Accident forgiveness"),
]

ENDORSEMENT_CODES_HOME = [
    ("HO 04 61", "Scheduled personal property"),
    ("HO 04 95", "Water backup and sump overflow coverage"),
    ("ID01", "Identity theft protection"),
    ("EQ01", "Earthquake coverage endorsement"),
    ("FL01", "Flood insurance supplement"),
]

STATES = ["CA", "TX", "FL", "NY", "IL", "PA", "OH", "GA", "NC", "MI"]

MAKES_MODELS = [
    ("Honda", "Civic"),
    ("Toyota", "Camry"),
    ("Ford", "F-150"),
    ("Chevrolet", "Equinox"),
    ("Tesla", "Model 3"),
    ("Hyundai", "Tucson"),
    ("BMW", "X3"),
    ("Nissan", "Altima"),
    ("Subaru", "Outback"),
    ("Mazda", "CX-5"),
]

NOTES_POOL = [
    "Premium increase due to regional rate adjustment",
    "Inflation guard applied to dwelling coverage",
    "Claim filed last year for water damage — monitor for rate impact",
    "New teen driver added — high risk profile",
    "SR-22 filing required per state mandate",
    "Roof age exceeds 20 years — consider replacement discount eligibility",
    "Bundle discount removed — auto policy moved to different carrier",
    "Credit score improvement — may qualify for preferred tier next renewal",
    "Hail damage claim pending from Q3 — watch for surcharge",
    "Dog breed exclusion may apply — verify liability coverage adequacy",
    "Home security system installed — potential discount next term",
    "Swimming pool added — liability exposure increased",
    "Policy was non-renewed by prior carrier due to loss history",
    "Underwriting review recommended for consecutive claim years",
    "Garage kept vehicle — usage verified via telematics data",
]


def _random_vin() -> str:
    chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"
    return "".join(random.choices(chars, k=17))


def _random_date_2024() -> date:
    start = date(2024, 1, 1)
    return start + timedelta(days=random.randint(0, 364))


def _make_auto_pair(idx: int) -> dict:
    policy_num = f"AUTO-2024-{idx:04d}"
    state = random.choice(STATES)
    carrier = random.choice(CARRIERS)
    eff = _random_date_2024()
    exp = eff + timedelta(days=365)

    base_premium = round(random.uniform(600, 4000), 2)

    # prior coverages
    bi_options = ["25/50", "50/100", "100/300", "250/500"]
    pd_options = ["25", "50", "100"]
    bi = random.choice(bi_options)
    pd = random.choice(pd_options)
    coll_ded = random.choice([250, 500, 1000])
    comp_ded = random.choice([100, 250, 500])

    n_vehicles = random.randint(1, 3)
    vehicles = []
    for _ in range(n_vehicles):
        make, model = random.choice(MAKES_MODELS)
        vehicles.append(
            {
                "vin": _random_vin(),
                "year": random.randint(2015, 2024),
                "make": make,
                "model": model,
                "usage": random.choice(["personal", "commute", "business"]),
            }
        )

    n_drivers = random.randint(1, 3)
    drivers = []
    for j in range(n_drivers):
        drivers.append(
            {
                "license_number": f"D{random.randint(1000000, 9999999)}",
                "name": f"Driver {idx}-{j}",
                "age": random.randint(16, 75),
                "violations": random.choice([0, 0, 0, 1, 1, 2, 3]),
                "sr22": random.random() < 0.03,
            }
        )

    n_endorsements = random.randint(0, 3)
    codes = random.sample(ENDORSEMENT_CODES_AUTO, min(n_endorsements, len(ENDORSEMENT_CODES_AUTO)))
    endorsements = [
        {"code": c, "description": d, "premium": round(random.uniform(10, 80), 2)}
        for c, d in codes
    ]

    prior = {
        "policy_number": policy_num,
        "policy_type": "auto",
        "carrier": carrier,
        "effective_date": str(eff),
        "expiration_date": str(exp),
        "premium": base_premium,
        "state": state,
        "notes": "",
        "auto_coverages": {
            "bodily_injury_limit": bi,
            "property_damage_limit": pd,
            "collision_deductible": coll_ded,
            "comprehensive_deductible": comp_ded,
            "uninsured_motorist": bi,
            "medical_payments": random.choice([1000, 2000, 5000, 10000]),
            "rental_reimbursement": random.random() < 0.4,
            "roadside_assistance": random.random() < 0.3,
        },
        "vehicles": vehicles,
        "drivers": drivers,
        "endorsements": endorsements,
    }

    # build renewal with variations
    renewal = json.loads(json.dumps(prior))
    renewal["effective_date"] = str(exp)
    renewal["expiration_date"] = str(exp + timedelta(days=365))

    # premium always changes
    pct = random.gauss(6, 8)
    renewal["premium"] = round(base_premium * (1 + pct / 100), 2)

    # carrier change (5%)
    if random.random() < 0.05:
        renewal["carrier"] = random.choice([c for c in CARRIERS if c != carrier])

    # liability decrease (8%)
    if random.random() < 0.08:
        lower_bi = ["25/50", "50/100"]
        renewal["auto_coverages"]["bodily_injury_limit"] = random.choice(lower_bi)

    # deductible increase (12%)
    if random.random() < 0.12:
        renewal["auto_coverages"]["collision_deductible"] = coll_ded + 250

    # vehicle change (10%)
    if random.random() < 0.10:
        make, model = random.choice(MAKES_MODELS)
        renewal["vehicles"].append(
            {
                "vin": _random_vin(),
                "year": random.randint(2023, 2025),
                "make": make,
                "model": model,
                "usage": "personal",
            }
        )
    if len(renewal["vehicles"]) > 1 and random.random() < 0.05:
        renewal["vehicles"].pop(0)

    # endorsement churn (20%)
    if random.random() < 0.20:
        available = [
            c
            for c in ENDORSEMENT_CODES_AUTO
            if c[0] not in {e["code"] for e in renewal["endorsements"]}
        ]
        if available:
            c, d = random.choice(available)
            renewal["endorsements"].append(
                {"code": c, "description": d, "premium": round(random.uniform(15, 60), 2)}
            )
    if renewal["endorsements"] and random.random() < 0.10:
        renewal["endorsements"].pop(random.randint(0, len(renewal["endorsements"]) - 1))

    # notes (30%)
    if random.random() < 0.30:
        renewal["notes"] = random.choice(NOTES_POOL)

    return {"prior": prior, "renewal": renewal}


def _make_home_pair(idx: int) -> dict:
    policy_num = f"HOME-2024-{idx:04d}"
    state = random.choice(STATES)
    carrier = random.choice(CARRIERS)
    eff = _random_date_2024()
    exp = eff + timedelta(days=365)

    base_premium = round(random.uniform(1200, 6000), 2)
    dwelling = round(random.uniform(150000, 800000), -3)

    prior = {
        "policy_number": policy_num,
        "policy_type": "home",
        "carrier": carrier,
        "effective_date": str(eff),
        "expiration_date": str(exp),
        "premium": base_premium,
        "state": state,
        "notes": "",
        "home_coverages": {
            "coverage_a_dwelling": dwelling,
            "coverage_b_other_structures": round(dwelling * 0.10),
            "coverage_c_personal_property": round(dwelling * 0.50),
            "coverage_d_loss_of_use": round(dwelling * 0.20),
            "coverage_e_liability": random.choice([100000, 300000, 500000]),
            "coverage_f_medical": random.choice([1000, 2500, 5000]),
            "deductible": random.choice([500, 1000, 1500, 2500]),
            "wind_hail_deductible": (
                random.choice([1000, 2500, 5000]) if state in ("TX", "FL", "NC") else None
            ),
            "water_backup": random.random() < 0.5,
            "replacement_cost": random.random() < 0.8,
        },
        "endorsements": [],
    }

    n_endorsements = random.randint(0, 3)
    codes = random.sample(ENDORSEMENT_CODES_HOME, min(n_endorsements, len(ENDORSEMENT_CODES_HOME)))
    prior["endorsements"] = [
        {"code": c, "description": d, "premium": round(random.uniform(30, 150), 2)}
        for c, d in codes
    ]

    renewal = json.loads(json.dumps(prior))
    renewal["effective_date"] = str(exp)
    renewal["expiration_date"] = str(exp + timedelta(days=365))

    # premium change
    pct = random.gauss(8, 10)
    renewal["premium"] = round(base_premium * (1 + pct / 100), 2)

    # inflation guard (70%)
    if random.random() < 0.70:
        guard_pct = random.uniform(2, 6)
        hc = renewal["home_coverages"]
        hc["coverage_a_dwelling"] = round(dwelling * (1 + guard_pct / 100))
        hc["coverage_b_other_structures"] = round(hc["coverage_a_dwelling"] * 0.10)
        hc["coverage_c_personal_property"] = round(hc["coverage_a_dwelling"] * 0.50)
        hc["coverage_d_loss_of_use"] = round(hc["coverage_a_dwelling"] * 0.20)

    # deductible increase (15%)
    if random.random() < 0.15:
        current = renewal["home_coverages"]["deductible"]
        renewal["home_coverages"]["deductible"] = current + 500

    # wind/hail deductible increase (10% for applicable states)
    if renewal["home_coverages"].get("wind_hail_deductible") and random.random() < 0.10:
        current = renewal["home_coverages"]["wind_hail_deductible"]
        renewal["home_coverages"]["wind_hail_deductible"] = current + 2500

    # coverage drops (8%)
    if random.random() < 0.08:
        renewal["home_coverages"]["water_backup"] = False

    # carrier change (5%)
    if random.random() < 0.05:
        renewal["carrier"] = random.choice([c for c in CARRIERS if c != carrier])

    # endorsement churn (20%)
    if random.random() < 0.20:
        available = [
            c
            for c in ENDORSEMENT_CODES_HOME
            if c[0] not in {e["code"] for e in renewal["endorsements"]}
        ]
        if available:
            c, d = random.choice(available)
            renewal["endorsements"].append(
                {"code": c, "description": d, "premium": round(random.uniform(30, 150), 2)}
            )
    if renewal["endorsements"] and random.random() < 0.10:
        renewal["endorsements"].pop(random.randint(0, len(renewal["endorsements"]) - 1))

    # notes (30%)
    if random.random() < 0.30:
        renewal["notes"] = random.choice(NOTES_POOL)

    return {"prior": prior, "renewal": renewal}


def main():
    random.seed(42)
    pairs = []

    for i in range(4800):
        pairs.append(_make_auto_pair(i))
    for i in range(3200):
        pairs.append(_make_home_pair(i))

    random.shuffle(pairs)

    out_path = Path(__file__).parent / "renewals.json"
    out_path.write_text(json.dumps(pairs, indent=None, separators=(",", ":")))

    total_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"Generated {len(pairs)} renewal pairs → {out_path} ({total_mb:.1f} MB)")

    auto_count = sum(1 for p in pairs if p["prior"]["policy_type"] == "auto")
    home_count = len(pairs) - auto_count
    notes_count = sum(1 for p in pairs if p["renewal"].get("notes"))
    print(f"  Auto: {auto_count}, Home: {home_count}, With notes: {notes_count}")


if __name__ == "__main__":
    main()
