# PhishGuard Testing Strategy and Evaluation

## 1. Objective and scope

The test objective is to show that PhishGuard correctly validates inputs, extracts stable URL-only features, returns usable predictions, protects session data, and meets its response-time target. The scope includes the Python feature pipeline, predictor, Flask pages/API, and local performance. It excludes external website scanning because the design intentionally makes no network requests.

| Test level | Objective | Tool and evidence | Pass criterion |
|---|---|---|---|
| Unit | Verify isolated feature and validation rules | `unittest`, console log | Every assertion passes |
| Integration | Verify Flask routes, JSON API, redirects, and session history work together | Flask test client, `unittest` log | Correct status, response body, and session state |
| System | Verify the trained model works end-to-end with the feature pipeline | `tests/test_system.py` | Valid output schema; each prediction < 2 s |
| Acceptance | Verify user-facing requirements in a browser | manual checklist below and screenshots | All critical scenarios accepted |

## 2. Test design

### Unit tests

`tests/test_feature_extractor.py` covers normalisation, stable feature ordering, phishing indicators, invalid schemes/whitespace, the 255-character web-input boundary, and long historical URLs during model training.

### Integration tests

`tests/test_app.py` uses Flask's test client and mocks model inference. It covers successful API output, missing API input, form redirect/session history, and clearing history. Mocking ensures route tests fail only for route/session defects, not because a model has not yet been retrained.

### System tests

`tests/test_system.py` runs against the real trained model. It tests safe-looking, suspicious, and IP-host URLs; validates the response schema and confidence range; and enforces the two-second response target. It is skipped—rather than falsely passed—until `src/train_model.py` has created a compatible model.

### Acceptance checklist

| ID | User scenario | Expected result | Result |
|---|---|---|---|
| AT-01 | Submit a valid URL | Verdict, confidence, and indicators are shown | Pending |
| AT-02 | Submit a URL without a scheme | App normalises it and returns a result | Pending |
| AT-03 | Submit blank, FTP, whitespace, or >255-char input | Clear validation message; no crash | Pending |
| AT-04 | View and clear history | Latest ten checks appear; clear removes them | Pending |
| AT-05 | Open the app on a desktop browser | Navigation, form, results, and About page are usable | Pending |
| AT-06 | Call `POST /api/check` with JSON | JSON prediction returned; missing URL returns HTTP 400 | Pending |

## 3. Execution procedure and evidence

Run the following after installing dependencies and retraining:

```cmd
python -m unittest discover -s tests -v > test_evidence\unit-integration-system.log 2>&1
type test_evidence\unit-integration-system.log
python scripts\run_performance_check.py
```

Capture screenshots for AT-01 to AT-05 and save them in `test_evidence/` using descriptive names, for example `AT-01-result.png`. Record the console log and `performance.json` alongside the completed acceptance table. Do not edit generated logs or performance output.

## 4. Results analysis guidance

Report the number of tests run, passed, failed, and skipped. Explain a skip—for example, the system test before retraining—as unavailable test preconditions, not a passing result.

Compare `performance.json`'s maximum latency with the 2,000 ms requirement. If the limit is missed, separate initial model-load time from repeat prediction time; loading is cached by the application, while normal requests use the already loaded model.

For model quality, use the held-out accuracy, precision, recall, F1, ROC-AUC, and confusion matrix written to `models/metrics.json`. Discuss false negatives as the higher security risk (a phishing URL classified legitimate) and false positives as the usability risk. The domain-grouped split intentionally produces a more conservative but more realistic score than a random split.

Known limitations: lexical URL analysis cannot identify every compromised legitimate domain, HTTPS is not proof of safety, and input patterns may change over time. These are design limitations rather than test failures and should be stated in the evaluation.
