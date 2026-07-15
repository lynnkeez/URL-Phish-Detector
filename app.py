"""
app.py
Flask web application for URL Phishing Guard.
Loads the trained model and serves 4 pages:
  /            - URL input & submission
  /result      - classification result + explanation for the last URL checked
  /history     - session-only history of URLs checked
  /about       - how the model works (methodology, constraints, criteria)

No submitted URL is logged or stored server-side (processed in-memory only,
result/history data lives only in the signed session cookie), per Q16/Q13.
"""

from flask import Flask, render_template, request, session, redirect, url_for
import joblib
import pandas as pd
import numpy as np
import os
import re
import math
import json
from collections import Counter
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

MODEL_PATH      = "model.joblib"
SCALER_PATH     = os.path.join("models", "scaler.joblib")
FEAT_NAMES_PATH = os.path.join("models", "feature_names.json")

_bundle        = None
_scaler        = None
_feature_names = None


# ── Model loader ───────────────────────────────────────────────────────────

def get_model():
    global _bundle, _scaler, _feature_names
    if _bundle is None:
        _bundle = joblib.load(MODEL_PATH)
        if os.path.exists(SCALER_PATH):
            _scaler = joblib.load(SCALER_PATH)
        if os.path.exists(FEAT_NAMES_PATH):
            with open(FEAT_NAMES_PATH) as f:
                _feature_names = json.load(f)
        else:
            _feature_names = _bundle.get("feature_names", [])
    return _bundle


# ── Feature extraction (replaces feature_extractor.py) ────────────────────

LEGIT_TLDS = {'.com', '.org', '.net', '.edu', '.gov', '.io', '.co'}


def _entropy(s):
    if not s:
        return 0.0
    freq = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def extract_features(url: str) -> dict:
    """
    Extract numeric features from a URL string.
    Column names match the PhiUSIIL dataset so they align with the trained model.
    """
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    try:
        parsed = urlparse(url)
    except Exception:
        return {}

    scheme   = parsed.scheme or ''
    netloc   = parsed.netloc or ''
    path     = parsed.path or ''
    query    = parsed.query or ''
    full     = url.lower()
    hostname = netloc.split(':')[0].lower()
    domain   = re.sub(r'^www\.', '', hostname)
    parts    = domain.split('.')
    tld      = ('.' + parts[-1]) if len(parts) > 1 else ''
    sld      = parts[-2] if len(parts) > 1 else ''
    subs     = parts[:-2] if len(parts) > 2 else []

    return {
        'URLLength'                  : len(url),
        'DomainLength'               : len(domain),
        'IsDomainIP'                 : int(bool(re.match(r'^\d{1,3}(\.\d{1,3}){3}$', hostname))),
        'TLDLength'                  : len(tld),
        'NoOfSubDomain'              : len(subs),
        'HasObfuscation'             : int('%' in url or '@' in url),
        'NoOfObfuscatedChar'         : url.count('%'),
        'ObfuscationRatio'           : round(url.count('%') / max(len(url), 1), 4),
        'NoOfLettersInURL'           : sum(c.isalpha() for c in url),
        'LetterRatioInURL'           : round(sum(c.isalpha() for c in url) / max(len(url), 1), 4),
        'NoOfDegitsInURL'            : sum(c.isdigit() for c in url),
        'DegitRatioInURL'            : round(sum(c.isdigit() for c in url) / max(len(url), 1), 4),
        'NoOfEqualsInURL'            : url.count('='),
        'NoOfQMarkInURL'             : url.count('?'),
        'NoOfAmpersandInURL'         : url.count('&'),
        'NoOfOtherSpecialCharsInURL' : sum(c in '-_.~!*()' for c in url),
        'SpacialCharRatioInURL'      : round(sum(c in '-_.~!*()@%' for c in url) / max(len(url), 1), 4),
        'IsHTTPS'                    : int(scheme == 'https'),
        'LineOfCode'                 : 0,
        'LargestLineLength'          : 0,
        'HasTitle'                   : 0,
        'DomainTitleMatchScore'      : 0,
        'URLTitleMatchScore'         : 0,
        'HasFavicon'                 : 0,
        'Robots'                     : 0,
        'IsResponsive'               : 0,
        'NoOfURLRedirect'            : 0,
        'NoOfSelfRedirect'           : 0,
        'HasDescription'             : 0,
        'NoOfPopup'                  : 0,
        'NoOfiFrame'                 : 0,
        'HasExternalFormSubmit'      : 0,
        'HasSocialNet'               : 0,
        'HasSubmitButton'            : 0,
        'HasHiddenFields'            : 0,
        'HasPasswordField'           : int('password' in full or 'passwd' in full),
        'Bank'                       : int('bank' in full),
        'Pay'                        : int('pay' in full),
        'Crypto'                     : int('crypto' in full or 'bitcoin' in full or 'wallet' in full),
        'HasCopyrightInfo'           : 0,
        'NoOfImage'                  : 0,
        'NoOfCSS'                    : 0,
        'NoOfJS'                     : 0,
        'NoOfSelfRef'                : 0,
        'NoOfEmptyRef'               : 0,
        'NoOfExternalRef'            : 0,
        'URLSimilarityIndex'         : round(_entropy(sld), 4),
        'CharContinuationRate'       : round(len(re.findall(r'(.)\1', url)) / max(len(url), 1), 4),
        'TLDLegitimateProb'          : 1.0 if tld in LEGIT_TLDS else 0.1,
        'URLCharProb'                : round(sum(c.isalnum() for c in url) / max(len(url), 1), 4),
    }


