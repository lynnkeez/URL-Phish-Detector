import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

SAMPLE = {
    "url": "https://example.com", "label": "Legitimate", "is_phishing": False,
    "confidence": 91.0, "phish_probability": 9.0, "risk_level": "Low",
    "features": {"has_https": 1, "suspicious_tld": 0, "ip_address": 0,
                 "brand_in_subdomain": 0, "phishing_keyword_count": 0,
                 "has_encoded_char": 0, "has_at_symbol": 0, "subdomain_count": 0},
}


class AppTests(unittest.TestCase):
    def setUp(self):
        app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = app.app.test_client()

    @patch("app.check_url", return_value=SAMPLE)
    def test_api_returns_prediction(self, _check_url):
        response = self.client.post("/api/check", json={"url": "https://example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["label"], "Legitimate")

    def test_api_rejects_missing_url(self):
        response = self.client.post("/api/check", json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    @patch("app.check_url", return_value=SAMPLE)
    def test_form_stores_session_history(self, _check_url):
        response = self.client.post("/", data={"url": "https://example.com"})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertEqual(len(session["history"]), 1)

    def test_clear_history_removes_session_data(self):
        with self.client.session_transaction() as session:
            session["history"] = [SAMPLE]
        response = self.client.post("/clear-history")
        self.assertEqual(response.status_code, 204)
        with self.client.session_transaction() as session:
            self.assertNotIn("history", session)


if __name__ == "__main__":
    unittest.main()
