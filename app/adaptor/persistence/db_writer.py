import logging
from datetime import datetime

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.models.review import ReviewResult
from app.infra.db_models import LLMResultRow, RuleResultRow

logger = logging.getLogger(__name__)


class DbResultWriter:
    def __init__(self):
        sync_url = settings.db_url.replace("+asyncpg", "+psycopg")
        self._engine = create_engine(sync_url)

    def save_rule_result(self, job_id: str, result: ReviewResult) -> None:
        try:
            row = RuleResultRow(
                policy_number=result.policy_number,
                job_id=job_id,
                risk_level=result.risk_level.value,
                flags_json=[f.value for f in result.diff.flags],
                changes_json=[c.model_dump() for c in result.diff.changes],
                summary_text=result.summary,
                broker_contacted=result.broker_contacted,
                quote_generated=result.quote_generated,
                reviewed_at=result.reviewed_at,
            )
            with Session(self._engine) as session:
                session.add(row)
                session.commit()
        except Exception:
            logger.warning("Failed to save rule result for %s", result.policy_number)

    def save_llm_result(self, job_id: str, result: ReviewResult) -> None:
        try:
            row = LLMResultRow(
                policy_number=result.policy_number,
                job_id=job_id,
                risk_level=result.risk_level.value,
                insights_json=[i.model_dump() for i in result.llm_insights],
                summary_text=result.summary,
            )
            with Session(self._engine) as session:
                session.add(row)
                session.commit()
        except Exception:
            logger.warning("Failed to save LLM result for %s", result.policy_number)

    def _update_rule_field(self, policy_number: str, **kwargs) -> None:
        try:
            with Session(self._engine) as session:
                latest = session.execute(
                    select(RuleResultRow)
                    .where(RuleResultRow.policy_number == policy_number)
                    .order_by(RuleResultRow.created_at.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if latest is None:
                    return
                session.execute(
                    update(RuleResultRow).where(RuleResultRow.id == latest.id).values(**kwargs)
                )
                session.commit()
        except Exception:
            logger.warning("Failed to update %s for %s", kwargs, policy_number)

    def update_broker_contacted(self, policy_number: str, value: bool) -> None:
        self._update_rule_field(policy_number, broker_contacted=value)

    def update_quote_generated(self, policy_number: str, value: bool) -> None:
        self._update_rule_field(policy_number, quote_generated=value)

    def update_reviewed_at(self, policy_number: str, value: datetime) -> None:
        self._update_rule_field(policy_number, reviewed_at=value)

    def load_latest_results(self) -> list[dict]:
        try:
            with Session(self._engine) as session:
                subq = (
                    select(
                        RuleResultRow.policy_number,
                        RuleResultRow.id,
                    )
                    .distinct(RuleResultRow.policy_number)
                    .order_by(
                        RuleResultRow.policy_number,
                        RuleResultRow.created_at.desc(),
                    )
                    .subquery()
                )
                rows = (
                    session.execute(
                        select(RuleResultRow).where(RuleResultRow.id.in_(select(subq.c.id)))
                    )
                    .scalars()
                    .all()
                )
                return [
                    {
                        "policy_number": r.policy_number,
                        "job_id": r.job_id,
                        "risk_level": r.risk_level,
                        "flags_json": r.flags_json,
                        "changes_json": r.changes_json,
                        "summary_text": r.summary_text,
                        "broker_contacted": r.broker_contacted,
                        "quote_generated": r.quote_generated,
                        "reviewed_at": r.reviewed_at,
                    }
                    for r in rows
                ]
        except Exception:
            logger.warning("Failed to load results from DB")
            return []

    def load_latest_llm_results(self) -> list[dict]:
        try:
            with Session(self._engine) as session:
                subq = (
                    select(
                        LLMResultRow.policy_number,
                        LLMResultRow.id,
                    )
                    .distinct(LLMResultRow.policy_number)
                    .order_by(
                        LLMResultRow.policy_number,
                        LLMResultRow.created_at.desc(),
                    )
                    .subquery()
                )
                rows = (
                    session.execute(
                        select(LLMResultRow).where(LLMResultRow.id.in_(select(subq.c.id)))
                    )
                    .scalars()
                    .all()
                )
                return [
                    {
                        "policy_number": r.policy_number,
                        "risk_level": r.risk_level,
                        "insights_json": r.insights_json,
                        "summary_text": r.summary_text,
                    }
                    for r in rows
                ]
        except Exception:
            logger.warning("Failed to load LLM results from DB")
            return []

    def dispose(self) -> None:
        self._engine.dispose()