# ── Classifier ─────────────────────────────────────────────────────────────

def classify(url: str) -> dict:
    """Run the model on a URL and build the result dict used by result.html."""
    bundle       = get_model()
    model        = bundle["model"]
    feature_names = _feature_names or bundle.get("feature_names", [])

    feats = extract_features(url)

    # Build DataFrame in the exact column order the model expects
    row = {col: feats.get(col, 0) for col in feature_names}
    X = pd.DataFrame([row])[feature_names]

    # Apply scaler if available
    if _scaler is not None:
        X = pd.DataFrame(_scaler.transform(X), columns=feature_names)

    pred       = model.predict(X)[0]
    proba      = model.predict_proba(X)[0]
    confidence = round(max(proba) * 100, 1)
    label      = "Phishing" if pred == 1 else "Legitimate"

    importances = sorted(
        zip(feature_names, model.feature_importances_), key=lambda x: -x[1]
    )[:5]
    top_importance = importances[0][1] if importances else 1
    explanation = [
        {
            "feature"   : name.replace("_", " "),
            "value"     : feats.get(name, 0),
            "importance": round(imp, 3),
            "bar_pct"   : round((imp / top_importance) * 100, 1) if top_importance else 0,
        }
        for name, imp in importances
    ]

    return {
        "url"        : url,
        "label"      : label,
        "is_phishing": bool(pred == 1),
        "confidence" : confidence,
        "explanation": explanation,
    }


# ── Routes (unchanged from your original) ─────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    error = None

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        if not url:
            error = "Please enter a URL."
        else:
            try:
                result = classify(url)
                session["last_result"] = result

                history = session.get("history", [])
                history.insert(0, {
                    "url"       : url,
                    "label"     : result["label"],
                    "confidence": result["confidence"],
                })
                session["history"] = history[:10]

                return redirect(url_for("result"))

            except FileNotFoundError:
                error = "Model not found. Run train_model.py first to generate model.joblib."
            except Exception as e:
                error = f"Could not process that URL: {e}"

    return render_template("index.html", error=error, active="check")


@app.route("/result", methods=["GET"])
def result():
    return render_template(
        "result.html",
        result=session.get("last_result"),
        active="result",
    )


@app.route("/history", methods=["GET"])
def history():
    return render_template(
        "history.html",
        history=session.get("history", []),
        active="history",
    )


@app.route("/clear-history", methods=["POST"])
def clear_history():
    session.pop("history", None)
    return ("", 204)


@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html", active="about")


if __name__ == "__main__":
    app.run(debug=True, port=5000)