"""Measure local prediction latency and save reproducible test evidence."""

import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from predictor import PhishGuardPredictor

URLS = [
    "https://www.google.com",
    "https://github.com/features",
    "http://paypal.login.verify.example.zip/%41",
    "http://192.168.1.1/login",
]


def main():
    predictor = PhishGuardPredictor()
    timings = []
    results = []
    for url in URLS:
        started = time.perf_counter()
        prediction = predictor.predict(url)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        timings.append(elapsed_ms)
        results.append({"url": url, "label": prediction["label"], "latency_ms": elapsed_ms})
    evidence = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "pass_criterion_ms": 2000,
        "mean_latency_ms": round(statistics.mean(timings), 2),
        "max_latency_ms": max(timings),
        "passed": max(timings) < 2000,
        "cases": results,
    }
    os.makedirs("test_evidence", exist_ok=True)
    with open("test_evidence/performance.json", "w", encoding="utf-8") as file:
        json.dump(evidence, file, indent=2)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
