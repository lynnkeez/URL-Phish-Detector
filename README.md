# URL Phishing Guard

A locally-run, machine learning-powered phishing URL detection system. Built
as an individual project for APT3065 (Concept Paper: LynnBetty Mawira,
669931). Classifies submitted URLs as **Phishing** or **Legitimate** in
real time using a Random Forest classifier trained on lexical and
structural URL features — no external API calls, no URL storage or
logging, sub-2-second response time.

## Project structure

```
phishguard/
├── app.py                     # Flask web app + REST API
├── requirements.txt           # Python dependencies
├── src/
│   ├── feature_extractor.py   # 30 URL features extraction
│   ├── dataset_generator.py   # Synthetic training data
│   ├── train_model.py         # Training + evaluation pipeline
│   └── predictor.py           # Inference wrapper
├── templates/
│   ├── base.html
│   ├── index.html             # Dark-themed web UI
│   ├── about.html
│   ├── history.html
│   └── result.html
├── models/                    # Trained Random Forest model
│   ├── metrics.json
│   ├── phishguard_model.joblib
│   └── scaler.joblib
└── data/
    └── urls.csv                # 6,000-sample dataset
```

## Success criteria

- Model accuracy ≥ 90%, F1-score ≥ 0.88 on held-out test data
- Classification returned within 2 seconds of submission
- Functional in a standard desktop browser with no installation required

## Setup

```bash
git clone https://github.com/<your-username>/phishguard.git
cd phishguard
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Generate the dataset (if `data/urls.csv` isn't already present)

```bash
python src/dataset_generator.py
```

## Train the model

```bash
python src/train_model.py --data data/urls.csv --out models/phishguard_model.joblib
```

This prints accuracy, F1, precision, recall, and the top 10 most important
features, and saves the trained model to `models/`.

## Run the web app

```bash
python app.py
```

Visit `http://localhost:5000`, enter a URL, and get a classification,
confidence score, and an explanation of the top features that drove the
decision.

## Methodology notes

- **Feature engineering:** 30 lexical, structural, and host-based features
  extracted directly from the raw URL string (see `src/feature_extractor.py`)
  — no network calls, no page rendering.
- **Domain-aware evaluation:** the train/test split uses
  `StratifiedGroupKFold`, grouped by registrable domain, so no domain (e.g.
  `paypal-secure1.tk` / `paypal-secure2.tk`) appears on both sides of the
  split. This prevents domain leakage from inflating accuracy.
- **Privacy:** submitted URLs are processed in-memory only. Session history
  is stored client-side/session-only and is never logged to disk or a
  database.

## Version control

This project follows a simplified GitFlow strategy (`main` / `develop` /
`feature branches`) with branch protection on `main` and semantic version
tags at each sprint boundary. See `BRANCHING_STRATEGY.md` for details.

## License / Academic context

Submitted as coursework for APT3065, Summer 2026 semester. Not intended
for production deployment.
