from dotenv import load_dotenv
import os
import time
import threading

load_dotenv("backend/.env")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json, httpx
from datetime import datetime, timezone

from backend.database.db import get_db, init_db, Prediction, Team
from backend.services.data_service import (
    get_all_teams, get_team_by_name,
    build_prediction_features, get_recent_predictions,
)
from backend.ml.train_model import predict_match, META_PATH

app = FastAPI(title="LaLigaMatchAI API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

# ── Config ────────────────────────────────────────────────────────────────────
FOOTBALL_BASE  = "https://api.football-data.org/v4"
LALIGA_CODE    = "PD"

_cache         = {}
CACHE_TTL      = 600
_last_req_time = 0
_req_lock      = threading.Lock()
MIN_REQ_GAP    = 7

def cache_get(key):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None

def cache_set(key, data):
    _cache[key] = (data, time.time())

def fheaders():
    if not FOOTBALL_API_KEY:
        raise HTTPException(503, "FOOTBALL_API_KEY not set in backend/.env")
    return {"X-Auth-Token": FOOTBALL_API_KEY}

def fget(path: str, params: dict = None):
    global _last_req_time
    cache_key = path + str(sorted((params or {}).items()))
    cached = cache_get(cache_key)
    if cached:
        return cached
    with _req_lock:
        wait = MIN_REQ_GAP - (time.time() - _last_req_time)
        if wait > 0:
            time.sleep(wait)
        _last_req_time = time.time()
    try:
        r = httpx.get(
            f"{FOOTBALL_BASE}{path}",
            headers=fheaders(),
            params=params or {},
            timeout=12
        )
        r.raise_for_status()
        data = r.json()
        cache_set(cache_key, data)
        return data
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            stale = _cache.get(cache_key)
            if stale:
                return stale[0]
        raise HTTPException(
            e.response.status_code,
            f"football-data.org: {e.response.text[:200]}"
        )
    except httpx.RequestError as e:
        raise HTTPException(502, f"Network error: {str(e)}")

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "LaLigaMatchAI v3"}

@app.get("/health", tags=["Health"])
def health():
    return {
        "status":          "healthy",
        "api_key_set":     bool(FOOTBALL_API_KEY),
        "api_key_preview": FOOTBALL_API_KEY[:6] + "..." if FOOTBALL_API_KEY else "NOT SET",
        "cache_entries":   len(_cache),
    }

# ── Teams ─────────────────────────────────────────────────────────────────────
@app.get("/teams", tags=["Teams"])
def list_teams(db: Session = Depends(get_db)):
    return {"teams": get_all_teams(db)}

@app.get("/team/{team_name}", tags=["Teams"])
def team_detail(team_name: str, db: Session = Depends(get_db)):
    result = get_team_by_name(db, team_name)
    if not result:
        raise HTTPException(404, f"Team '{team_name}' not found")
    return result

# ── Live Standings ────────────────────────────────────────────────────────────
@app.get("/live/standings", tags=["Live"])
def live_standings():
    data  = fget(f"/competitions/{LALIGA_CODE}/standings")
    table = data["standings"][0]["table"]
    return {
        "season": "2025/26",
        "standings": [
            {
                "position":      r["position"],
                "team":          r["team"]["name"],
                "short_name":    r["team"]["shortName"],
                "crest":         r["team"].get("crest", ""),
                "team_id":       r["team"]["id"],
                "played":        r["playedGames"],
                "won":           r["won"],
                "draw":          r["draw"],
                "lost":          r["lost"],
                "goals_for":     r["goalsFor"],
                "goals_against": r["goalsAgainst"],
                "goal_diff":     r["goalDifference"],
                "points":        r["points"],
            }
            for r in table
        ]
    }

# ── Recent Results ────────────────────────────────────────────────────────────
@app.get("/live/results", tags=["Live"])
def live_results():
    data    = fget(f"/competitions/{LALIGA_CODE}/matches", {"status": "FINISHED", "limit": 10})
    matches = data.get("matches", [])
    result  = []
    for m in matches[-10:]:
        hg = m["score"]["fullTime"]["home"] or 0
        ag = m["score"]["fullTime"]["away"] or 0
        result.append({
            "matchday":   m["matchday"],
            "date":       m["utcDate"],
            "home_team":  m["homeTeam"]["name"],
            "away_team":  m["awayTeam"]["name"],
            "home_score": hg,
            "away_score": ag,
            "home_crest": m["homeTeam"].get("crest", ""),
            "away_crest": m["awayTeam"].get("crest", ""),
            "result":     "home" if hg > ag else "away" if ag > hg else "draw",
        })
    return {"results": list(reversed(result))}

