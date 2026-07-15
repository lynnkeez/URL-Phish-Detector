# URL Phishing Guard — Starter Scaffold

This is a working starting point for your concept paper's system. It covers
Objectives 2–4: feature engineering, model training, and the Flask web UI.

## 1. Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Get a labeled URL dataset

You need a CSV at `data/urls.csv` with two columns: `url,label`
(label = 1 for phishing, 0 for legitimate). Note: the classic UCI "Phishing
Websites" dataset already contains pre-extracted features, not raw URLs — it
won't work directly with this pipeline since the whole point is to do your
own feature engineering from raw URLs. Instead, use one of:

- **Kaggle: "Phishing URL Dataset"** (raw URL + label, ready to use)
- **PhishTank** (https://phishtank.org) verified phishing feed, combined with
  **Tranco** (https://tranco-list.eu) top-ranked domains as your legitimate class
- Any other raw-URL, labeled dataset — just make sure column names match
  `url` and `label`, or edit `train_model.py` accordingly

Aim for a reasonably balanced dataset (similar counts of phishing vs.
legitimate) of at least a few thousand rows for stable results.

## 3. Extract features & train the model

```bash
python train_model.py --data data/urls.csv --out model.joblib
```

This prints accuracy, F1, precision, recall, and the top 10 most important
features — check these against your success criteria (≥90% accuracy, F1 ≥ 0.88).

If you're short of that bar:
- add more features (e.g. count of `%` encoded chars, presence of `www`,
  ratio of vowels/consonants)
- tune `n_estimators` / `max_depth` in `train_model.py`
- check class balance in your dataset

## 4. Run the web app

```bash
python app.py
```

Visit http://localhost:5000, enter a URL, and you'll get a classification,
confidence score, and the top features driving the model's decision —
this covers the "explanation" requirement (Q12) and the 2-second response
target (Q13) since everything runs locally with no external API calls.

## Files

- `feature_extraction.py` — 22 lexical/structural features from a raw URL,
  no network calls needed (keeps it free, fast, and within your resource
  constraints per Q10/Q17)
- `train_model.py` — builds the feature matrix, trains a Random Forest,
  reports evaluation metrics, saves `model.joblib`
- `app.py` — Flask app: form → prediction → confidence + explanation +
  session-only history (nothing persisted, per your Q16 ethics statement)
- `templates/index.html` — minimal UI

## Suggested next steps against your 11-week plan

1. Week 1–2: literature review (already scoped in your paper) + finalize dataset source
2. Week 3–4: build & validate feature extraction, exploratory data analysis
3. Week 5–6: train/tune model, hit accuracy/F1 targets
4. Week 7–8: build out Flask UI, error handling for malformed URLs
5. Week 9: load/perf testing (20 concurrent requests, <2s response)
6. Week 10: polish explanation output, session history, styling
7. Week 11: write-up, demo, final report
