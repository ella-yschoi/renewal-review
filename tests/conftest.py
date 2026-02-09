import json
from pathlib import Path

import pytest

from app.engine.parser import parse_pair
from app.models.policy import RenewalPair

SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"


@pytest.fixture
def auto_pair_raw() -> dict:
    return json.loads((SAMPLES_DIR / "auto_pair.json").read_text())


@pytest.fixture
def home_pair_raw() -> dict:
    return json.loads((SAMPLES_DIR / "home_pair.json").read_text())


@pytest.fixture
def auto_pair(auto_pair_raw: dict) -> RenewalPair:
    return parse_pair(auto_pair_raw)


@pytest.fixture
def home_pair(home_pair_raw: dict) -> RenewalPair:
    return parse_pair(home_pair_raw)
