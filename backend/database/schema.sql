-- LaLigaMatchAI Database Schema
-- PostgreSQL

CREATE DATABASE laliga_analytics;
\c laliga_analytics;

-- ─────────────────────────────────────────
-- TEAMS
-- ─────────────────────────────────────────
CREATE TABLE teams (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    short_name  VARCHAR(10),
    founded     INT,
    stadium     VARCHAR(100),
    city        VARCHAR(100),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_teams_name ON teams(name);

-- ─────────────────────────────────────────
-- MATCHES
-- ─────────────────────────────────────────
CREATE TABLE matches (
    id              SERIAL PRIMARY KEY,
    season          VARCHAR(10) NOT NULL,
    match_date      DATE NOT NULL,
    home_team_id    INT NOT NULL REFERENCES teams(id),
    away_team_id    INT NOT NULL REFERENCES teams(id),
    home_goals      INT,
    away_goals      INT,
    shots_home      INT,
    shots_away      INT,
    shots_on_target_home INT,
    shots_on_target_away INT,
    possession_home FLOAT,
    possession_away FLOAT,
    result          VARCHAR(10) CHECK (result IN ('home_win','draw','away_win')),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_matches_home_team   ON matches(home_team_id);
CREATE INDEX idx_matches_away_team   ON matches(away_team_id);
CREATE INDEX idx_matches_season      ON matches(season);
CREATE INDEX idx_matches_date        ON matches(match_date);

-- ─────────────────────────────────────────
-- TEAM_STATS  (per season aggregates)
-- ─────────────────────────────────────────
CREATE TABLE team_stats (
    id                  SERIAL PRIMARY KEY,
    team_id             INT NOT NULL REFERENCES teams(id),
    season              VARCHAR(10) NOT NULL,
    matches_played      INT DEFAULT 0,
    wins                INT DEFAULT 0,
    draws               INT DEFAULT 0,
    losses              INT DEFAULT 0,
    goals_scored        INT DEFAULT 0,
    goals_conceded      INT DEFAULT 0,
    goal_difference     INT GENERATED ALWAYS AS (goals_scored - goals_conceded) STORED,
    points              INT GENERATED ALWAYS AS (wins*3 + draws) STORED,
    league_position     INT,
    avg_possession      FLOAT,
    avg_shots_per_match FLOAT,
    updated_at          TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_id, season)
);

CREATE INDEX idx_team_stats_team   ON team_stats(team_id);
CREATE INDEX idx_team_stats_season ON team_stats(season);

-- ─────────────────────────────────────────
-- FEATURES  (engineered ML features)
-- ─────────────────────────────────────────
CREATE TABLE features (
    id                    SERIAL PRIMARY KEY,
    match_id              INT NOT NULL REFERENCES matches(id),
    home_form_last5       FLOAT,
    away_form_last5       FLOAT,
    home_goal_avg         FLOAT,
    away_goal_avg         FLOAT,
    home_conceded_avg     FLOAT,
    away_conceded_avg     FLOAT,
    home_advantage        FLOAT,
    head_to_head_score    FLOAT,
    home_league_position  INT,
    away_league_position  INT,
    home_strength_score   FLOAT,
    away_strength_score   FLOAT,
    created_at            TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_features_match ON features(match_id);

-- ─────────────────────────────────────────
-- PREDICTIONS
-- ─────────────────────────────────────────
CREATE TABLE predictions (
    id              SERIAL PRIMARY KEY,
    home_team_id    INT NOT NULL REFERENCES teams(id),
    away_team_id    INT NOT NULL REFERENCES teams(id),
    home_win_prob   FLOAT NOT NULL,
    draw_prob       FLOAT NOT NULL,
    away_win_prob   FLOAT NOT NULL,
    predicted_result VARCHAR(10),
    confidence      FLOAT,
    model_version   VARCHAR(50),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_predictions_home ON predictions(home_team_id);
CREATE INDEX idx_predictions_away ON predictions(away_team_id);