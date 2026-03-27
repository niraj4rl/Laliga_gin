"""
backend/database/db.py
SQLAlchemy models + session factory for LaLigaMatchAI.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date,
    ForeignKey, DateTime, CheckConstraint, UniqueConstraint, Index, text
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Load backend/.env reliably regardless of current working directory.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

def _build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url

    # Support split DB_* variables for local dev if DATABASE_URL is not provided.
    db_user = os.getenv("DB_USER", "postgres").strip() or "postgres"
    db_password = os.getenv("DB_PASSWORD", "").strip()
    db_host = os.getenv("DB_HOST", "localhost").strip() or "localhost"
    db_port = os.getenv("DB_PORT", "5432").strip() or "5432"
    db_name = os.getenv("DB_NAME", "laliga_analytics").strip() or "laliga_analytics"

    if not db_password:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_URL in backend/.env "
            "or provide DB_PASSWORD (optionally DB_USER, DB_HOST, DB_PORT, DB_NAME)."
        )

    return (
        f"postgresql://{db_user}:{quote_plus(db_password)}@"
        f"{db_host}:{db_port}/{db_name}"
    )


DATABASE_URL = _build_database_url()


engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# ────────────────────────────────────────────────────────────
# ORM Models
# ────────────────────────────────────────────────────────────

class Team(Base):
    __tablename__ = "teams"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False, unique=True)
    short_name = Column(String(10))
    founded    = Column(Integer)
    stadium    = Column(String(100))
    city       = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    home_matches  = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches  = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")
    stats         = relationship("TeamStat", back_populates="team")


class Match(Base):
    __tablename__ = "matches"

    id                       = Column(Integer, primary_key=True, index=True)
    season                   = Column(String(10), nullable=False)
    match_date               = Column(Date, nullable=False)
    home_team_id             = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id             = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_goals               = Column(Integer)
    away_goals               = Column(Integer)
    shots_home               = Column(Integer)
    shots_away               = Column(Integer)
    shots_on_target_home     = Column(Integer)
    shots_on_target_away     = Column(Integer)
    possession_home          = Column(Float)
    possession_away          = Column(Float)
    result                   = Column(String(10))
    created_at               = Column(DateTime, server_default=func.now())

    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    features  = relationship("Feature", back_populates="match", uselist=False)

    __table_args__ = (
        CheckConstraint("result IN ('home_win','draw','away_win')", name="valid_result"),
        Index("idx_matches_home_team", "home_team_id"),
        Index("idx_matches_away_team", "away_team_id"),
    )


class TeamStat(Base):
    __tablename__ = "team_stats"

    id                  = Column(Integer, primary_key=True, index=True)
    team_id             = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season              = Column(String(10), nullable=False)
    matches_played      = Column(Integer, default=0)
    wins                = Column(Integer, default=0)
    draws               = Column(Integer, default=0)
    losses              = Column(Integer, default=0)
    goals_scored        = Column(Integer, default=0)
    goals_conceded      = Column(Integer, default=0)
    points              = Column(Integer, default=0)
    league_position     = Column(Integer)
    avg_possession      = Column(Float)
    avg_shots_per_match = Column(Float)
    updated_at          = Column(DateTime, server_default=func.now())

    team = relationship("Team", back_populates="stats")

    __table_args__ = (
        UniqueConstraint("team_id", "season", name="uq_team_season"),
    )


class Feature(Base):
    __tablename__ = "features"

    id                    = Column(Integer, primary_key=True, index=True)
    match_id              = Column(Integer, ForeignKey("matches.id"), nullable=False)
    home_form_last5       = Column(Float)
    away_form_last5       = Column(Float)
    home_goal_avg         = Column(Float)
    away_goal_avg         = Column(Float)
    home_conceded_avg     = Column(Float)
    away_conceded_avg     = Column(Float)
    home_advantage        = Column(Float)
    head_to_head_score    = Column(Float)
    home_league_position  = Column(Integer)
    away_league_position  = Column(Integer)
    home_strength_score   = Column(Float)
    away_strength_score   = Column(Float)
    created_at            = Column(DateTime, server_default=func.now())

    match = relationship("Match", back_populates="features")


class Prediction(Base):
    __tablename__ = "predictions"

    id               = Column(Integer, primary_key=True, index=True)
    home_team_id     = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id     = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_win_prob    = Column(Float, nullable=False)
    draw_prob        = Column(Float, nullable=False)
    away_win_prob    = Column(Float, nullable=False)
    predicted_result = Column(String(10))
    confidence       = Column(Float)
    model_version    = Column(String(50))
    created_at       = Column(DateTime, server_default=func.now())

    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────

def get_db():
    """FastAPI dependency – yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables (run once on first start)."""
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        raise RuntimeError(
            "Database connection failed. Verify PostgreSQL is running and your "
            "DATABASE_URL/DB_* credentials in backend/.env are correct."
        ) from exc