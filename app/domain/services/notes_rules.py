from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models.diff import DiffFlag

if TYPE_CHECKING:
    from app.config import NotesKeywords

_CATEGORY_MAP = {
    "claims_history": DiffFlag.CLAIMS_HISTORY,
    "property_risk": DiffFlag.PROPERTY_RISK,
    "regulatory": DiffFlag.REGULATORY,
    "driver_risk": DiffFlag.DRIVER_RISK_NOTE,
}


def flag_notes_keywords(
    notes: str,
    keywords_config: NotesKeywords | None = None,
) -> list[DiffFlag]:
    if not notes:
        return []

    if keywords_config is None:
        from app.config import settings

        keywords_config = settings.notes_keywords

    notes_lower = notes.lower()
    flags: list[DiffFlag] = []

    for category, diff_flag in _CATEGORY_MAP.items():
        keyword_list = getattr(keywords_config, category, [])
        for keyword in keyword_list:
            if keyword.lower() in notes_lower:
                flags.append(diff_flag)
                break

    return flags
