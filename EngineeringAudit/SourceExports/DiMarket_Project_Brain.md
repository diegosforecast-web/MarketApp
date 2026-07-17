# DiMarket - Project Brain

## Mission

Build the most trustworthy AI forecasting platform that an individual investor can access.

---

# Product Vision

DiMarket is an AI-powered stock forecasting platform accessible from any device through the internet.

Users can forecast every publicly traded ticker available through brokers such as Robinhood.

The platform combines:

- Deep Learning
- Machine Learning
- Statistical forecasting
- Technical indicators
- Ensemble AI

to generate trustworthy price forecasts.

---

# Subscription Plans

## Free

- 3 predictions
- Horizon:
    - 1 Day
    - 2 Days
    - 3 Days

---

## Standard ($8.99/month)

Unlimited predictions

Forecast horizon:

- up to 1 day

Bonus:

- 5 predictions
- up to 5-day horizon

---

## Premium ($16/month)

Unlimited predictions

Forecast horizon:

- up to 5 days

Bonus:

- 5 predictions
- up to 30-day horizon

---

## Gold ($49.99/month)

Unlimited

Unlimited horizon

Unlimited predictions

(Current backend supports up to ~60-day horizon.)

---

# UI Philosophy

Minimal.

Elegant.

Black theme.

Professional.

Inspired by premium trading platforms.

Main prediction card displays:

Ticker

Current Price

Forecast

Expected Move %

AI Confidence

Confidence Level

Details button

---

# Details View

Shows:

Individual model predictions

GRU

LSTM

GBM

Linear

Ensemble

Prediction interval

Market regime

Model agreement

AI explanation

Feature importance (future)

---

# Current Backend Status

Architecture reviewed.

Main project located in:

src/MarketApp/backend

Main components identified:

comparison/

core/

data/

endpoints/

features/

forecasters/

models/

models_to_deploy/

training/

---

# Important Findings

Feature engineering includes:

Returns

RSI

MACD

ATR

Volatility

Stochastic Oscillator

Ensemble architecture exists.

CompareEngine is modular.

GRU model implemented in PyTorch.

LSTM models stored as .h5.

TFT wrapper exists.

Regime classifier exists.

---

# Long-Term AI Vision

Adaptive ensemble weights based on historical performance.

Confidence based on:

Historical accuracy

Model agreement

Market regime

Volatility

Prediction horizon

Never fake certainty.

The system should prefer saying "Low Confidence" over pretending to know.

---

# Development Philosophy

Never sacrifice trust for marketing.

Every prediction should be explainable.

Transparency is a competitive advantage.

Accuracy is more important than quantity of features.

---

# Planned Architecture

Frontend

↓

FastAPI Backend

↓

Prediction Service

↓

Feature Engineering

↓

Model Runners

↓

Ensemble

↓

Confidence Engine

↓

API Response

↓

Frontend Prediction Card

---

# Sprint Status

Sprint 1:
Repository audit completed.

Sprint 2:
Begin implementation.

First goal:

Connect complete prediction pipeline.

---

# North Star

"We're trying to build the most trustworthy AI forecasting platform that an individual investor can access."


If you are reading this in a new ChatGPT conversation:
We are continuing development of DiMarket.
The complete engineering review has already been performed.
Please begin by reading:
DiMarket_Project_Brain.md
The current backend is located in:
src/MarketApp/backend
Do not redesign the project.
Continue improving it.
The current priority is:
Sprint 2
Complete the prediction pipeline.
After that:
Improve ensemble
Improve confidence engine
UI
Authentication
Stripe
SaaS deployment
The guiding principle is:
Build the most trustworthy AI forecasting platform that an individual investor can access.
Session Update (2026-07-04)
Current status:
Prediction pipeline connected.
Forecast endpoint operational.
Next sprint is focused on model quality rather than infrastructure.
Next tasks:
Improve GBM predictions.
Increase training data.
Verify feature ordering.
Integrate into ensemble.


LAST SESSION 07/04/26
# Sprint 3.1 Engineering Decisions

## Historical Data Architecture

A key architectural decision was made after auditing the forecasting pipeline.

Training and prediction now have different data requirements.

