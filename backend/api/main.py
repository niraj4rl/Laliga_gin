from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.database.db import Prediction, Team, get_db, init_db
from backend.ml.train_model import META_PATH, predict_match
from backend.services.data_service import (
    build_prediction_features,
    get_all_teams,
    get_recent_predictions,
    get_team_by_name,
)

# Load backend/.env regardless of startup cwd.
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
APIFOOTBALL_API_KEY = os.getenv("APIFOOTBALL_API_KEY", "")

_default_cors = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
]
_cors_from_env = os.getenv("CORS_ORIGINS", "")
if _cors_from_env.strip():
    CORS_ORIGINS = [o.strip() for o in _cors_from_env.split(",") if o.strip()]
else:
    frontend_url = os.getenv("FRONTEND_URL", "").strip()
    CORS_ORIGINS = _default_cors + ([frontend_url] if frontend_url else [])

app = FastAPI(title="LaLigaMatchAI API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


FOOTBALL_BASE = "https://api.football-data.org/v4"
RAPIDAPI_BASE = "https://api-football-v1.p.rapidapi.com/v3"
APIFOOTBALL_BASE = os.getenv("APIFOOTBALL_BASE", RAPIDAPI_BASE)
LALIGA_CODE = "PD"
LALIGA_ID = 140
_now = datetime.now(timezone.utc)
_default_season = _now.year if _now.month >= 7 else _now.year - 1
CURRENT_SEASON = int(os.getenv("CURRENT_SEASON", str(_default_season)))

UPCOMING_MATCH_LIMIT = int(os.getenv("UPCOMING_MATCH_LIMIT", "8"))
ENABLE_INJURY_LOOKUP = os.getenv("ENABLE_INJURY_LOOKUP", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

POSITION_IMPACT = {
    "attacker": 0.85,
    "forward": 0.85,
    "striker": 0.85,
    "centre-forward": 0.85,
    "left winger": 0.75,
    "right winger": 0.75,
    "attacking midfield": 0.70,
    "midfielder": 0.60,
    "central midfield": 0.60,
    "defensive midfield": 0.55,
    "left midfield": 0.55,
    "right midfield": 0.55,
    "defender": 0.50,
    "centre-back": 0.50,
    "left-back": 0.45,
    "right-back": 0.45,
    "goalkeeper": 0.65,
    "gk": 0.65,
}


_cache = {}
CACHE_TTL = int(os.getenv("FOOTBALL_CACHE_TTL", "1800"))
STALE_CACHE_TTL = int(os.getenv("FOOTBALL_STALE_CACHE_TTL", "43200"))
_last_req_time = 0.0
_req_lock = threading.Lock()
MIN_REQ_GAP = 7
QUOTA_COOLDOWN_SECONDS = int(os.getenv("FOOTBALL_QUOTA_COOLDOWN_SECONDS", "3600"))
_quota_limited_until = 0.0
RAPIDAPI_COOLDOWN_SECONDS = int(os.getenv("RAPIDAPI_COOLDOWN_SECONDS", "3600"))
_rapidapi_limited_until = 0.0
INJURY_SNAPSHOT_TTL_SECONDS = int(os.getenv("INJURY_SNAPSHOT_TTL_SECONDS", str(7 * 24 * 3600)))
_snapshot_lock = threading.Lock()
_snapshot_path = Path(__file__).resolve().parents[2] / "data" / "injury_snapshots.json"


def get_pos_impact(position: str) -> float:
    if not position:
        return 0.5
    pos = position.lower()
    for key, value in POSITION_IMPACT.items():
        if key in pos:
            return value
    return 0.5


def cache_get(key: str, allow_stale: bool = False):
    if key in _cache:
        data, ts = _cache[key]
        max_age = STALE_CACHE_TTL if allow_stale else CACHE_TTL
        if time.time() - ts < max_age:
            return data
    return None


def cache_set(key: str, data):
    _cache[key] = (data, time.time())


def cache_get_latest(prefix: str, allow_stale: bool = False):
    max_age = STALE_CACHE_TTL if allow_stale else CACHE_TTL
    now = time.time()
    candidates = [
        (k, v) for k, v in _cache.items() if k.startswith(prefix) and (now - v[1]) < max_age
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1][1])[1][0]


def fheaders() -> dict:
    if not FOOTBALL_API_KEY:
        raise HTTPException(503, "FOOTBALL_API_KEY not set in backend/.env")
    return {"X-Auth-Token": FOOTBALL_API_KEY}


def fget(path: str, params: dict | None = None):
    global _last_req_time, _quota_limited_until

    cache_key = "fd:" + path + str(sorted((params or {}).items()))
    cached = cache_get(cache_key)
    if cached:
        return cached

    if time.time() < _quota_limited_until:
        stale = cache_get(cache_key, allow_stale=True) or cache_get_latest(
            f"fd:{path}", allow_stale=True
        )
        if stale:
            return stale
        retry_after = max(int(_quota_limited_until - time.time()), 1)
        raise HTTPException(
            503, f"football-data.org quota cooldown active. Retry in {retry_after}s"
        )

    with _req_lock:
        wait = MIN_REQ_GAP - (time.time() - _last_req_time)
        if wait > 0:
            time.sleep(wait)
        _last_req_time = time.time()

    try:
        resp = httpx.get(
            f"{FOOTBALL_BASE}{path}",
            headers=fheaders(),
            params=params or {},
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        cache_set(cache_key, data)
        return data
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            _quota_limited_until = time.time() + QUOTA_COOLDOWN_SECONDS
            stale = cache_get(cache_key, allow_stale=True) or cache_get_latest(
                f"fd:{path}", allow_stale=True
            )
            if stale:
                return stale
            raise HTTPException(429, "football-data.org rate limit reached and no cache available")
        stale = cache_get(cache_key, allow_stale=True) or cache_get_latest(
            f"fd:{path}", allow_stale=True
        )
        if stale:
            return stale
        raise HTTPException(e.response.status_code, f"football-data.org: {e.response.text[:200]}")
    except httpx.RequestError as e:
        stale = cache_get(cache_key, allow_stale=True) or cache_get_latest(
            f"fd:{path}", allow_stale=True
        )
        if stale:
            return stale
        raise HTTPException(502, f"Network error: {str(e)}")


def rapi_get(path: str, params: dict | None = None):
    global _rapidapi_limited_until
    provider_key = APIFOOTBALL_API_KEY or RAPIDAPI_KEY
    if not provider_key:
        return None

    cache_key = "rapi:" + path + str(sorted((params or {}).items()))
    cached = cache_get(cache_key)
    if cached:
        return cached

    if time.time() < _rapidapi_limited_until:
        return cache_get(cache_key, allow_stale=True)

    try:
        # Supports API-Football style apiKey header while keeping RapidAPI compatibility.
        headers = {
            "apiKey": provider_key,
            "x-apisports-key": provider_key,
            "X-RapidAPI-Key": provider_key,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com",
        }
        resp = httpx.get(
            f"{APIFOOTBALL_BASE}{path}",
            headers=headers,
            params=params or {},
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        cache_set(cache_key, data)
        return data
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            _rapidapi_limited_until = time.time() + RAPIDAPI_COOLDOWN_SECONDS
        return cache_get(cache_key, allow_stale=True)
    except Exception:
        return cache_get(cache_key, allow_stale=True)


def get_injury_data_status(include_injuries: bool) -> str:
    if not include_injuries or not ENABLE_INJURY_LOOKUP:
        return "disabled"
    if not (APIFOOTBALL_API_KEY or RAPIDAPI_KEY):
        return "missing_key"
    if time.time() < _rapidapi_limited_until:
        return "rate_limited"
    return "enabled"


def rapidapi_retry_in_seconds() -> int:
    return max(int(_rapidapi_limited_until - time.time()), 0)


def rapidapi_is_limited() -> bool:
    return time.time() < _rapidapi_limited_until


def get_football_squad_fallback(team_id: int | None) -> dict:
    empty = {
        "injuries": [],
        "suspensions": [],
        "key_players": [],
        "total_impact": 0.0,
        "injury_penalty": 0.0,
        "data_source": "none",
    }
    if not team_id:
        return empty

    try:
        team_data = fget(f"/teams/{team_id}")
    except Exception:
        return empty

    squad = team_data.get("squad", []) or []
    if not squad:
        return empty

    attackers = []
    others = []
    for p in squad:
        position = (p.get("position") or "").lower()
        row = {
            "name": p.get("name", "Unknown"),
            "position": p.get("position", ""),
            "goals": 0,
            "assists": 0,
            "impact": get_pos_impact(p.get("position", "")),
        }
        if any(k in position for k in ["forward", "attacker", "wing", "striker"]):
            attackers.append(row)
        else:
            others.append(row)

    key_players = (attackers + others)[:3]
    return {
        "injuries": [],
        "suspensions": [],
        "key_players": key_players,
        "total_impact": 0.0,
        "injury_penalty": 0.0,
        "data_source": "football_fallback",
    }


def _team_key(name: str) -> str:
    return (name or "").strip().lower()


def _load_snapshots() -> dict:
    if not _snapshot_path.exists():
        return {}
    try:
        with open(_snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        return {}
    return {}


def _save_snapshots(data: dict) -> None:
    _snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with open(_snapshot_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True)


def get_cached_team_snapshot(team_name: str) -> dict | None:
    key = _team_key(team_name)
    with _snapshot_lock:
        snapshots = _load_snapshots()
        record = snapshots.get(key)
    if not record:
        return None

    ts = int(record.get("timestamp", 0) or 0)
    if ts <= 0:
        return None
    if time.time() - ts > INJURY_SNAPSHOT_TTL_SECONDS:
        return None

    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    return payload


def set_cached_team_snapshot(team_name: str, payload: dict) -> None:
    key = _team_key(team_name)
    with _snapshot_lock:
        snapshots = _load_snapshots()
        snapshots[key] = {
            "timestamp": int(time.time()),
            "payload": payload,
        }
        _save_snapshots(snapshots)


def get_team_injuries(team_name: str, team_id: int | None = None) -> dict:
    empty = {
        "injuries": [],
        "suspensions": [],
        "key_players": [],
        "total_impact": 0.0,
        "injury_penalty": 0.0,
        "data_source": "none",
    }

    cached = get_cached_team_snapshot(team_name)

    def cached_or_empty() -> dict:
        if cached:
            cached_copy = dict(cached)
            cached_copy["data_source"] = "cached"
            return cached_copy
        return dict(empty)

    if not (APIFOOTBALL_API_KEY or RAPIDAPI_KEY):
        fallback = get_football_squad_fallback(team_id)
        if fallback.get("key_players"):
            return fallback
        return cached_or_empty()

    if rapidapi_is_limited():
        fallback = get_football_squad_fallback(team_id)
        if fallback.get("key_players"):
            return fallback
        return cached_or_empty()

    team_data = rapi_get(
        "/teams", {"search": team_name, "league": LALIGA_ID, "season": CURRENT_SEASON}
    )
    if not team_data or not team_data.get("response"):
        team_data = rapi_get("/teams", {"search": team_name})
    if not team_data or not team_data.get("response"):
        fallback = get_football_squad_fallback(team_id)
        if fallback.get("key_players"):
            return fallback
        return cached_or_empty()

    team_id = None
    for t in team_data["response"]:
        country = t.get("team", {}).get("country", "")
        if country in ("Spain", "ES", ""):
            team_id = t["team"]["id"]
            break
    if not team_id:
        team_id = team_data["response"][0]["team"]["id"]

    injury_data = rapi_get(
        "/injuries", {"league": LALIGA_ID, "season": CURRENT_SEASON, "team": team_id}
    )
    # Player list enrichment is intentionally disabled for predictions payload.
    player_data = None

    apps_map = {}
    goals_map = {}
    assists_map = {}
    pos_map = {}

    if player_data and player_data.get("response"):
        for p in player_data["response"]:
            pid = p["player"]["id"]
            stats = p.get("statistics", [{}])[0]
            apps_map[pid] = stats.get("games", {}).get("appearences", 0) or 0
            goals_map[pid] = stats.get("goals", {}).get("total", 0) or 0
            assists_map[pid] = stats.get("goals", {}).get("assists", 0) or 0
            pos_map[pid] = stats.get("games", {}).get("position", "") or ""

    injuries = []
    suspensions = []
    total_impact = 0.0

    if injury_data and injury_data.get("response"):
        for item in injury_data["response"]:
            player = item.get("player", {})
            name = player.get("name", "Unknown")
            pid = player.get("id", 0)
            ptype = player.get("type", "")
            reason = player.get("reason", "Injured")

            position = pos_map.get(pid, ptype)
            base_impact = get_pos_impact(position)
            apps = apps_map.get(pid, 0)
            goals = goals_map.get(pid, 0)
            assists = assists_map.get(pid, 0)

            contrib_boost = min((goals + assists) * 0.02, 0.15)
            reg_boost = 0.10 if apps >= 20 else 0.05 if apps >= 10 else 0.0
            impact = round(min(base_impact + contrib_boost + reg_boost, 1.0), 3)
            total_impact += impact

            entry = {
                "name": name,
                "position": position or ptype or "-",
                "reason": reason,
                "impact": impact,
                "impact_label": "HIGH" if impact >= 0.75 else "MED" if impact >= 0.55 else "LOW",
                "appearances": apps,
                "goals": goals,
                "assists": assists,
            }
            if any(w in reason.lower() for w in ["suspen", "card", "ban"]):
                suspensions.append(entry)
            else:
                injuries.append(entry)

    key_players = []

    top3 = sum(sorted([p["impact"] for p in injuries + suspensions], reverse=True)[:3])
    penalty = round(top3 / 10.0, 4)

    result = {
        "injuries": sorted(injuries, key=lambda x: x["impact"], reverse=True)[:5],
        "suspensions": sorted(suspensions, key=lambda x: x["impact"], reverse=True)[:3],
        "key_players": key_players[:3],
        "total_impact": round(total_impact, 3),
        "injury_penalty": penalty,
        "data_source": "live",
    }

    has_meaningful_data = bool(result["injuries"] or result["suspensions"] or result["key_players"])
    if has_meaningful_data or not cached:
        set_cached_team_snapshot(team_name, result)
    return result


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "LaLigaMatchAI v4"}


@app.get("/health", tags=["Health"])
def health():
    with _snapshot_lock:
        snapshot_count = len(_load_snapshots())
    return {
        "status": "healthy",
        "football_api_set": bool(FOOTBALL_API_KEY),
        "rapidapi_set": bool(RAPIDAPI_KEY),
        "apifootball_set": bool(APIFOOTBALL_API_KEY),
        "cache_entries": len(_cache),
        "snapshot_teams": snapshot_count,
        "quota_limited": time.time() < _quota_limited_until,
        "quota_retry_in_s": max(int(_quota_limited_until - time.time()), 0),
        "rapidapi_limited": rapidapi_is_limited(),
        "rapidapi_retry_in_s": rapidapi_retry_in_seconds(),
    }


@app.get("/teams", tags=["Teams"])
def list_teams(db: Session = Depends(get_db)):
    return {"teams": get_all_teams(db)}


@app.get("/team/{team_name}", tags=["Teams"])
def team_detail(team_name: str, db: Session = Depends(get_db)):
    result = get_team_by_name(db, team_name)
    if not result:
        raise HTTPException(404, f"'{team_name}' not found")
    return result


@app.get("/live/standings", tags=["Live"])
def live_standings():
    data = fget(f"/competitions/{LALIGA_CODE}/standings")
    table = data["standings"][0]["table"]
    return {
        "season": "2025/26",
        "standings": [
            {
                "position": r["position"],
                "team": r["team"]["name"],
                "short_name": r["team"]["shortName"],
                "crest": r["team"].get("crest", ""),
                "team_id": r["team"]["id"],
                "played": r["playedGames"],
                "won": r["won"],
                "draw": r["draw"],
                "lost": r["lost"],
                "goals_for": r["goalsFor"],
                "goals_against": r["goalsAgainst"],
                "goal_diff": r["goalDifference"],
                "points": r["points"],
            }
            for r in table
        ],
    }


@app.get("/live/results", tags=["Live"])
def live_results():
    data = fget(f"/competitions/{LALIGA_CODE}/matches", {"status": "FINISHED", "limit": 10})
    matches = data.get("matches", [])
    result = []
    for m in matches[-10:]:
        hg = m["score"]["fullTime"]["home"] or 0
        ag = m["score"]["fullTime"]["away"] or 0
        result.append(
            {
                "matchday": m["matchday"],
                "date": m["utcDate"],
                "home_team": m["homeTeam"]["name"],
                "away_team": m["awayTeam"]["name"],
                "home_score": hg,
                "away_score": ag,
                "home_crest": m["homeTeam"].get("crest", ""),
                "away_crest": m["awayTeam"].get("crest", ""),
                "result": "home" if hg > ag else "away" if ag > hg else "draw",
            }
        )
    return {"results": list(reversed(result))}


def form_from_standings(team_id: int, table: list) -> dict:
    for r in table:
        if r["team"]["id"] == team_id:
            played = r["playedGames"] or 1
            return {
                "form_string": "-",
                "avg_scored": round(r["goalsFor"] / played, 2),
                "avg_conceded": round(r["goalsAgainst"] / played, 2),
                "form_rating": round(r["points"] / (played * 3), 3),
            }
    return {"form_string": "-", "avg_scored": 1.2, "avg_conceded": 1.2, "form_rating": 0.5}


@app.get("/predict/upcoming", tags=["Predictions"])
def predict_upcoming(
    include_injuries: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    fixtures_data = fget(f"/competitions/{LALIGA_CODE}/matches", {"status": "SCHEDULED", "limit": 10})
    matches = fixtures_data.get("matches", [])[:UPCOMING_MATCH_LIMIT]
    if not matches:
        return {"predictions": [], "message": "No upcoming fixtures"}

    standings_data = fget(f"/competitions/{LALIGA_CODE}/standings")
    standings_table = standings_data["standings"][0]["table"]

    position_map = {r["team"]["id"]: r["position"] for r in standings_table}
    goals_for_map = {r["team"]["id"]: r["goalsFor"] for r in standings_table}
    goals_against_map = {r["team"]["id"]: r["goalsAgainst"] for r in standings_table}
    played_map = {r["team"]["id"]: r["playedGames"] for r in standings_table}
    points_map = {r["team"]["id"]: r["points"] for r in standings_table}

    predictions = []
    empty_squad = {"injuries": [], "suspensions": [], "key_players": [], "injury_penalty": 0.0}
    injury_status = get_injury_data_status(include_injuries)
    injury_lookup_enabled = injury_status == "enabled"

    for m in matches:
        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]
        home_name = m["homeTeam"]["name"]
        away_name = m["awayTeam"]["name"]

        home_form = form_from_standings(home_id, standings_table)
        away_form = form_from_standings(away_id, standings_table)

        if injury_lookup_enabled:
            home_squad = get_team_injuries(home_name, team_id=home_id)
            away_squad = get_team_injuries(away_name, team_id=away_id)
        else:
            home_squad = empty_squad
            away_squad = empty_squad

        home_source = home_squad.get("data_source", "none")
        away_source = away_squad.get("data_source", "none")
        from_cache = home_source == "cached" or away_source == "cached"
        from_fallback_provider = home_source == "football_fallback" or away_source == "football_fallback"
        has_squad_content = bool(
            home_squad.get("injuries")
            or home_squad.get("suspensions")
            or home_squad.get("key_players")
            or away_squad.get("injuries")
            or away_squad.get("suspensions")
            or away_squad.get("key_players")
        )

        card_injury_status = injury_status
        if from_cache:
            card_injury_status = "cached_fallback"
        elif from_fallback_provider:
            card_injury_status = "fallback_provider"
        elif injury_lookup_enabled and rapidapi_is_limited() and not has_squad_content:
            card_injury_status = "rate_limited"

        if from_cache:
            data_source = "cached"
        elif from_fallback_provider:
            data_source = "football_fallback"
        elif injury_lookup_enabled and has_squad_content:
            data_source = "live"
        else:
            data_source = "none"

        h_played = played_map.get(home_id, 10) or 10
        a_played = played_map.get(away_id, 10) or 10
        h_form_r = home_form["form_rating"]
        a_form_r = away_form["form_rating"]
        h_goals = round(goals_for_map.get(home_id, 12) / h_played, 3)
        a_goals = round(goals_for_map.get(away_id, 12) / a_played, 3)
        h_conc = round(goals_against_map.get(home_id, 12) / h_played, 3)
        a_conc = round(goals_against_map.get(away_id, 12) / a_played, 3)
        h_pos = position_map.get(home_id, 10)
        a_pos = position_map.get(away_id, 10)
        h_xg = round(min(h_goals / max(h_goals + 0.5, 1), 0.6), 3)
        a_xg = round(min(a_goals / max(a_goals + 0.5, 1), 0.6), 3)

        h_penalty = home_squad["injury_penalty"]
        a_penalty = away_squad["injury_penalty"]

        h_str = round(
            max(
                h_form_r * 0.35
                + h_goals * 0.35
                + (1 / max(h_conc + 0.1, 0.1)) * 0.2
                + (1 / max(h_pos, 1)) * 0.1
                - h_penalty,
                0.05,
            ),
            3,
        )
        a_str = round(
            max(
                a_form_r * 0.35
                + a_goals * 0.35
                + (1 / max(a_conc + 0.1, 0.1)) * 0.2
                + (1 / max(a_pos, 1)) * 0.1
                - a_penalty,
                0.05,
            ),
            3,
        )

        features = {
            "home_form_last8": h_form_r,
            "away_form_last8": a_form_r,
            "home_goal_avg": h_goals,
            "away_goal_avg": a_goals,
            "home_conceded_avg": h_conc,
            "away_conceded_avg": a_conc,
            "home_xg_proxy": h_xg,
            "away_xg_proxy": a_xg,
            "home_shots_avg": round(h_goals * 8, 2),
            "away_shots_avg": round(a_goals * 8, 2),
            "home_sot_avg": round(h_goals * 3.5, 2),
            "away_sot_avg": round(a_goals * 3.5, 2),
            "home_corners_avg": 5.0,
            "away_corners_avg": 5.0,
            "home_cards_avg": 2.0,
            "away_cards_avg": 2.0,
            "head_to_head_score": 0.5,
            "home_league_position": h_pos,
            "away_league_position": a_pos,
            "home_home_win_rate": round(h_form_r * 0.9, 3),
            "away_away_win_rate": round(a_form_r * 0.7, 3),
            "home_advantage": round(h_form_r - a_form_r + 0.08, 3),
            "home_strength_score": h_str,
            "away_strength_score": a_str,
            "goal_diff_ratio": round((h_goals - a_goals) / max(h_goals + a_goals, 0.1), 3),
            "position_diff": round((a_pos - h_pos) / 20.0, 3),
            "form_diff": round(h_form_r - a_form_r, 3),
            "xg_diff": round(h_xg - a_xg, 3),
        }

        try:
            pred = predict_match(features)
        except Exception:
            pred = {
                "home_win": 0.4,
                "draw": 0.3,
                "away_win": 0.3,
                "predicted_result": "draw",
                "confidence": 0.4,
            }

        predictions.append(
            {
                "matchday": m["matchday"],
                "date": m["utcDate"],
                "home_team": home_name,
                "away_team": away_name,
                "home_crest": m["homeTeam"].get("crest", ""),
                "away_crest": m["awayTeam"].get("crest", ""),
                "home_position": h_pos,
                "away_position": a_pos,
                "home_form": home_form["form_string"],
                "away_form": away_form["form_string"],
                "home_win_prob": round(pred["home_win"] * 100),
                "draw_prob": round(pred["draw"] * 100),
                "away_win_prob": round(pred["away_win"] * 100),
                "predicted_result": pred["predicted_result"],
                "confidence": round(pred["confidence"] * 100),
                "home_avg_goals": home_form["avg_scored"],
                "away_avg_goals": away_form["avg_scored"],
                "home_points": points_map.get(home_id, 0),
                "away_points": points_map.get(away_id, 0),
                "home_injuries": home_squad["injuries"],
                "away_injuries": away_squad["injuries"],
                "home_suspensions": home_squad["suspensions"],
                "away_suspensions": away_squad["suspensions"],
                "home_key_players": home_squad["key_players"],
                "away_key_players": away_squad["key_players"],
                "home_injury_penalty": h_penalty,
                "away_injury_penalty": a_penalty,
                "injury_data_available": from_cache or from_fallback_provider or (injury_lookup_enabled and has_squad_content),
                "injury_data_status": card_injury_status,
                "injury_data_source": data_source,
                "rapidapi_limited": rapidapi_is_limited(),
                "rapidapi_retry_in_s": rapidapi_retry_in_seconds(),
            }
        )

    return {"predictions": predictions, "generated_at": datetime.now(timezone.utc).isoformat()}


@app.get("/predict/manual", tags=["Predictions"])
def predict_manual(home: str = Query(...), away: str = Query(...), db: Session = Depends(get_db)):
    ht = db.query(Team).filter(Team.name.ilike(f"%{home}%")).first()
    at = db.query(Team).filter(Team.name.ilike(f"%{away}%")).first()
    if not ht:
        raise HTTPException(404, f"'{home}' not found")
    if not at:
        raise HTTPException(404, f"'{away}' not found")
    features = build_prediction_features(db, ht.id, at.id)
    pred = predict_match(features)
    return {"home_team": ht.name, "away_team": at.name, **pred, "features": features}


@app.get("/predictions/history", tags=["Predictions"])
def prediction_history(limit: int = Query(default=20), db: Session = Depends(get_db)):
    return {"predictions": get_recent_predictions(db, limit=limit)}


@app.get("/model/info", tags=["Model"])
def model_info():
    if not META_PATH.exists():
        raise HTTPException(404, "Model not trained yet")
    with open(META_PATH) as f:
        return json.load(f)
