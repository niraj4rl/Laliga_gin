"""
backend/database/download_real_data.py
Downloads 10 seasons of real La Liga data from football-data.co.uk
Includes: goals, shots, shots on target, corners, fouls, cards, possession
Run: python -m backend.database.download_real_data
"""

from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

import pandas as pd
import requests
from pathlib import Path
from io import StringIO

# 10 seasons of La Liga data
SEASON_URLS = {
    "2014-15": "https://www.football-data.co.uk/mmz4281/1415/SP1.csv",
    "2015-16": "https://www.football-data.co.uk/mmz4281/1516/SP1.csv",
    "2016-17": "https://www.football-data.co.uk/mmz4281/1617/SP1.csv",
    "2017-18": "https://www.football-data.co.uk/mmz4281/1718/SP1.csv",
    "2018-19": "https://www.football-data.co.uk/mmz4281/1819/SP1.csv",
    "2019-20": "https://www.football-data.co.uk/mmz4281/1920/SP1.csv",
    "2020-21": "https://www.football-data.co.uk/mmz4281/2021/SP1.csv",
    "2021-22": "https://www.football-data.co.uk/mmz4281/2122/SP1.csv",
    "2022-23": "https://www.football-data.co.uk/mmz4281/2223/SP1.csv",
    "2023-24": "https://www.football-data.co.uk/mmz4281/2324/SP1.csv",
}

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "laliga_matches.csv"
OUT_PATH.parent.mkdir(exist_ok=True)


def safe_col(df, col, default=0):
    return df[col] if col in df.columns else pd.Series([default] * len(df))


def download_season(season: str, url: str) -> pd.DataFrame:
    print(f"  Downloading {season}...")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), encoding="latin-1")
    return df


def clean_season(df: pd.DataFrame, season: str) -> pd.DataFrame:
    required = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
    df = df.dropna(subset=required)
    df = df[df["FTR"].isin(["H", "A", "D"])].copy()

    result_map = {"H": "home_win", "A": "away_win", "D": "draw"}
    df["result"] = df["FTR"].map(result_map)
    df["match_date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["match_date"])

    out = pd.DataFrame({
        "season":                season,
        "match_date":            df["match_date"].dt.strftime("%Y-%m-%d"),
        "home_team":             df["HomeTeam"].str.strip(),
        "away_team":             df["AwayTeam"].str.strip(),
        "home_goals":            pd.to_numeric(df["FTHG"], errors="coerce").fillna(0).astype(int),
        "away_goals":            pd.to_numeric(df["FTAG"], errors="coerce").fillna(0).astype(int),
        # Half time goals
        "home_ht_goals":         pd.to_numeric(safe_col(df, "HTHG"), errors="coerce").fillna(0).astype(int),
        "away_ht_goals":         pd.to_numeric(safe_col(df, "HTAG"), errors="coerce").fillna(0).astype(int),
        # Shots
        "shots_home":            pd.to_numeric(safe_col(df, "HS"), errors="coerce").fillna(0).astype(int),
        "shots_away":            pd.to_numeric(safe_col(df, "AS"), errors="coerce").fillna(0).astype(int),
        "shots_on_target_home":  pd.to_numeric(safe_col(df, "HST"), errors="coerce").fillna(0).astype(int),
        "shots_on_target_away":  pd.to_numeric(safe_col(df, "AST"), errors="coerce").fillna(0).astype(int),
        # Corners
        "corners_home":          pd.to_numeric(safe_col(df, "HC"), errors="coerce").fillna(0).astype(int),
        "corners_away":          pd.to_numeric(safe_col(df, "AC"), errors="coerce").fillna(0).astype(int),
        # Fouls
        "fouls_home":            pd.to_numeric(safe_col(df, "HF"), errors="coerce").fillna(0).astype(int),
        "fouls_away":            pd.to_numeric(safe_col(df, "AF"), errors="coerce").fillna(0).astype(int),
        # Cards
        "yellow_home":           pd.to_numeric(safe_col(df, "HY"), errors="coerce").fillna(0).astype(int),
        "yellow_away":           pd.to_numeric(safe_col(df, "AY"), errors="coerce").fillna(0).astype(int),
        "red_home":              pd.to_numeric(safe_col(df, "HR"), errors="coerce").fillna(0).astype(int),
        "red_away":              pd.to_numeric(safe_col(df, "AR"), errors="coerce").fillna(0).astype(int),
        # Result
        "result":                df["result"],
    })

    return out


if __name__ == "__main__":
    all_seasons = []

    for season, url in SEASON_URLS.items():
        try:
            raw   = download_season(season, url)
            clean = clean_season(raw, season)
            all_seasons.append(clean)
            print(f"  ✅ {season}: {len(clean)} matches")
        except Exception as e:
            print(f"  ❌ {season} failed: {e}")

    if not all_seasons:
        print("No data downloaded!")
        exit(1)

    combined = pd.concat(all_seasons, ignore_index=True)
    combined.sort_values("match_date", inplace=True)
    combined.reset_index(drop=True, inplace=True)
    combined.to_csv(OUT_PATH, index=False, encoding="utf-8")

    print(f"\n✅  Saved {len(combined)} real matches → {OUT_PATH}")
    print(f"    Seasons : {list(combined['season'].unique())}")
    print(f"    Teams   : {combined['home_team'].nunique()} unique")
    print(f"    Results : {combined['result'].value_counts().to_dict()}")