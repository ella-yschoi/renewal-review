from datetime import date, datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db import Base


class RenewalPairRow(Base):
    __tablename__ = "renewal_pairs"

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


class BatchResultRow(Base):
    __tablename__ = "batch_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(8), index=True)
    policy_number: Mapped[str] = mapped_column(String(50), index=True)
    risk_level: Mapped[str] = mapped_column(String(10))
    flags_json: Mapped[list] = mapped_column(JSON, default=list)
    summary_text: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