Prediction requires:

- Latest market prices
- Low latency
- Stable API

Training requires:

- Long historical datasets
- Thousands of observations
- Reproducible downloads

Therefore the project now separates these responsibilities.

Prediction Pipeline

MarketDataService

↓

Alpha Vantage

Training Pipeline

download_history.py

↓

Yahoo Finance

↓

price_history.csv

↓

training_gbm.py

This separation reduces vendor lock-in and allows future migration to Polygon, Tiingo or other providers without modifying the training pipeline.

---

## GBM Audit Results

Audit confirmed:

Training rows:

69

Validation R²:

Approximately -0.99

Primary cause:

Insufficient historical data.

Feature engineering was reviewed and considered correct.

No evidence of feature loss beyond expected rolling-window warm-up periods.

---

## New Training Dataset

download_history.py now downloads approximately:

2513 trading days

Date range:

2016-07-05

↓

2026-07-02

The dataset is now sufficient for proper model evaluation.

---

## Future Model Metadata

The GBM model bundle should evolve to include:

- model
- prediction horizon
- feature names
- training start/end dates
- training row count
- MAE
- RMSE
- MAPE
- R²
- model version
- training timestamp

This metadata will improve reproducibility and simplify future model comparisons.

---

## Immediate Next Sprint

Priority order:

1. Retrain GBM using expanded dataset.

2. Compare:

- Dataset size
- MAE
- RMSE
- MAPE
- R²

against previous baseline.

3. Validate inference pipeline.

4. Improve model bundle metadata.

Only after establishing a strong baseline should feature engineering or model architecture be modified.



# SESSION UPDATE 2026-07-07

## Sprint 3.2

Infrastructure phase is largely complete.

Focus has shifted from pipeline construction to model quality.

### Current Model Status

Direction XGB:
~46-47% walk-forward accuracy

Delta XGB:
~47.6% directional accuracy

Return XGB:
~47.1% directional accuracy

None are currently deployable for trading decisions.

### Major Engineering Conclusion

Validation R² is not a reliable success metric.

Walk-forward directional accuracy is now the primary model evaluation metric.

### Current Bottleneck

Target engineering.

The existing labels are too noisy because they classify very small market moves.

Example:

future_close > current_close

This causes the model to learn noise instead of meaningful directional moves.

### Approved Next Direction

Build threshold-based directional labels.

Training file:

training/training_direction_threshold.py

Backtest file:

backtesting/walk_forward_direction_threshold.py

Target definition:

BUY:
future_return > +2%

SELL:
future_return < -2%

IGNORE:
-2% <= future_return <= +2%

### Current Roadmap

1. Threshold Direction Model
2. Walk-Forward Validation
3. PnL Backtesting
4. Transaction Cost Modeling
5. Equity Curve Analysis
6. Drawdown Analysis
7. Sharpe Ratio
8. Ensemble Improvement
9. Confidence Engine Improvement
10. Production Deployment

### Important Continuation Note

If resuming development in a future session:

DO NOT redesign the architecture.

DO NOT replace the existing feature pipeline.

Continue from Sprint 3.2 and begin by implementing:

- training/training_direction_threshold.py
- backtesting/walk_forward_direction_threshold.py

These are the next approved engineering tasks.

---

# SESSION UPDATE 2026-07-08

## Current Development Stage

DiMarket has moved beyond basic prediction pipeline construction.

The project is now in the trust, validation, explainability, and MLOps phase.

The guiding principle remains unchanged:

Build the most trustworthy AI forecasting platform that an individual investor can access.

## Current Production Candidate

The threshold-direction XGBoost classifier is the current primary production candidate.

It uses threshold labels:

BUY:
future_return > +2%

SELL:
future_return < -2%

IGNORE:
-2% <= future_return <= +2%

The model is evaluated using walk-forward validation and portfolio simulation rather than random train/test splits.

Current trusted results:
- Average walk-forward accuracy: 56.75%
- Average precision: 66.66%
- Average recall: 60.89%
- Average F1: 62.01%
- Top 10% signal win rate: 77.5%
- Top 20% signal win rate: 71.25%
- Best confidence threshold: 0.55
- Profit Factor: approximately 1.93
- Sharpe Ratio: approximately 3.87
- Sortino Ratio: approximately 9.15

