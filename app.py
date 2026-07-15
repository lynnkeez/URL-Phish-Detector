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
import os

from feature_extraction import extract_features

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

MODEL_PATH = "model.joblib"
_bundle = None


def get_model():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def classify(url: str) -> dict:
    """Run the model on a URL and build the result dict used by result.html."""
    bundle = get_model()
    model = bundle["model"]
    feature_names = bundle["feature_names"]

    feats = extract_features(url)
    X = pd.DataFrame([feats])[feature_names]

    pred = model.predict(X)[0]
    proba = model.predict_proba(X)[0]
    confidence = round(max(proba) * 100, 1)
    label = "Phishing" if pred == 1 else "Legitimate"

    importances = sorted(
        zip(feature_names, model.feature_importances_), key=lambda x: -x[1]
    )[:5]
    top_importance = importances[0][1] if importances else 1
    explanation = [
        {
            "feature": name.replace("_", " "),
            "value": feats[name],
            "importance": round(imp, 3),
            "bar_pct": round((imp / top_importance) * 100, 1) if top_importance else 0,
        }
        for name, imp in importances
    ]

    return {
        "url": url,
        "label": label,
        "is_phishing": bool(pred == 1),
        "confidence": confidence,
        "explanation": explanation,
    }


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
                    "url": url,
                    "label": result["label"],
                    "confidence": result["confidence"],
                })
                session["history"] = history[:10]  # keep last 10, session-only

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
