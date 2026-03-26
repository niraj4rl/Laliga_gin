"""
backend/database/seed.py
Generates and inserts synthetic La Liga historical data.
Run once: python -m backend.database.seed
"""
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
import random
import csv
import os
from datetime import date, timedelta
from pathlib import Path

# ────────────────────────────────────────────────────────────
# Team definitions  (name, short, strength 0-1)
# ────────────────────────────────────────────────────────────
TEAMS = [
    ("Real Madrid",      "RMA", 0.92, "Estadio Santiago Bernabéu", "Madrid"),
    ("FC Barcelona",     "BAR", 0.90, "Camp Nou",                  "Barcelona"),
    ("Atlético Madrid",  "ATM", 0.82, "Estadio Metropolitano",     "Madrid"),
    ("Sevilla FC",       "SEV", 0.74, "Estadio Ramón Sánchez-Pizjuán", "Sevilla"),
    ("Real Sociedad",    "RSO", 0.70, "Reale Arena",               "San Sebastián"),
    ("Villarreal CF",    "VIL", 0.68, "Estadio de la Cerámica",    "Villarreal"),
    ("Athletic Club",    "ATH", 0.66, "San Mamés",                 "Bilbao"),
    ("Real Betis",       "BET", 0.65, "Estadio Benito Villamarín", "Seville"),
    ("Valencia CF",      "VAL", 0.62, "Estadio Mestalla",          "Valencia"),
    ("Getafe CF",        "GET", 0.54, "Coliseum Alfonso Pérez",    "Getafe"),
    ("Celta Vigo",       "CEL", 0.55, "Estadio Abanca-Balaídos",   "Vigo"),
    ("Osasuna",          "OSA", 0.53, "El Sadar",                  "Pamplona"),
    ("Granada CF",       "GRA", 0.48, "Estadio Los Cármenes",      "Granada"),
    ("Rayo Vallecano",   "RAY", 0.50, "Estadio de Vallecas",       "Madrid"),
    ("Cádiz CF",         "CAD", 0.46, "Estadio Nuevo Mirandilla",  "Cádiz"),
    ("UD Almería",       "ALM", 0.45, "Estadio de los Juegos Mediterráneos", "Almería"),
    ("Girona FC",        "GIR", 0.60, "Estadi Municipal de Montilivi", "Girona"),
    ("UD Las Palmas",    "LPA", 0.47, "Estadio Gran Canaria",      "Las Palmas"),
    ("Deportivo Alavés", "ALA", 0.49, "Estadio de Mendizorroza",   "Vitoria"),
    ("RCD Mallorca",     "MAL", 0.51, "Visit Mallorca Estadi",     "Palma"),
]

SEASONS = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]

random.seed(42)


def simulate_match(home_strength: float, away_strength: float):
    """Return (home_goals, away_goals, shots_h, shots_a, sot_h, sot_a, poss_h)."""
    home_advantage = 0.10
    h = home_strength + home_advantage
    a = away_strength

    # Expected goals based on strength difference
    h_xg = max(0.3, 1.5 * h / (h + a) + random.gauss(0, 0.4))
    a_xg = max(0.3, 1.5 * a / (h + a) + random.gauss(0, 0.4))

    hg = max(0, int(random.gauss(h_xg, 0.8)))
    ag = max(0, int(random.gauss(a_xg, 0.8)))

    shots_h     = max(3, int(random.gauss(14 * h / (h + a), 3)))
    shots_a     = max(3, int(random.gauss(14 * a / (h + a), 3)))
    sot_h       = max(1, int(shots_h * random.uniform(0.30, 0.50)))
    sot_a       = max(1, int(shots_a * random.uniform(0.30, 0.50)))
    poss_h      = round(min(70, max(30, random.gauss(50 + 10 * (h - a), 5))), 1)

    if hg > ag:
        result = "home_win"
    elif hg < ag:
        result = "away_win"
    else:
        result = "draw"

    return hg, ag, shots_h, shots_a, sot_h, sot_a, poss_h, result


def generate_csv():
    """Write data/laliga_matches.csv with synthetic match data."""
    out_path = Path(__file__).resolve().parents[2] / "data" / "laliga_matches.csv"
    out_path.parent.mkdir(exist_ok=True)

    team_map = {t[0]: t for t in TEAMS}

    rows = []
    for season in SEASONS:
        year = int(season.split("-")[0])
        season_start = date(year, 8, 15)

        for i, home in enumerate(TEAMS):
            for j, away in enumerate(TEAMS):
                if i == j:
                    continue
                offset_days = random.randint(0, 260)
                match_date  = season_start + timedelta(days=offset_days)
                hg, ag, sh, sa, soth, sota, poss_h, result = simulate_match(
                    home[2], away[2]
                )
                rows.append({
                    "season":                season,
                    "match_date":            match_date.isoformat(),
                    "home_team":             home[0],
                    "away_team":             away[0],
                    "home_goals":            hg,
                    "away_goals":            ag,
                    "shots_home":            sh,
                    "shots_away":            sa,
                    "shots_on_target_home":  soth,
                    "shots_on_target_away":  sota,
                    "possession_home":       poss_h,
                    "possession_away":       round(100 - poss_h, 1),
                    "result":                result,
                })

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅  Wrote {len(rows)} rows → {out_path}")
    return out_path


def seed_database(csv_path: str = None):
    """Insert all teams + matches into PostgreSQL."""
    try:
        from backend.database.db import SessionLocal, init_db, Team, Match
    except ModuleNotFoundError:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from backend.database.db import SessionLocal, init_db, Team, Match

    init_db()
    db = SessionLocal()

    try:
        # Insert teams
        for t in TEAMS:
            if not db.query(Team).filter_by(name=t[0]).first():
                db.add(Team(name=t[0], short_name=t[1], stadium=t[3], city=t[4]))
        db.commit()

        team_id_map = {t.name: t.id for t in db.query(Team).all()}

        # Read CSV
        if csv_path is None:
            csv_path = Path(__file__).resolve().parents[2] / "data" / "laliga_matches.csv"

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(Match(
                    season=row["season"],
                    match_date=date.fromisoformat(row["match_date"]),
                    home_team_id=team_id_map[row["home_team"]],
                    away_team_id=team_id_map[row["away_team"]],
                    home_goals=int(row["home_goals"]),
                    away_goals=int(row["away_goals"]),
                    shots_home=int(row["shots_home"]),
                    shots_away=int(row["shots_away"]),
                    shots_on_target_home=int(row["shots_on_target_home"]),
                    shots_on_target_away=int(row["shots_on_target_away"]),
                    possession_home=float(row["possession_home"]),
                    possession_away=float(row["possession_away"]),
                    result=row["result"],
                ))
                if len(batch) >= 500:
                    db.bulk_save_objects(batch)
                    db.commit()
                    batch = []

            if batch:
                db.bulk_save_objects(batch)
                db.commit()

        print("✅  Database seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    generate_csv()
    seed_database()