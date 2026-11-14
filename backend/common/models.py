from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Investigation(Base):
    """One NASA PSI investigation (e.g. PSI-69 FLEX), normalized from the PSI API."""

    __tablename__ = "investigations"

    accession: Mapped[str] = mapped_column(String(32), primary_key=True)
    acronym: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(Text, default="")
    research_area: Mapped[str] = mapped_column(String(128), default="")
    sub_research_area: Mapped[str] = mapped_column(String(256), default="")
    project_type: Mapped[str] = mapped_column(String(128), default="")
    flight_platform: Mapped[str] = mapped_column(String(256), default="")
    hardware: Mapped[str] = mapped_column(Text, default="")
    hardware_link: Mapped[str] = mapped_column(Text, default="")
    managing_center: Mapped[str] = mapped_column(String(256), default="")
    start_date: Mapped[str] = mapped_column(String(32), default="")
    end_date: Mapped[str] = mapped_column(String(32), default="")
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doi: Mapped[str] = mapped_column(String(128), default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    approach: Mapped[str] = mapped_column(Text, default="")
    research_impacts: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    related: Mapped[list] = mapped_column(JSONB, default=list)
    publications: Mapped[list] = mapped_column(JSONB, default=list)
    contacts: Mapped[list] = mapped_column(JSONB, default=list)
    thumbnail_url: Mapped[str] = mapped_column(Text, default="")
    psi_url: Mapped[str] = mapped_column(Text, default="")
    profile: Mapped[dict] = mapped_column(JSONB, default=dict)
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)
    source: Mapped[str] = mapped_column(String(16), default="live")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tables: Mapped[list["ExperimentTable"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan", order_by="ExperimentTable.id"
    )


class ExperimentTable(Base):
    """A test-matrix CSV published with an investigation (PSI 'Experimental table')."""

    __tablename__ = "experiment_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    accession: Mapped[str] = mapped_column(
        ForeignKey("investigations.accession", ondelete="CASCADE"), index=True
    )
    file_name: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(32), default="experimental")
    columns: Mapped[list] = mapped_column(JSONB, default=list)
    rows: Mapped[list] = mapped_column(JSONB, default=list)
    row_count: Mapped[int] = mapped_column(Integer, default=0)

    investigation: Mapped[Investigation] = relationship(back_populates="tables")


class Incident(Base):
    """Historical spacecraft fire / oxygen incidents (context for why this matters)."""

    __tablename__ = "incidents"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    date: Mapped[str] = mapped_column(String(32))
    year: Mapped[int] = mapped_column(Integer)
    vehicle: Mapped[str] = mapped_column(String(256), default="")
    atmosphere: Mapped[str] = mapped_column(Text, default="")
    cause: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str] = mapped_column(Text, default="")
    lessons: Mapped[list] = mapped_column(JSONB, default=list)
    pillars: Mapped[list] = mapped_column(JSONB, default=list)
    related_investigations: Mapped[list] = mapped_column(JSONB, default=list)
    source_url: Mapped[str] = mapped_column(Text, default="")


class Spinoff(Base):
    """NASA Spinoff technologies with terrestrial fire-safety applications."""

    __tablename__ = "spinoffs"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256))
    year: Mapped[int] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(Text, default="")
    application: Mapped[str] = mapped_column(Text, default="")
    pillar: Mapped[str] = mapped_column(String(32), default="")
    related_investigations: Mapped[list] = mapped_column(JSONB, default=list)
    source_url: Mapped[str] = mapped_column(Text, default="")


class Habitat(Base):
    """Crewed-environment atmosphere scenarios used for relevance ranking."""

    __tablename__ = "habitats"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    short: Mapped[str] = mapped_column(String(64), default="")
    o2_min: Mapped[float] = mapped_column(Float)
    o2_max: Mapped[float] = mapped_column(Float)
    p_min_psi: Mapped[float] = mapped_column(Float)
    p_max_psi: Mapped[float] = mapped_column(Float)
    gravity_g: Mapped[float] = mapped_column(Float)
    flow_min: Mapped[float] = mapped_column(Float, default=0.0)
    flow_max: Mapped[float] = mapped_column(Float, default=20.0)
    description: Mapped[str] = mapped_column(Text, default="")
    basis: Mapped[str] = mapped_column(Text, default="")
    is_assumption: Mapped[bool] = mapped_column(Boolean, default=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default="live")
    status: Mapped[str] = mapped_column(String(16), default="running")
    message: Mapped[str] = mapped_column(Text, default="")
    investigations: Mapped[int] = mapped_column(Integer, default=0)
    tables: Mapped[int] = mapped_column(Integer, default=0)


class AIBrief(Base):
    """Cached SI-generated investigation briefs."""

    __tablename__ = "ai_briefs"

    accession: Mapped[str] = mapped_column(String(32), primary_key=True)
    model: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
