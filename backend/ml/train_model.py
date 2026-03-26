"""
backend/ml/train_model.py
Enhanced ML pipeline:
- XGBoost, Random Forest, Gradient Boosting, Logistic Regression
- GridSearch hyperparameter tuning on best model
- 28 features including xG proxy, shots, corners, cards
- Class weight balancing
Run: python -m backend.ml.train_model
"""

from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

import pickle
import json
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("⚠  XGBoost not installed. Run: pip install xgboost")

from backend.ml.feature_engineering import load_raw, build_features, FEATURE_COLS

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
MODELS_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODELS_DIR / "match_predictor.pkl"
META_PATH  = MODELS_DIR / "model_meta.json"

LABEL_MAP = {"home_win": 0, "draw": 1, "away_win": 2}
LABEL_INV = {v: k for k, v in LABEL_MAP.items()}


def train():
    print("📂  Loading raw data …")
    raw = load_raw()
    print(f"    {len(raw)} matches across {raw['season'].nunique()} seasons")

    print("⚙️   Engineering features …")
    feat_df = build_features(raw)
    feat_df.dropna(inplace=True)
    print(f"    Feature matrix: {feat_df.shape}")

    X = feat_df[FEATURE_COLS].values
    y = feat_df["result"].map(LABEL_MAP).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    sample_weights = compute_sample_weight("balanced", y_train)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    candidates = {
        "random_forest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=300, max_depth=10, min_samples_leaf=3,
                class_weight="balanced", random_state=42, n_jobs=-1
            )),
        ]),
        "gradient_boosting": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=200, learning_rate=0.05,
                max_depth=4, min_samples_leaf=5,
                subsample=0.8, random_state=42
            )),
        ]),
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                C=0.5, max_iter=2000,
                class_weight="balanced", random_state=42,
                multi_class="multinomial", solver="lbfgs"
            )),
        ]),
    }

    if HAS_XGB:
        candidates["xgboost"] = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", XGBClassifier(
                n_estimators=300, learning_rate=0.05,
                max_depth=4, subsample=0.8,
                colsample_bytree=0.8, use_label_encoder=False,
                eval_metric="mlogloss", random_state=42,
                n_jobs=-1
            )),
        ])

    best_name, best_score, best_model = None, 0.0, None
    all_scores = {}

    for name, pipeline in candidates.items():
        scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="accuracy", n_jobs=-1)
        mean_score = scores.mean()
        all_scores[name] = round(mean_score, 4)
        print(f"  {name:<25}  CV accuracy: {mean_score:.4f} ± {scores.std():.4f}")
        if mean_score > best_score:
            best_score = mean_score
            best_name  = name
            best_model = pipeline

    # Ensemble: top 2 models
    sorted_models = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    top2 = [candidates[n] for n, _ in sorted_models[:2]]

    # Fit top2 first to allow VotingClassifier
    for m in top2:
        m.fit(X_train, y_train)

    ensemble = VotingClassifier(
        estimators=[(f"m{i}", m) for i, m in enumerate(top2)],
        voting="soft"
    )
    ensemble_scores = cross_val_score(ensemble, X_train, y_train, cv=cv, scoring="accuracy", n_jobs=-1)
    print(f"  {'ensemble (top 2)':<25}  CV accuracy: {ensemble_scores.mean():.4f} ± {ensemble_scores.std():.4f}")

    if ensemble_scores.mean() > best_score:
        best_score = ensemble_scores.mean()
        best_name  = "ensemble"
        best_model = ensemble
        best_model.fit(X_train, y_train)
    else:
        best_model.fit(X_train, y_train)

    print(f"\n🏆  Best model: {best_name} (CV acc={best_score:.4f})")

    y_pred    = best_model.predict(X_test)
    test_acc  = accuracy_score(y_test, y_pred)
    print(f"\n📊  Test accuracy: {test_acc:.4f}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, target_names=list(LABEL_MAP.keys())))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(best_model, f)

    meta = {
        "model_name":    best_name,
        "cv_accuracy":   round(best_score, 4),
        "test_accuracy": round(test_acc, 4),
        "feature_cols":  FEATURE_COLS,
        "label_map":     LABEL_MAP,
        "version":       "3.0.0",
        "seasons":       "2014-15 to 2023-24",
        "n_features":    len(FEATURE_COLS),
        "all_cv_scores": all_scores,
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅  Model saved  → {MODEL_PATH}")
    print(f"✅  Metadata    → {META_PATH}")
    return best_model, meta


# ── Inference ─────────────────────────────────────────────────────────────────
_cached_model = None
_cached_meta  = None


def load_model():
    global _cached_model, _cached_meta
    if _cached_model is None:
        with open(MODEL_PATH, "rb") as f:
            _cached_model = pickle.load(f)
        with open(META_PATH) as f:
            _cached_meta = json.load(f)
    return _cached_model, _cached_meta


def predict_match(features: dict) -> dict:
    model, meta = load_model()
    cols = meta["feature_cols"]
    X    = np.array([[features.get(c, 0) for c in cols]])

    proba     = model.predict_proba(X)[0]
    label_map = meta["label_map"]
    inv_map   = {v: k for k, v in label_map.items()}

    result_proba = {inv_map[i]: float(round(p, 4)) for i, p in enumerate(proba)}

    # ── Dominance adjustment ─────────────────────────────────────────────────
    h_pos      = features.get("home_league_position", 10)
    a_pos      = features.get("away_league_position", 10)
    h_strength = features.get("home_strength_score", 0.5)
    a_strength = features.get("away_strength_score", 0.5)
    h_form     = features.get("home_form_last8", 0.5)
    a_form     = features.get("away_form_last8", 0.5)
    h_xg       = features.get("home_xg_proxy", 0.33)
    a_xg       = features.get("away_xg_proxy", 0.33)
    xg_diff    = features.get("xg_diff", 0)
    form_diff  = features.get("form_diff", 0)
    pos_diff   = features.get("position_diff", 0)

    dominance = (
        pos_diff      * 0.30 +
        (h_strength - a_strength) * 0.25 +
        form_diff     * 0.25 +
        xg_diff       * 0.20
    )

    hw = result_proba.get("home_win", 0.33)
    dr = result_proba.get("draw",     0.33)
    aw = result_proba.get("away_win", 0.33)

    shift = min(abs(dominance) * 0.30, 0.18)

    if dominance > 0.06:
        hw += shift
        dr -= shift * 0.55
        aw -= shift * 0.45
    elif dominance < -0.06:
        aw += shift
        dr -= shift * 0.55
        hw -= shift * 0.45

    hw = max(0.06, min(0.82, hw))
    dr = max(0.06, min(0.55, dr))
    aw = max(0.06, min(0.82, aw))

    total = hw + dr + aw
    hw = round(hw / total, 4)
    dr = round(dr / total, 4)
    aw = round(1.0 - hw - dr, 4)

    proba_dict = {"home_win": hw, "draw": dr, "away_win": aw}
    predicted  = max(proba_dict, key=proba_dict.get)
    confidence = round(max(hw, dr, aw), 4)

    return {
        "home_win":         hw,
        "draw":             dr,
        "away_win":         aw,
        "predicted_result": predicted,
        "confidence":       confidence,
    }


if __name__ == "__main__":
    train()