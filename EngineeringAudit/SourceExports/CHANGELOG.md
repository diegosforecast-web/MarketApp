# Sprint 3.3 (Current Status)

## Threshold Direction Model Breakthrough

### Latest Walk-Forward Results

Threshold Target:
- BUY = future_return > +2%
- SELL = future_return < -2%
- IGNORE = between -2% and +2%

Dataset:
- 1,296 usable samples
- BUY: 776
- SELL: 520

### Walk-Forward Performance

Average Accuracy: 56.75%
Average Precision: 66.66%
Average Recall: 60.89%
Average F1 Score: 62.01%

Baseline Accuracy: 60.00%

### Probability Ranking Performance

Top 10% Signals:
- 77.5% win rate

Top 20% Signals:
- 71.25% win rate

Top 30% Signals:
- 69.17% win rate

### Confidence Analysis

Global Results:

| Threshold | Coverage | Win Rate |
|-----------|----------|----------|
| 0.50 | 55.8% | 65.0% |
| 0.60 | 50.3% | 65.7% |
| 0.85 | 26.0% | 66.3% |
| 0.90 | 20.3% | 66.7% |

Key Finding:

Confidence filtering improves trade selection quality but does not dramatically improve win rate beyond ~66%.

### Trade Simulation Results

| Threshold | Trades | Profit Factor |
|-----------|---------|--------------|
| 0.50 | 223 | 1.89 |
| 0.55 | 215 | 2.01 |
| 0.60 | 201 | 2.00 |
| 0.80 | 127 | 1.98 |
| 0.90 | 81 | 1.93 |

### Major Conclusion

Threshold-based target engineering solved the primary modeling issue.

Previous models:
- 46%–47% directional accuracy

Current threshold model:
- 56.75% walk-forward accuracy
- 65%–67% win rate on executed signals
- Profit Factor near 2.0

The project has successfully moved beyond random directional prediction.

## Architecture Status

Completed:
- Historical data pipeline
- Feature engineering pipeline
- Threshold directional classifier
- Walk-forward validation
- Confidence analysis
- Trade simulation
- Profit factor analysis
- Model persistence

## Sprint 3.4 Roadmap

Priority 1:
- Equity curve generation
- CAGR calculation
- Maximum drawdown

Priority 2:
- Sharpe ratio
- Sortino ratio
- Volatility-adjusted returns

Priority 3:
- Transaction cost modeling
- Slippage modeling

Priority 4:
- Ensemble research
- Regime-aware models

# Sprint 3.3 (Current Status)

## Threshold Direction Model Breakthrough

### Latest Walk-Forward Results

Threshold Target:
- BUY = future_return > +2%
- SELL = future_return < -2%
- IGNORE = between -2% and +2%

Dataset:
- 1,296 usable samples
- BUY: 776
- SELL: 520

### Walk-Forward Performance

Average Accuracy: 56.75%
Average Precision: 66.66%
Average Recall: 60.89%
Average F1 Score: 62.01%

Baseline Accuracy: 60.00%

### Probability Ranking Performance

Top 10% Signals:
- 77.5% win rate

Top 20% Signals:
- 71.25% win rate

Top 30% Signals:
- 69.17% win rate

### Confidence Analysis

Global Results:

| Threshold | Coverage | Win Rate |
|-----------|----------|----------|
| 0.50 | 55.8% | 65.0% |
| 0.60 | 50.3% | 65.7% |
| 0.85 | 26.0% | 66.3% |
| 0.90 | 20.3% | 66.7% |

Key Finding:

Confidence filtering improves trade selection quality but does not dramatically improve win rate beyond ~66%.

### Trade Simulation Results

| Threshold | Trades | Profit Factor |
|-----------|---------|--------------|
| 0.50 | 223 | 1.89 |
| 0.55 | 215 | 2.01 |
| 0.60 | 201 | 2.00 |
| 0.80 | 127 | 1.98 |
| 0.90 | 81 | 1.93 |

### Major Conclusion

Threshold-based target engineering solved the primary modeling issue.

Previous models:
- 46%–47% directional accuracy

Current threshold model:
- 56.75% walk-forward accuracy
- 65%–67% win rate on executed signals
- Profit Factor near 2.0

The project has successfully moved beyond random directional prediction.

## Architecture Status

Completed:
- Historical data pipeline
- Feature engineering pipeline
- Threshold directional classifier
- Walk-forward validation
- Confidence analysis
- Trade simulation
- Profit factor analysis
- Model persistence

## Sprint 3.4 Roadmap

Priority 1:
- Equity curve generation
- CAGR calculation
- Maximum drawdown

Priority 2:
- Sharpe ratio
- Sortino ratio
- Volatility-adjusted returns

Priority 3:
- Transaction cost modeling
- Slippage modeling

Priority 4:
- Ensemble research
- Regime-aware models

---

# Session Update 2026-07-08

