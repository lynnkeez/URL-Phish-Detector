import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feature_extractor import FEATURE_NAMES, extract_features, normalise_url


class FeatureExtractorTests(unittest.TestCase):
    def test_adds_scheme_and_preserves_feature_order(self):
        features = extract_features("example.com/login")
        self.assertEqual(list(features), FEATURE_NAMES)
        self.assertEqual(normalise_url("example.com"), "http://example.com")

    def test_flags_common_phishing_indicators(self):
        features = extract_features("http://paypal.login.verify.example.zip/%41")
        self.assertEqual(features["suspicious_tld"], 1)
        self.assertEqual(features["brand_in_subdomain"], 1)
        self.assertGreater(features["phishing_keyword_count"], 0)
        self.assertEqual(features["has_encoded_char"], 1)

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            normalise_url("not a valid url")
        with self.assertRaises(ValueError):
            normalise_url("ftp://example.com")

    def test_training_can_extract_long_historical_urls(self):
        long_url = "https://example.com/" + "a" * 300
        self.assertGreater(extract_features(long_url, enforce_length=False)["url_length"], 255)

    def test_web_length_boundary_is_enforced(self):
        accepted = "https://e.co/" + "a" * (255 - len("https://e.co/"))
        rejected = accepted + "a"
        self.assertEqual(normalise_url(accepted), accepted)
        with self.assertRaises(ValueError):
            normalise_url(rejected)


if __name__ == "__main__":
    unittest.main()