# ── Squad info (disabled to avoid rate limits on free tier) ──────────────────
def get_team_squad_info(team_id: int) -> dict:
    return {
        "injuries":    [],
        "suspensions": [],
        "key_players": [],
        "squad_size":  0,
    }

# ── Form from standings ───────────────────────────────────────────────────────
def form_from_standings(team_id: int, table: list) -> dict:
    for r in table:
        if r["team"]["id"] == team_id:
            played = r["playedGames"] or 1
            return {
                "form_string":  "—",
                "avg_scored":   round(r["goalsFor"]     / played, 2),
                "avg_conceded": round(r["goalsAgainst"] / played, 2),
                "form_rating":  round(r["points"] / (played * 3), 3),
            }
    return {
        "form_string":  "—",
        "avg_scored":   1.2,
        "avg_conceded": 1.2,
        "form_rating":  0.5,
    }

# ── Auto Predict Upcoming Matches ─────────────────────────────────────────────
@app.get("/predict/upcoming", tags=["Predictions"])
def predict_upcoming(db: Session = Depends(get_db)):
    """
    Predicts all upcoming La Liga fixtures.
    Only 2 API calls total — fixtures + standings.
    Cached for 10 minutes.
    """
    # Call 1: fixtures
    fixtures_data = fget(
        f"/competitions/{LALIGA_CODE}/matches",
        {"status": "SCHEDULED", "limit": 10}
    )
    matches = fixtures_data.get("matches", [])[:10]

    if not matches:
        return {"predictions": [], "message": "No upcoming fixtures found"}

    # Call 2: standings
    standings_data  = fget(f"/competitions/{LALIGA_CODE}/standings")
    standings_table = standings_data["standings"][0]["table"]

    position_map      = {r["team"]["id"]: r["position"]     for r in standings_table}
    goals_for_map     = {r["team"]["id"]: r["goalsFor"]     for r in standings_table}
    goals_against_map = {r["team"]["id"]: r["goalsAgainst"] for r in standings_table}
    played_map        = {r["team"]["id"]: r["playedGames"]  for r in standings_table}
    points_map        = {r["team"]["id"]: r["points"]       for r in standings_table}

    predictions = []

    for m in matches:
        home_id   = m["homeTeam"]["id"]
        away_id   = m["awayTeam"]["id"]
        home_name = m["homeTeam"]["name"]
        away_name = m["awayTeam"]["name"]

        home_form = form_from_standings(home_id, standings_table)
        away_form = form_from_standings(away_id, standings_table)

        home_squad = get_team_squad_info(home_id)
        away_squad = get_team_squad_info(away_id)

        h_played = played_map.get(home_id, 10) or 10
        a_played = played_map.get(away_id, 10) or 10
        h_form_r = home_form["form_rating"]
        a_form_r = away_form["form_rating"]
        h_goals  = round(goals_for_map.get(home_id, 12)    / h_played, 3)
        a_goals  = round(goals_for_map.get(away_id, 12)    / a_played, 3)
        h_conc   = round(goals_against_map.get(home_id, 12) / h_played, 3)
        a_conc   = round(goals_against_map.get(away_id, 12) / a_played, 3)
        h_pos    = position_map.get(home_id, 10)
        a_pos    = position_map.get(away_id, 10)
        h_xg     = round(min(h_goals / max(h_goals + 0.5, 1), 0.6), 3)
        a_xg     = round(min(a_goals / max(a_goals + 0.5, 1), 0.6), 3)
        h_str    = round(h_form_r*0.35 + h_goals*0.35 + (1/max(h_conc+0.1,0.1))*0.2 + (1/max(h_pos,1))*0.1, 3)
        a_str    = round(a_form_r*0.35 + a_goals*0.35 + (1/max(a_conc+0.1,0.1))*0.2 + (1/max(a_pos,1))*0.1, 3)

        features = {
            "home_form_last8":      h_form_r,
            "away_form_last8":      a_form_r,
            "home_goal_avg":        h_goals,
            "away_goal_avg":        a_goals,
            "home_conceded_avg":    h_conc,
            "away_conceded_avg":    a_conc,
            "home_xg_proxy":        h_xg,
            "away_xg_proxy":        a_xg,
            "home_shots_avg":       round(h_goals * 8, 2),
            "away_shots_avg":       round(a_goals * 8, 2),
            "home_sot_avg":         round(h_goals * 3.5, 2),
            "away_sot_avg":         round(a_goals * 3.5, 2),
            "home_corners_avg":     5.0,
            "away_corners_avg":     5.0,
            "home_cards_avg":       2.0,
            "away_cards_avg":       2.0,
            "head_to_head_score":   0.5,
            "home_league_position": h_pos,
            "away_league_position": a_pos,
            "home_home_win_rate":   round(h_form_r * 0.9, 3),
            "away_away_win_rate":   round(a_form_r * 0.7, 3),
            "home_advantage":       round(h_form_r - a_form_r + 0.08, 3),
            "home_strength_score":  h_str,
            "away_strength_score":  a_str,
            "goal_diff_ratio":      round((h_goals - a_goals) / max(h_goals + a_goals, 0.1), 3),
            "position_diff":        round((a_pos - h_pos) / 20.0, 3),
            "form_diff":            round(h_form_r - a_form_r, 3),
            "xg_diff":              round(h_xg - a_xg, 3),
        }

        try:
            pred = predict_match(features)
        except Exception:
            pred = {
                "home_win": 0.4, "draw": 0.3, "away_win": 0.3,
                "predicted_result": "draw", "confidence": 0.4
            }

        predictions.append({
            "matchday":         m["matchday"],
            "date":             m["utcDate"],
            "home_team":        home_name,
            "away_team":        away_name,
            "home_crest":       m["homeTeam"].get("crest", ""),
            "away_crest":       m["awayTeam"].get("crest", ""),
            "home_position":    h_pos,
            "away_position":    a_pos,
            "home_form":        home_form["form_string"],
            "away_form":        away_form["form_string"],
            "home_win_prob":    round(pred["home_win"] * 100),
            "draw_prob":        round(pred["draw"] * 100),
            "away_win_prob":    round(pred["away_win"] * 100),
            "predicted_result": pred["predicted_result"],
            "confidence":       round(pred["confidence"] * 100),
            "home_avg_goals":   home_form["avg_scored"],
            "away_avg_goals":   away_form["avg_scored"],
            "home_points":      points_map.get(home_id, 0),
            "away_points":      points_map.get(away_id, 0),
            "home_injuries":    home_squad["injuries"],
            "away_injuries":    away_squad["injuries"],
            "home_suspensions": home_squad["suspensions"],
            "away_suspensions": away_squad["suspensions"],
            "home_key_players": home_squad["key_players"],
            "away_key_players": away_squad["key_players"],
        })

    return {
        "predictions":  predictions,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

# ── Manual Predict ────────────────────────────────────────────────────────────
@app.get("/predict/manual", tags=["Predictions"])
def predict_manual(
    home: str = Query(...),
    away: str = Query(...),
    db: Session = Depends(get_db)
):
    ht = db.query(Team).filter(Team.name.ilike(f"%{home}%")).first()
    at = db.query(Team).filter(Team.name.ilike(f"%{away}%")).first()
    if not ht: raise HTTPException(404, f"'{home}' not found")
    if not at: raise HTTPException(404, f"'{away}' not found")
    features = build_prediction_features(db, ht.id, at.id)
    pred = predict_match(features)
    return {"home_team": ht.name, "away_team": at.name, **pred, "features": features}

@app.get("/predictions/history", tags=["Predictions"])
def prediction_history(
    limit: int = Query(default=20),
    db: Session = Depends(get_db)
):
    return {"predictions": get_recent_predictions(db, limit=limit)}

@app.get("/model/info", tags=["Model"])
def model_info():
    if not META_PATH.exists():
        raise HTTPException(404, "Model not trained yet")
    with open(META_PATH) as f:
        return json.load(f)