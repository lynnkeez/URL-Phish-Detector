"""System checks that run only after a compatible model has been trained."""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from predictor import PhishGuardPredictor


class SystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.predictor = PhishGuardPredictor()
        except FileNotFoundError as exc:
            raise unittest.SkipTest(f"System model not ready: {exc}")

    def test_predictions_have_complete_schema_and_meet_response_target(self):
        urls = [
            "https://www.google.com",
            "http://paypal.login.verify.example.zip/%41",
            "http://192.168.1.1/login",
        ]
        for url in urls:
            started = time.perf_counter()
            result = self.predictor.predict(url)
            elapsed = time.perf_counter() - started
            self.assertLess(elapsed, 2.0, f"Prediction exceeded 2 seconds for {url}")
            self.assertIn(result["label"], {"Phishing", "Legitimate"})
            self.assertGreaterEqual(result["confidence"], 0)
            self.assertLessEqual(result["confidence"], 100)


if __name__ == "__main__":
    unittest.main()