Important:
The model's value is not pure accuracy. Its value is ranking, confidence filtering, explainability, and trade-selection quality.

## Calibration Decision

Raw model probabilities are not reliable enough by themselves.

Calibration testing showed:
- Raw ECE: approximately 0.211
- Platt Scaling ECE: approximately 0.051
- Isotonic ECE: approximately 0.086

Decision:
Use Platt Scaling as the default probability calibration method for the threshold-direction model.

DiMarket should never fake certainty. If confidence is weak or poorly calibrated, the product should say so.

## Explainability Decision

Explainability is now a core product requirement, not an optional feature.

New explainability package:
- explainability/models.py
- explainability/feature_dictionary.py
- explainability/narrative.py
- explainability/explanation.py
- explainability/reporting.py
- explainability/shap_engine.py

The current implementation uses native XGBoost feature contribution output instead of shap.TreeExplainer because it is more stable with the current XGBoost version.

Goal:
Every prediction should eventually answer:
- What is the prediction?
- What is the confidence?
- Which features supported the prediction?
- Which features opposed it?
- What is the human-readable explanation?
- Is the probability historically reliable?

## Experiment Tracking Decision

Experiment tracking is now part of the backend foundation.

New package:
- experiments/

Tracked fields include:
- run id
- timestamp
- model name
- dataset
- horizon
- threshold
- Git commit
- parameters
- metrics
- notes

Generated files:
- reports/experiments.jsonl
- reports/experiment_summary.csv

Purpose:
Do not rely on terminal logs. Every important training or backtest run should be reproducible and comparable.

## Model Registry Decision

A model registry has been introduced.

Registry file:
- models/registry.json

Current tasks:
- direction
- return_forecast

Task definitions:
- direction: primary directional trading signal
- return_forecast: supporting expected-return estimate

Important:
The direction task should be owned by the threshold-direction XGBoost classifier.
The return_forecast task can be owned by the GBM log-return regressor.

## GBM Return Forecast Decision

GBM was changed from predicting absolute future close price to predicting log return:

target = log(future_close / current_close)

This is the correct target for return forecasting.

However, current GBM return metrics are not production-worthy:
- R²: approximately -0.1676
- Directional Accuracy: approximately 49.23%
- Worse than zero-return naive baseline

Decision:
GBM return forecast remains a research/supporting model only.
Do not use it as the primary trading recommendation engine.

## Current Backend Architecture Direction

Primary decision flow:

Historical Data
↓
Feature Engineering
↓
Threshold-Direction XGBoost
↓
Probability Calibration
↓
Confidence Filter
↓
SHAP-style Explanation
↓
Portfolio/Decision Report
↓
API Response
↓
Frontend Prediction Card

Supporting flow:

Historical Data
↓
Feature Engineering
↓
GBM Return Forecast
↓
Expected Return Estimate
↓
Decision Context

## Immediate Next Approved Tasks

1. Register threshold-direction XGBoost as the production direction model.

2. Save direction model artifacts with versioned filenames:
   - xgb_direction_v001.pkl
   - xgb_direction_v002.pkl

3. Store direction model metadata:
   - horizon
   - threshold target
   - feature list
   - walk-forward metrics
   - calibration method
   - selected confidence threshold
   - Git commit

4. Add model lifecycle commands:
   - list model versions
   - inspect current production model
   - promote model version
   - rollback production model

5. Continue improving confidence and explainability before UI polish.

## Do Not Do

Do not redesign the architecture.

Do not replace the existing feature pipeline.

Do not make the GBM return regressor the main production signal unless it beats the naive baseline and the threshold-direction model.

Do not optimize for flashy predictions over trust.

Do not add unnecessary features outside the roadmap.

## Current North Star

DiMarket should become a trustworthy AI decision-support platform for individual investors.

The product should prefer:
- transparent uncertainty
- calibrated confidence
- explainable predictions
- reproducible model history
- validated trading behavior

over:
- inflated accuracy claims
- black-box predictions
- unvalidated model outputs
- marketing-driven certainty
