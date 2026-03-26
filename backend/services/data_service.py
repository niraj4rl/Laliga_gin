"""
backend/services/data_service.py
Business logic: fetch team stats, compute live features for predictions.
"""

from typing import Optional
from sqlalchemy.orm import Session
import numpy as np

from backend.database.db import Team, Match, TeamStat, Prediction
from backend.ml.feature_engineering import FEATURE_COLS


# ────────────────────────────────────────────────────────────
# Team queries
# ────────────────────────────────────────────────────────────

def get_all_teams(db: Session) -> list[dict]:
    teams = db.query(Team).order_by(Team.name).all()
    return [
        {"id": t.id, "name": t.name, "short_name": t.short_name,
         "stadium": t.stadium, "city": t.city}
        for t in teams
    ]


def get_team_by_name(db: Session, name: str) -> Optional[dict]:
    team = db.query(Team).filter(Team.name.ilike(f"%{name}%")).first()
    if not team:
        return None

    # Latest season stats
    stat = (
        db.query(TeamStat)
        .filter(TeamStat.team_id == team.id)
        .order_by(TeamStat.season.desc())
        .first()
    )

    # Last 5 matches
    home_matches = (
        db.query(Match)
        .filter(Match.home_team_id == team.id)
        .order_by(Match.match_date.desc())
        .limit(10)
        .all()
    )
    away_matches = (
        db.query(Match)
        .filter(Match.away_team_id == team.id)
        .order_by(Match.match_date.desc())
        .limit(10)
        .all()
    )

    all_matches = sorted(
        home_matches + away_matches,
        key=lambda m: m.match_date,
        reverse=True
    )[:5]

    recent_form = []
    for m in all_matches:
        side = "home" if m.home_team_id == team.id else "away"
        if m.result == "home_win":
            outcome = "W" if side == "home" else "L"
        elif m.result == "away_win":
            outcome = "W" if side == "away" else "L"
        else:
            outcome = "D"
        opp = m.away_team_id if side == "home" else m.home_team_id
        opp_team = db.query(Team).filter(Team.id == opp).first()
        recent_form.append({
            "date":     m.match_date.isoformat(),
            "opponent": opp_team.name if opp_team else "Unknown",
            "outcome":  outcome,
            "score":    f"{m.home_goals}-{m.away_goals}",
        })

    return {
        "id":           team.id,
        "name":         team.name,
        "short_name":   team.short_name,
        "stadium":      team.stadium,
        "city":         team.city,
        "season_stats": {
            "season":            stat.season        if stat else None,
            "matches_played":    stat.matches_played if stat else 0,
            "wins":              stat.wins           if stat else 0,
            "draws":             stat.draws          if stat else 0,
            "losses":            stat.losses         if stat else 0,
            "goals_scored":      stat.goals_scored   if stat else 0,
            "goals_conceded":    stat.goals_conceded if stat else 0,
            "points":            stat.points         if stat else 0,
            "league_position":   stat.league_position if stat else None,
            "avg_possession":    stat.avg_possession  if stat else None,
        } if stat else {},
        "recent_form": recent_form,
    }


# ────────────────────────────────────────────────────────────
# Feature computation for a new prediction
# ────────────────────────────────────────────────────────────

def _rolling_form_db(db: Session, team_id: int, n: int = 5) -> float:
    matches = (
        db.query(Match)
        .filter((Match.home_team_id == team_id) | (Match.away_team_id == team_id))
        .order_by(Match.match_date.desc())
        .limit(n)
        .all()
    )
    if not matches:
        return 0.5
    pts = []
    for m in matches:
        if m.result == "home_win":
            pts.append(1.0 if m.home_team_id == team_id else 0.0)
        elif m.result == "away_win":
            pts.append(1.0 if m.away_team_id == team_id else 0.0)
        else:
            pts.append(0.33)
    return float(np.mean(pts))


