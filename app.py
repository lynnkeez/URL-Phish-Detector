"""Flask interface and small JSON API for the URL-only PhishGuard model."""

import os
import sys
from functools import lru_cache

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from predictor import PhishGuardPredictor

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or "development-only-change-before-deployment",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)


@lru_cache(maxsize=1)
def get_predictor():
    return PhishGuardPredictor()


def explain_prediction(result: dict) -> list:
    """Return URL-specific indicators, rather than misleading global importance."""
    values = result["features"]
    indicators = []
    rules = [
        ("Suspicious top-level domain", values["suspicious_tld"], "This domain ending is frequently abused in malicious campaigns."),
        ("IP address used as a host", values["ip_address"], "Legitimate public services normally use a named domain."),
        ("Brand name in a subdomain", values["brand_in_subdomain"], "A brand in a subdomain can impersonate the real organisation."),
        ("Phishing-related words", values["phishing_keyword_count"], "Words such as login, verify, or account can be used to pressure users."),
        ("Encoded or obfuscated characters", values["has_encoded_char"] or values["has_at_symbol"], "Obfuscation can disguise the actual destination."),
        ("Many subdomains", values["subdomain_count"] >= 3, "Long subdomain chains can make a deceptive address harder to read."),
        ("HTTPS enabled", values["has_https"], "HTTPS protects the connection but does not by itself prove a site is safe."),
    ]
    for name, triggered, description in rules:
        if triggered:
            indicators.append({"feature": name, "value": "Detected", "description": description, "bar_pct": 100})
    if not indicators:
        indicators.append({"feature": "No strong lexical warning signs", "value": "Detected", "description": "The URL structure alone did not trigger a strong warning. Treat this as risk guidance, not a guarantee.", "bar_pct": 35})
    return indicators[:5]


def check_url(url: str) -> dict:
    result = get_predictor().predict(url)
    result["explanation"] = explain_prediction(result)
    return result


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        try:
            result = check_url(request.form.get("url", ""))
            session["last_result"] = result
            history = session.get("history", [])
            history.insert(0, {key: result[key] for key in ("url", "label", "confidence")})
            session["history"] = history[:10]
            return redirect(url_for("result"))
        except (ValueError, FileNotFoundError) as exc:
            error = str(exc)
    return render_template("index.html", error=error, active="check")


@app.post("/api/check")
def api_check():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(check_url(body.get("url", "")))
    except (ValueError, FileNotFoundError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/result")
def result():
    return render_template("result.html", result=session.get("last_result"), active="result")


@app.get("/history")
def history():
    return render_template("history.html", history=session.get("history", []), active="history")


@app.post("/clear-history")
def clear_history():
    session.pop("history", None)
    return "", 204


@app.get("/about")
def about():
    return render_template("about.html", active="about")


if __name__ == "__main__":
    app.run(port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
