"""
PhishGuard - Predictor
Loads the trained model and exposes a clean predict() interface.
"""

import os
import sys
import joblib
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from feature_extractor import extract_features, FEATURE_NAMES

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH  = os.path.join(BASE_DIR, 'models', 'phishguard_model.joblib')
SCALER_PATH = os.path.join(BASE_DIR, 'models', 'scaler.joblib')


class PhishGuardPredictor:
    """Wraps the trained model for single-URL and batch prediction."""

    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Run `python src/train_model.py` first."
            )
        self.model  = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)

    def predict(self, url: str) -> dict:
        """
        Predict whether a URL is phishing or legitimate.

        Returns a dict:
          label      : 'Phishing' | 'Legitimate'
          confidence : float (0–1), confidence in the predicted class
          phish_prob : float (0–1), raw probability of being phishing
          risk_level : 'High' | 'Medium' | 'Low'
          features   : dict of extracted features
        """
        features = extract_features(url)
        X = np.array([list(features.values())], dtype=float)
        X_scaled = self.scaler.transform(X)

        prediction  = self.model.predict(X_scaled)[0]
        probabilities = self.model.predict_proba(X_scaled)[0]
        phish_prob  = float(probabilities[1])
        legit_prob  = float(probabilities[0])

        label      = 'Phishing' if prediction == 1 else 'Legitimate'
        confidence = phish_prob if prediction == 1 else legit_prob

        if phish_prob >= 0.75:
            risk_level = 'High'
        elif phish_prob >= 0.40:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'

        return {
            'url':        url,
            'label':      label,
            'confidence': round(confidence, 4),
            'phish_prob': round(phish_prob, 4),
            'legit_prob': round(legit_prob, 4),
            'risk_level': risk_level,
            'features':   features,
        }

    def predict_batch(self, urls: list) -> list:
        """Predict for a list of URLs. Returns list of result dicts."""
        return [self.predict(url) for url in urls]


# ── CLI quick-test ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    predictor = PhishGuardPredictor()

    test_cases = [
        ('https://www.google.com/search?q=machine+learning', 'Legitimate'),
        ('http://paypal-secure-verify-account.xyz/login.php', 'Phishing'),
        ('https://github.com/features',                       'Legitimate'),
        ('http://192.168.0.1/admin/login.php',                'Phishing'),
        ('http://apple.signin-verify-suspended.ml/update.php','Phishing'),
        ('https://stackoverflow.com/questions/tagged/python', 'Legitimate'),
    ]

    print(f"\n{'URL':<55} {'Expected':<12} {'Got':<12} {'Phish%':<8} {'Risk'}")
    print('-' * 100)
    correct = 0
    for url, expected in test_cases:
        r = predictor.predict(url)
        match = '✓' if r['label'] == expected else '✗'
        correct += (r['label'] == expected)
        print(f"{match} {url[:52]:<53} {expected:<12} {r['label']:<12} {r['phish_prob']:.2f}     {r['risk_level']}")

    print(f"\nAccuracy on test cases: {correct}/{len(test_cases)}")
