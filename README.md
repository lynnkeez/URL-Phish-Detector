# PhishGuard

PhishGuard is a local Flask application that estimates phishing risk from a URL's structure. It uses no external lookups or page rendering: training, evaluation, and live predictions all use the same 31 URL-only features.

## Why URL-only?

The source dataset includes webpage-content fields such as image counts and page titles. Those cannot be known safely without visiting a submitted link, so PhishGuard deliberately does **not** train on them. This keeps the live application, training data, and evaluation method aligned.

The output is risk guidance, not a guarantee that a site is safe. Users should not enter passwords or sensitive information based only on this result.

## Setup and run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src\train_model.py
python app.py
```

Then open `http://127.0.0.1:5000`.

Set a unique `SECRET_KEY` environment variable before deployment. Set `FLASK_DEBUG=1` only for local development.

## Training and evaluation

`src/train_model.py` derives all features from the raw URL column, converts the dataset target to `1 = phishing`, uses a domain-grouped stratified split, and writes the model plus held-out metrics to `models/`.

Run tests with:

```powershell
python -m unittest discover -s tests -v
```

See [TESTING.md](TESTING.md) for the test strategy, acceptance checklist, evidence procedure, and results-analysis guidance.

## API

`POST /api/check` accepts JSON such as `{"url": "https://example.com"}` and returns a label, confidence, phishing probability, risk level, and URL-specific indicators.

## Limitations

- A URL-only classifier cannot detect every compromised legitimate domain.
- HTTPS encrypts a connection; it does not prove a website is trustworthy.
- Results should be assessed alongside user awareness and organisation security controls.
