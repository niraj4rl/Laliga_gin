"""
backend/ml/feature_engineering.py
Enhanced feature engineering - 28 features including:
xG proxy, shots on target, corners, cards, home/away win rates,
differentials, composite strength scores.
"""

from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

import pandas as pd
import numpy as np
from pathlib import Path


def load_raw(csv_path=None) -> pd.DataFrame:
    if csv_path is None:
        csv_path = Path(__file__).resolve().parents[2] / "data" / "laliga_matches.csv"
    df = pd.read_csv(csv_path, parse_dates=["match_date"], encoding="utf-8")
    df.sort_values("match_date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def _past(df, team, before_idx, n):
    mask = (
        ((df["home_team"] == team) | (df["away_team"] == team)) &
        (df.index < before_idx)
    )
    return df[mask].tail(n)


def rolling_points(df, team, before_idx, n=8) -> float:
    past = _past(df, team, before_idx, n)
    if past.empty:
        return 0.5
    pts = []
    for _, r in past.iterrows():
        if r["result"] == "home_win":
            pts.append(1.0 if r["home_team"] == team else 0.0)
        elif r["result"] == "away_win":
            pts.append(1.0 if r["away_team"] == team else 0.0)
        else:
            pts.append(0.33)
    return float(np.mean(pts))


def rolling_stat(df, team, before_idx, col_home, col_away, n=8) -> float:
    past = _past(df, team, before_idx, n)
    if past.empty or col_home not in df.columns:
        return 0.0
    vals = []
    for _, r in past.iterrows():
        col = col_home if r["home_team"] == team else col_away
        v = r.get(col, 0)
        if pd.notna(v):
            vals.append(float(v))
    return float(np.mean(vals)) if vals else 0.0


def xg_proxy(df, team, before_idx, n=8) -> float:
    past = _past(df, team, before_idx, n)
    if past.empty:
        return 0.33
    sot_total, s_total = 0, 0
    for _, r in past.iterrows():
        if r["home_team"] == team:
            sot_total += r.get("shots_on_target_home", 0) or 0
            s_total   += r.get("shots_home", 1) or 1
        else:
            sot_total += r.get("shots_on_target_away", 0) or 0
            s_total   += r.get("shots_away", 1) or 1
    return round(sot_total / max(s_total, 1), 4)


def head_to_head(df, home, away, before_idx, n=8) -> float:
    mask = (
        (
            ((df["home_team"] == home) & (df["away_team"] == away)) |
            ((df["home_team"] == away) & (df["away_team"] == home))
        ) &
        (df.index < before_idx)
    )
    h2h = df[mask].tail(n)
    if h2h.empty:
        return 0.5
    scores = []
    for _, r in h2h.iterrows():
        if r["home_team"] == home:
            scores.append(1.0 if r["result"] == "home_win" else 0.0)
        else:
            scores.append(1.0 if r["result"] == "away_win" else 0.0)
    return float(np.mean(scores))


def league_position(df, team, before_idx) -> int:
    past = df[df.index < before_idx]
    if past.empty:
        return 10
    teams = list(set(past["home_team"].tolist() + past["away_team"].tolist()))
    pts = {t: 0 for t in teams}
    for _, r in past.iterrows():
        if r["result"] == "home_win":
            pts[r["home_team"]] += 3
        elif r["result"] == "away_win":
            pts[r["away_team"]] += 3
        else:
            pts[r["home_team"]] += 1
            pts[r["away_team"]] += 1
    sorted_t = sorted(pts, key=pts.get, reverse=True)
    return (sorted_t.index(team) + 1) if team in sorted_t else 10


def home_win_rate(df, team, before_idx, n=10) -> float:
    past = df[(df["home_team"] == team) & (df.index < before_idx)].tail(n)
    if past.empty:
        return 0.45
    return round((past["result"] == "home_win").sum() / len(past), 4)


def away_win_rate(df, team, before_idx, n=10) -> float:
    past = df[(df["away_team"] == team) & (df.index < before_idx)].tail(n)
    if past.empty:
        return 0.30
    return round((past["result"] == "away_win").sum() / len(past), 4)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    total = len(df)

    for idx, row in df.iterrows():
        if idx % 500 == 0:
            print(f"  Processing {idx}/{total}...")

        home = row["home_team"]
        away = row["away_team"]

        h_form           = rolling_points(df, home, idx, n=8)
        a_form           = rolling_points(df, away, idx, n=8)
        h_goals_scored   = rolling_stat(df, home, idx, "home_goals", "away_goals", n=8)
        a_goals_scored   = rolling_stat(df, away, idx, "away_goals", "home_goals", n=8)
        h_goals_conceded = rolling_stat(df, home, idx, "away_goals", "home_goals", n=8)
        a_goals_conceded = rolling_stat(df, away, idx, "home_goals", "away_goals", n=8)
        h_xg             = xg_proxy(df, home, idx, n=8)
        a_xg             = xg_proxy(df, away, idx, n=8)
        h_shots          = rolling_stat(df, home, idx, "shots_home", "shots_away", n=8)
        a_shots          = rolling_stat(df, away, idx, "shots_away", "shots_home", n=8)
        h_sot            = rolling_stat(df, home, idx, "shots_on_target_home", "shots_on_target_away", n=8)
        a_sot            = rolling_stat(df, away, idx, "shots_on_target_away", "shots_on_target_home", n=8)
        h_corners        = rolling_stat(df, home, idx, "corners_home", "corners_away", n=8)
        a_corners        = rolling_stat(df, away, idx, "corners_away", "corners_home", n=8)
        h_cards          = rolling_stat(df, home, idx, "yellow_home", "yellow_away", n=8)
        a_cards          = rolling_stat(df, away, idx, "yellow_away", "yellow_home", n=8)
        h2h              = head_to_head(df, home, away, idx, n=8)
        h_pos            = league_position(df, home, idx)
        a_pos            = league_position(df, away, idx)
        h_home_wr        = home_win_rate(df, home, idx, n=10)
        a_away_wr        = away_win_rate(df, away, idx, n=10)

        h_attack  = h_goals_scored * 0.5 + h_sot * 0.3 + h_xg * 0.2
        a_attack  = a_goals_scored * 0.5 + a_sot * 0.3 + a_xg * 0.2
        h_defence = 1.0 / max(h_goals_conceded + 0.1, 0.1)
        a_defence = 1.0 / max(a_goals_conceded + 0.1, 0.1)
        h_strength = round(h_form * 0.35 + h_attack * 0.35 + h_defence * 0.2 + (1/max(h_pos,1)) * 0.1, 4)
        a_strength = round(a_form * 0.35 + a_attack * 0.35 + a_defence * 0.2 + (1/max(a_pos,1)) * 0.1, 4)

        records.append({
            "home_form_last8":      round(h_form, 4),
            "away_form_last8":      round(a_form, 4),
            "home_goal_avg":        round(h_goals_scored, 4),
            "away_goal_avg":        round(a_goals_scored, 4),
            "home_conceded_avg":    round(h_goals_conceded, 4),
            "away_conceded_avg":    round(a_goals_conceded, 4),
            "home_xg_proxy":        round(h_xg, 4),
            "away_xg_proxy":        round(a_xg, 4),
            "home_shots_avg":       round(h_shots, 4),
            "away_shots_avg":       round(a_shots, 4),
            "home_sot_avg":         round(h_sot, 4),
            "away_sot_avg":         round(a_sot, 4),
            "home_corners_avg":     round(h_corners, 4),
            "away_corners_avg":     round(a_corners, 4),
            "home_cards_avg":       round(h_cards, 4),
            "away_cards_avg":       round(a_cards, 4),
            "head_to_head_score":   round(h2h, 4),
            "home_league_position": h_pos,
            "away_league_position": a_pos,
            "home_home_win_rate":   round(h_home_wr, 4),
            "away_away_win_rate":   round(a_away_wr, 4),
            "home_advantage":       round(h_form - a_form + 0.08, 4),
            "home_strength_score":  h_strength,
            "away_strength_score":  a_strength,
            "goal_diff_ratio":      round((h_goals_scored - a_goals_scored) / max(h_goals_scored + a_goals_scored, 0.1), 4),
            "position_diff":        round((a_pos - h_pos) / 20.0, 4),
            "form_diff":            round(h_form - a_form, 4),
            "xg_diff":              round(h_xg - a_xg, 4),
            "result":               row["result"],
        })

    return pd.DataFrame(records)


FEATURE_COLS = [
    "home_form_last8", "away_form_last8",
    "home_goal_avg", "away_goal_avg",
    "home_conceded_avg", "away_conceded_avg",
    "home_xg_proxy", "away_xg_proxy",
    "home_shots_avg", "away_shots_avg",
    "home_sot_avg", "away_sot_avg",
    "home_corners_avg", "away_corners_avg",
    "home_cards_avg", "away_cards_avg",
    "head_to_head_score",
    "home_league_position", "away_league_position",
    "home_home_win_rate", "away_away_win_rate",
    "home_advantage",
    "home_strength_score", "away_strength_score",
    "goal_diff_ratio", "position_diff", "form_diff", "xg_diff",
]


if __name__ == "__main__":
    raw = load_raw()
    print(f"Loaded {len(raw)} rows across {raw['season'].nunique()} seasons")
    print("Building enhanced features (this takes 5-10 mins for 3800 rows)...")
    features = build_features(raw)
    out = Path(__file__).resolve().parents[2] / "data" / "features.csv"
    features.to_csv(out, index=False)
    print(f"\n✅  Features saved → {out}")
    print(f"    Shape   : {features.shape}")
    print(f"    Features: {len(FEATURE_COLS)}")
    print(features.head(2))