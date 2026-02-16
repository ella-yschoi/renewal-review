from app.config import NotesKeywords
from app.domain.models.diff import DiffFlag
from app.domain.services.notes_rules import flag_notes_keywords


def test_empty_notes():
    assert flag_notes_keywords("") == []


def test_claims_keyword():
    flags = flag_notes_keywords("Prior claim filed in 2023")
    assert DiffFlag.CLAIMS_HISTORY in flags


def test_property_risk_keyword():
    flags = flag_notes_keywords("Roof replacement needed per inspection")
    assert DiffFlag.PROPERTY_RISK in flags


def test_regulatory_keyword():
    flags = flag_notes_keywords("Non-renewal notice issued by carrier")
    assert DiffFlag.REGULATORY in flags


def test_driver_risk_keyword():
    flags = flag_notes_keywords("Driver has DUI on record")
    assert DiffFlag.DRIVER_RISK_NOTE in flags


def test_multiple_categories():
    flags = flag_notes_keywords("DUI driver with prior claim and roof damage")
    assert DiffFlag.DRIVER_RISK_NOTE in flags
    assert DiffFlag.CLAIMS_HISTORY in flags
    assert DiffFlag.PROPERTY_RISK in flags


def test_case_insensitive():
    flags = flag_notes_keywords("FLOOD ZONE property")
    assert DiffFlag.PROPERTY_RISK in flags


def test_no_match():
    flags = flag_notes_keywords("Standard renewal, no changes")
    assert flags == []


def test_custom_keywords_config():
    cfg = NotesKeywords(
        claims_history=["custom_keyword"],
        property_risk=[],
        regulatory=[],
        driver_risk=[],
    )
    flags = flag_notes_keywords("Found custom_keyword in text", keywords_config=cfg)
    assert DiffFlag.CLAIMS_HISTORY in flags
    assert len(flags) == 1
