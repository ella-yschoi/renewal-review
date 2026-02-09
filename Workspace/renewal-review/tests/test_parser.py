from app.engine.parser import parse_pair, parse_snapshot
from app.models.policy import PolicyType, RenewalPair


def test_parse_auto_snapshot(auto_pair_raw: dict):
    snap = parse_snapshot(auto_pair_raw["prior"])
    assert snap.policy_number == "AUTO-2024-001"
    assert snap.policy_type == PolicyType.AUTO
    assert snap.premium == 1200.0
    assert snap.auto_coverages is not None
    assert snap.auto_coverages.bodily_injury_limit == "100/300"


def test_parse_home_snapshot(home_pair_raw: dict):
    snap = parse_snapshot(home_pair_raw["prior"])
    assert snap.policy_type == PolicyType.HOME
    assert snap.home_coverages is not None
    assert snap.home_coverages.coverage_a_dwelling == 350000


def test_parse_vehicles(auto_pair_raw: dict):
    snap = parse_snapshot(auto_pair_raw["renewal"])
    assert len(snap.vehicles) == 2
    assert snap.vehicles[0].vin == "1HGBH41JXMN109186"
    assert snap.vehicles[1].make == "Tesla"


def test_parse_drivers(auto_pair_raw: dict):
    snap = parse_snapshot(auto_pair_raw["prior"])
    assert len(snap.drivers) == 1
    assert snap.drivers[0].license_number == "D1234567"


def test_parse_endorsements(auto_pair_raw: dict):
    snap = parse_snapshot(auto_pair_raw["renewal"])
    assert len(snap.endorsements) == 2
    assert snap.endorsements[0].code == "UM100"


def test_parse_pair(auto_pair_raw: dict):
    pair = parse_pair(auto_pair_raw)
    assert isinstance(pair, RenewalPair)
    assert pair.prior.policy_number == pair.renewal.policy_number


def test_normalize_dates(auto_pair_raw: dict):
    auto_pair_raw["prior"]["effective_date"] = "2024/01/15"
    snap = parse_snapshot(auto_pair_raw["prior"])
    assert str(snap.effective_date) == "2024-01-15"


def test_parse_notes(auto_pair_raw: dict):
    snap = parse_snapshot(auto_pair_raw["renewal"])
    assert "regional rate adjustment" in snap.notes
