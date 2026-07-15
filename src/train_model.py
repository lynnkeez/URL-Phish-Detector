"""
train_model.py
Trains a Random Forest classifier on labeled URLs.

Works with the PhiUSIIL dataset which already has pre-computed features.
No feature_extractor needed — we use the dataset's existing numeric columns.

Uses a domain-aware, stratified split (StratifiedGroupKFold) so that no
registrable domain appears in both the train and test sets. A plain random
split can leak the same domain across both sides and inflate accuracy —
this keeps the evaluation honest.

Usage:
    python src/train_model.py --data data/urls.csv --out model.joblib
"""

import os
import json
import argparse
from urllib.parse import urlparse

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    classification_report, confusion_matrix
)
import joblib

# Columns to drop — not useful as ML features
DROP_COLS = ["FILENAME", "URL", "Title", "label"]


def registrable_domain(url: str) -> str:
    """Best-effort 'domain group' for a URL: last two dot-separated host
    labels (e.g. 'mail.paypal-secure.tk' -> 'paypal-secure.tk'). Falls back
    to the raw host, or the raw URL string if host is missing."""
    try:
        parsed_input = str(url) if "://" in str(url) else "http://" + str(url)
        host = urlparse(parsed_input).netloc.split(":")[0].split("@")[-1].lower()
        if not host:
            return str(url)
        parts = host.split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else host
    except Exception:
        return str(url)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/urls.csv", help="Path to PhiUSIIL CSV")
    parser.add_argument("--out",  default="model.joblib",  help="Where to save the trained model")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    # ── Load dataset ───────────────────────────────────────────────────────
    print(f"Loading data from {args.data} ...")
    df = pd.read_csv(args.data)

    # PhiUSIIL uses uppercase 'URL' — fix column reference
    df = df.dropna(subset=["URL", "label"])
    df["label"] = df["label"].astype(int)

    print(f"Rows loaded : {len(df)}")
    print(f"Phishing    : {df['label'].sum()}")
    print(f"Legitimate  : {(df['label'] == 0).sum()}")

    # ── Build feature matrix from existing dataset columns ─────────────────
    # Drop non-numeric / non-feature columns
    drop = [c for c in DROP_COLS if c in df.columns]
    feature_cols = [c for c in df.columns if c not in drop]

    X = df[feature_cols].copy()
    y = df["label"].values

    # Convert everything to numeric, fill gaps with 0
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)

    print(f"\nFeature matrix : {X.shape[0]} rows x {X.shape[1]} features")

    # ── Domain-aware split ─────────────────────────────────────────────────
    domains = df["URL"].apply(registrable_domain).reset_index(drop=True)
    print(f"Unique domains : {domains.nunique()}")

    n_splits = max(round(1 / args.test_size), 2)
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    train_idx, test_idx = next(sgkf.split(X, y, groups=domains))

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    train_domains = set(domains.iloc[train_idx])
    test_domains  = set(domains.iloc[test_idx])
    overlap       = train_domains & test_domains
    print(
        f"Split : {len(X_train)} train / {len(X_test)} test rows "
        f"({len(train_domains)} / {len(test_domains)} unique domains, "
        f"{len(overlap)} overlapping domains)"
    )

    # ── Scale features ─────────────────────────────────────────────────────
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    # ── Train ──────────────────────────────────────────────────────────────
    print("\nTraining Random Forest (may take 1-2 minutes) ...")
    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    clf.fit(X_train_s, y_train)

    # ── Evaluate ───────────────────────────────────────────────────────────
    y_pred = clf.predict(X_test_s)
    print("\n=== Evaluation on held-out test set ===")
    print(f"Accuracy  : {accuracy_score(y_test, y_pred):.4f}")
    print(f"F1-score  : {f1_score(y_test, y_pred):.4f}")
    print(f"Precision : {precision_score(y_test, y_pred):.4f}")
    print(f"Recall    : {recall_score(y_test, y_pred):.4f}")
    print("\nClassification report:\n", classification_report(y_test, y_pred))
    print("Confusion matrix:\n", confusion_matrix(y_test, y_pred))

    importances = sorted(
        zip(X.columns, clf.feature_importances_), key=lambda x: -x[1]
    )
    print("\nTop 10 most important features:")
    for name, imp in importances[:10]:
        bar = "█" * int(imp * 300)
        print(f"  {name:35s} {imp:.4f}  {bar}")

    # ── Save model + scaler + feature names ───────────────────────────────
    # Save model.joblib in the same format your app.py expects:
    # {"model": clf, "feature_names": [...]}
    joblib.dump({"model": clf, "feature_names": list(X.columns)}, args.out)
    print(f"\n[✓] Model saved → {args.out}")

    # Also save scaler and feature names for the Flask app
    os.makedirs("models", exist_ok=True)
    joblib.dump(scaler, os.path.join("models", "scaler.joblib"))
    with open(os.path.join("models", "feature_names.json"), "w") as f:
        json.dump(list(X.columns), f)

    print(f"[✓] Scaler saved → models/scaler.joblib")
    print(f"[✓] Feature names saved → models/feature_names.json")


if __name__ == "__main__":
    main()