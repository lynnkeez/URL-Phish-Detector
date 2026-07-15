"""
train_model.py
Trains a Random Forest classifier on labeled URLs.

Expected input CSV (data/urls.csv) with columns:
    url,label
where label is 1 for phishing, 0 for legitimate.

Uses a domain-aware, stratified split (StratifiedGroupKFold) so that no
registrable domain (e.g. paypal-secure1.tk / paypal-secure2.tk) appears in
both the train and test sets. A plain random split can leak the same domain
across both sides and inflate accuracy — this keeps the evaluation honest.

Usage:
    python train_model.py --data data/urls.csv --out model.joblib
"""

import argparse
from urllib.parse import urlparse

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    classification_report, confusion_matrix
)
import joblib

from feature_extraction import extract_features, FEATURE_NAMES


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dropped = 0
    for url in df["url"]:
        try:
            rows.append(extract_features(str(url)))
        except Exception:
            rows.append({name: None for name in FEATURE_NAMES})
            dropped += 1
    if dropped:
        print(f"Warning: {dropped} URLs failed feature extraction and were zero-filled.")
    feat_df = pd.DataFrame(rows).fillna(0)
    return feat_df


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
    parser.add_argument("--data", default="data/urls.csv", help="Path to labeled CSV (url,label)")
    parser.add_argument("--out", default="model.joblib", help="Where to save the trained model")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    print(f"Loading data from {args.data} ...")
    df = pd.read_csv(args.data)
    df = df.dropna(subset=["url", "label"])
    df["label"] = df["label"].astype(int)

    print(f"Rows loaded: {len(df)}  (phishing={df['label'].sum()}, legit={(df['label']==0).sum()})")

    domains = df["url"].apply(registrable_domain).reset_index(drop=True)
    print(f"Unique domains: {domains.nunique()}")

    print("Extracting features ...")
    X = build_feature_matrix(df).reset_index(drop=True)
    y = df["label"].reset_index(drop=True).values

    # Domain-aware split: pick n_splits so the held-out fold is ~test_size
    # of the data, then take one fold as the test set. StratifiedGroupKFold
    # keeps class balance similar across folds while guaranteeing every
    # domain's rows stay entirely on one side of the split.
    n_splits = max(round(1 / args.test_size), 2)
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    train_idx, test_idx = next(sgkf.split(X, y, groups=domains))

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    train_domains = set(domains.iloc[train_idx])
    test_domains = set(domains.iloc[test_idx])
    overlap = train_domains & test_domains
    print(
        f"Split: {len(X_train)} train / {len(X_test)} test rows "
        f"({len(train_domains)} / {len(test_domains)} unique domains, "
        f"{len(overlap)} overlapping domains)"
    )

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print("\n=== Evaluation on held-out test set ===")
    print(f"Accuracy : {accuracy_score(y_test, y_pred):.4f}")
    print(f"F1-score : {f1_score(y_test, y_pred):.4f}")
    print(f"Precision: {precision_score(y_test, y_pred):.4f}")
    print(f"Recall   : {recall_score(y_test, y_pred):.4f}")
    print("\nClassification report:\n", classification_report(y_test, y_pred))
    print("Confusion matrix:\n", confusion_matrix(y_test, y_pred))

    importances = sorted(
        zip(X.columns, clf.feature_importances_), key=lambda x: -x[1]
    )
    print("\nTop 10 most important features:")
    for name, imp in importances[:10]:
        print(f"  {name:30s} {imp:.4f}")

    joblib.dump({"model": clf, "feature_names": list(X.columns)}, args.out)
    print(f"\nModel saved to {args.out}")


if __name__ == "__main__":
    main()