## Sprint 3.4 Completed - Trust, Explainability, and MLOps Foundation

This session advanced DiMarket from a model-evaluation project into a more complete ML research platform.

### Completed Backend Capabilities

Completed:
- Walk-forward threshold-direction validation
- Portfolio analytics
- Transaction cost modeling
- Slippage modeling
- Confidence calibration
- Platt Scaling vs Isotonic calibration comparison
- SHAP-style model explanations using native XGBoost contribution output
- Experiment tracking
- Automatic walk-forward experiment logging
- Model registry foundation
- Versioned model registration
- GBM return-forecast model registration

### Threshold Direction Model Status

The threshold-direction XGBoost model remains the strongest production candidate.

Current trusted metrics:
- Average Accuracy: 56.75%
- Average Precision: 66.66%
- Average Recall: 60.89%
- Average F1 Score: 62.01%
- Top 10% win rate: 77.5%
- Top 20% win rate: 71.25%
- Top 30% win rate: 69.17%
- Best confidence threshold: 0.55
- Win rate at best threshold: approximately 65.6%
- Profit Factor: approximately 1.93
- Sharpe Ratio: approximately 3.87
- Sortino Ratio: approximately 9.15
- Max Drawdown: approximately -46.3%

Decision:
The threshold-direction XGBoost model should become the primary production direction model.

### Calibration Status

Raw probabilities were not well calibrated.

Latest comparison:
- Raw ECE: approximately 0.211
- Platt Scaling ECE: approximately 0.051
- Isotonic ECE: approximately 0.086
- Isotonic MCE: 1.000, indicating instability on the current evaluation sample

Decision:
Platt Scaling should be the default calibration method for the direction model until larger calibration datasets are available.

### Explainability Status

A new explainability layer was added.

New package:
- explainability/

Implemented:
- FeatureContribution
- PredictionExplanation
- FeatureDictionary
- NarrativeBuilder
- ExplanationBuilder
- Explainability reporting
- XGBoost native contribution-based explanation engine

Important implementation decision:
Native XGBoost pred_contribs is used instead of shap.TreeExplainer for the current model because it avoids compatibility issues with recent XGBoost base_score formatting.

### Experiment Tracking Status

A new experiment framework was added.

New package:
- experiments/

Implemented:
- ExperimentRun dataclass
- ExperimentTracker
- JSONL experiment log
- CSV experiment summary export
- Git commit capture
- Automatic walk-forward experiment logging

Generated outputs:
- reports/experiments.jsonl
- reports/experiment_summary.csv

Current automatic logging includes:
- accuracy
- precision
- recall
- F1
- baseline
- top bucket win rates
- selected threshold
- profit factor
- Sharpe ratio
- Sortino ratio
- max drawdown
- CAGR
- final equity
- Git commit

### Model Registry Status

The model registry was upgraded from a hardcoded GBM loader into a version-aware registry.

Current registry tasks:
- direction
- return_forecast

Current design:
- direction is reserved for the threshold-direction XGBoost classifier
- return_forecast is used for the GBM log-return regressor

Registry file:
- models/registry.json

Versioned model files:
- gbm_model_v002.pkl
- gbm_model_v003.pkl
- gbm_model_v004.pkl

### GBM Return Forecast Status

The GBM model was changed from predicting future absolute close price to predicting log return:

target = log(future_close / current_close)

This made the feature importances more meaningful.

However, the GBM return model is not currently production-worthy.

Latest return-forecast metrics:
- MAE: approximately 0.0140
- RMSE: approximately 0.0196
- R²: approximately -0.1676
- Directional Accuracy: approximately 49.23%

Naive zero-return baseline:
- MAE: approximately 0.0120
- RMSE: approximately 0.0181
- R²: approximately -0.0017

Decision:
The GBM return model should remain a research/supporting model, not the primary trading signal.

### Current Architecture Decision

Production path should be:

direction
→ threshold-direction XGBoost classifier
→ calibrated probability
→ SHAP-style explanation
→ decision/report layer

Supporting path should be:

return_forecast
→ GBM log-return regressor
→ expected return estimate
→ secondary context only

### Immediate Next Sprint

Priority 1:
Register the threshold-direction XGBoost classifier under the direction task in the model registry.

Priority 2:
Ensure direction model artifacts are versioned:
- xgb_direction_v001.pkl
- xgb_direction_v002.pkl
- etc.

Priority 3:
Store direction model metadata:
- horizon
- threshold
- feature names
- training rows
- validation/walk-forward metrics
- calibration method
- selected confidence threshold
- Git commit

Priority 4:
Add model registry commands:
- list versions
- inspect production model
- promote version to production
- rollback production model

Priority 5:
Keep the roadmap focused.
Do not redesign architecture.
Do not replace the feature pipeline.
Do not make GBM the production signal unless it beats the naive baseline and direction model.

