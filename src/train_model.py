"""Train and evaluate PhishGuard using only URL-derived features."""

import argparse
import json
import os
import sys
from urllib.parse import urlparse

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

sys.path.insert(0, os.path.dirname(__file__))
from feature_extractor import FEATURE_NAMES, extract_features


def registrable_domain(url: str) -> str:
    hostname = urlparse(str(url) if "://" in str(url) else "http://" + str(url)).hostname or str(url)
    parts = hostname.lower().split(".")
    return ".".join(parts[-2:]) if len(parts) > 1 else hostname


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/urls.csv")
    parser.add_argument("--out", default="models/phishguard_model.joblib")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    data = pd.read_csv(args.data, usecols=["URL", "label"]).dropna()
    # PhiUSIIL uses 1 for legitimate and 0 for phishing. Convert to an explicit
    # target where 1 always means phishing throughout this project.
    target = (data["label"].astype(int) == 0).astype(int)
    print(f"Rows: {len(data)} | phishing: {target.sum()} | legitimate: {(target == 0).sum()}")
    print("Extracting URL-only features...")

    def extract_training_record(url):
        try:
            return extract_features(url, enforce_length=False)
        except ValueError:
            return None

    records = data["URL"].map(extract_training_record)
    valid_rows = records.notna()
    if not valid_rows.all():
        print(f"Skipping {(~valid_rows).sum()} malformed URLs.")
        data = data.loc[valid_rows].reset_index(drop=True)
        target = target.loc[valid_rows].reset_index(drop=True)
        records = records.loc[valid_rows]
    features = pd.DataFrame.from_records(records.tolist(), columns=FEATURE_NAMES).fillna(0)
    groups = data["URL"].map(registrable_domain)
    folds = max(round(1 / args.test_size), 2)
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=42)
    train_index, test_index = next(splitter.split(features, target, groups))
    model = RandomForestClassifier(n_estimators=300, min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=-1)
    model.fit(features.iloc[train_index], target.iloc[train_index])
    predicted = model.predict(features.iloc[test_index])
    probabilities = model.predict_proba(features.iloc[test_index])[:, 1]
    metrics = {
        "accuracy": round(float(accuracy_score(target.iloc[test_index], predicted)), 4),
        "f1_score": round(float(f1_score(target.iloc[test_index], predicted)), 4),
        "precision": round(float(precision_score(target.iloc[test_index], predicted)), 4),
        "recall": round(float(recall_score(target.iloc[test_index], predicted)), 4),
        "roc_auc": round(float(roc_auc_score(target.iloc[test_index], probabilities)), 4),
        "train_size": len(train_index), "test_size": len(test_index), "n_features": len(FEATURE_NAMES),
        "confusion_matrix": confusion_matrix(target.iloc[test_index], predicted).tolist(),
        "feature_importance": dict(sorted(zip(FEATURE_NAMES, model.feature_importances_), key=lambda item: -item[1])[:10]),
    }
    print(json.dumps(metrics, indent=2))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES}, args.out)
    with open(os.path.join(os.path.dirname(args.out) or ".", "metrics.json"), "w", encoding="utf-8") as output:
        json.dump(metrics, output, indent=2)


if __name__ == "__main__":
    main()
