from datetime import date, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db import Base


class RenewalPairRow(Base):
    __tablename__ = "raw_renewals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_number: Mapped[str] = mapped_column(String(50), index=True)
    policy_type: Mapped[str] = mapped_column(String(10))
    carrier_prior: Mapped[str] = mapped_column(String(100))
    carrier_renewal: Mapped[str] = mapped_column(String(100))
    premium_prior: Mapped[float] = mapped_column(Float)
    premium_renewal: Mapped[float] = mapped_column(Float)
    effective_date_prior: Mapped[date] = mapped_column()
    effective_date_renewal: Mapped[date] = mapped_column()
    state: Mapped[str] = mapped_column(String(2), default="CA")
    prior_json: Mapped[dict] = mapped_column(JSON)
    renewal_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RuleResultRow(Base):
    __tablename__ = "rule_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_number: Mapped[str] = mapped_column(String(50), index=True)
    job_id: Mapped[str] = mapped_column(String(8), index=True)
    risk_level: Mapped[str] = mapped_column(String(30))
    flags_json: Mapped[list] = mapped_column(JSON, default=list)
    changes_json: Mapped[list] = mapped_column(JSON, default=list)
    summary_text: Mapped[str] = mapped_column(Text, default="")
    broker_contacted: Mapped[bool] = mapped_column(Boolean, default=False)
    quote_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LLMResultRow(Base):
    __tablename__ = "llm_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_number: Mapped[str] = mapped_column(String(50), index=True)
    job_id: Mapped[str] = mapped_column(String(8), index=True)
    risk_level: Mapped[str] = mapped_column(String(30))
    insights_json: Mapped[list] = mapped_column(JSON, default=list)
    summary_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ComparisonRunRow(Base):
    __tablename__ = "comparison_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    result_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
