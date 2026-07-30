"""Inference wrapper for the URL-only PhishGuard model."""

import os
import sys
import joblib
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from feature_extractor import FEATURE_NAMES, extract_features, normalise_url

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "phishguard_model.joblib")


class PhishGuardPredictor:
    def __init__(self, model_path=MODEL_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError("Model not found. Run `python src/train_model.py` first.")
        self.bundle = joblib.load(model_path)
        self.model = self.bundle["model"]
        self.feature_names = self.bundle.get("feature_names", FEATURE_NAMES)
        if self.feature_names != FEATURE_NAMES:
            raise FileNotFoundError(
                "Model uses an older feature set. Run `python src/train_model.py` to retrain the URL-only model."
            )

    def predict(self, url: str) -> dict:
        normalised = normalise_url(url)
        features = extract_features(normalised)
        matrix = pd.DataFrame([[features[name] for name in self.feature_names]], columns=self.feature_names)
        phish_probability = float(self.model.predict_proba(matrix)[0][1])
        is_phishing = phish_probability >= 0.5
        confidence = phish_probability if is_phishing else 1 - phish_probability
        risk_level = "High" if phish_probability >= 0.75 else "Medium" if phish_probability >= 0.4 else "Low"
        return {
            "url": normalised,
            "label": "Phishing" if is_phishing else "Legitimate",
            "is_phishing": is_phishing,
            "confidence": round(confidence * 100, 1),
            "phish_probability": round(phish_probability * 100, 1),
            "risk_level": risk_level,
            "features": features,
            "feature_names": self.feature_names,
        }