def _rolling_goals(db: Session, team_id: int, scored: bool = True, n: int = 5) -> float:
    matches = (
        db.query(Match)
        .filter((Match.home_team_id == team_id) | (Match.away_team_id == team_id))
        .order_by(Match.match_date.desc())
        .limit(n)
        .all()
    )
    if not matches:
        return 1.2
    vals = []
    for m in matches:
        if m.home_team_id == team_id:
            vals.append(m.home_goals if scored else m.away_goals)
        else:
            vals.append(m.away_goals if scored else m.home_goals)
    return float(np.mean([v for v in vals if v is not None] or [1.2]))


def _head_to_head(db: Session, home_id: int, away_id: int, n: int = 5) -> float:
    matches = (
        db.query(Match)
        .filter(
            ((Match.home_team_id == home_id) & (Match.away_team_id == away_id)) |
            ((Match.home_team_id == away_id) & (Match.away_team_id == home_id))
        )
        .order_by(Match.match_date.desc())
        .limit(n)
        .all()
    )
    if not matches:
        return 0.5
    scores = []
    for m in matches:
        if m.home_team_id == home_id:
            scores.append(1.0 if m.result == "home_win" else 0.0)
        else:
            scores.append(1.0 if m.result == "away_win" else 0.0)
    return float(np.mean(scores))


def build_prediction_features(db: Session, home_id: int, away_id: int) -> dict:
    """Build feature dict from live DB for the prediction endpoint."""
    h_form       = _rolling_form_db(db, home_id)
    a_form       = _rolling_form_db(db, away_id)
    h_goal_avg   = _rolling_goals(db, home_id, scored=True)
    a_goal_avg   = _rolling_goals(db, away_id, scored=True)
    h_conc_avg   = _rolling_goals(db, home_id, scored=False)
    a_conc_avg   = _rolling_goals(db, away_id, scored=False)
    h2h          = _head_to_head(db, home_id, away_id)

    h_stat = db.query(TeamStat).filter(TeamStat.team_id == home_id).order_by(TeamStat.season.desc()).first()
    a_stat = db.query(TeamStat).filter(TeamStat.team_id == away_id).order_by(TeamStat.season.desc()).first()
    h_pos  = h_stat.league_position if h_stat and h_stat.league_position else 10
    a_pos  = a_stat.league_position if a_stat and a_stat.league_position else 10

    h_strength = (h_form + (1 / max(h_pos, 1) * 10) + h_goal_avg - h_conc_avg) / 3
    a_strength = (a_form + (1 / max(a_pos, 1) * 10) + a_goal_avg - a_conc_avg) / 3

    return {
        "home_form_last5":      round(h_form, 4),
        "away_form_last5":      round(a_form, 4),
        "home_goal_avg":        round(h_goal_avg, 4),
        "away_goal_avg":        round(a_goal_avg, 4),
        "home_conceded_avg":    round(h_conc_avg, 4),
        "away_conceded_avg":    round(a_conc_avg, 4),
        "home_advantage":       round(h_form - a_form + 0.1, 4),
        "head_to_head_score":   round(h2h, 4),
        "home_league_position": int(h_pos),
        "away_league_position": int(a_pos),
        "home_strength_score":  round(h_strength, 4),
        "away_strength_score":  round(a_strength, 4),
    }


# ────────────────────────────────────────────────────────────
# Prediction history
# ────────────────────────────────────────────────────────────

def get_recent_predictions(db: Session, limit: int = 20) -> list[dict]:
    preds = (
        db.query(Prediction)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for p in preds:
        ht = db.query(Team).filter(Team.id == p.home_team_id).first()
        at = db.query(Team).filter(Team.id == p.away_team_id).first()
        result.append({
            "id":              p.id,
            "home_team":       ht.name if ht else "?",
            "away_team":       at.name if at else "?",
            "home_win_prob":   p.home_win_prob,
            "draw_prob":       p.draw_prob,
            "away_win_prob":   p.away_win_prob,
            "predicted_result": p.predicted_result,
            "confidence":      p.confidence,
            "created_at":      p.created_at.isoformat(),
        })
    return result