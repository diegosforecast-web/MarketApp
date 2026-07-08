"""
Walk-forward engine for the threshold direction model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

from xgboost import XGBClassifier

from backtesting.probability import (
    confidence_analysis,
    probability_deciles,
    top_bucket_win_rate,
)

from explainability.reporting import format_explanation_report
from explainability.shap_engine import ShapEngine


@dataclass(frozen=True)
class WalkForwardConfig:
    train_size: int = 800
    test_size: int = 100
    random_state: int = 42
    explain_top_prediction: bool = True


@dataclass
class WalkForwardResult:
    fold_metrics: pd.DataFrame
    all_probs: list[float]
    all_actuals: list[int]
    all_future_returns: list[float]
    all_future_dates: list


def run_walk_forward_engine(
    X: pd.DataFrame,
    y: pd.Series,
    feats: pd.DataFrame,
    config: WalkForwardConfig | None = None,
) -> WalkForwardResult:
    if config is None:
        config = WalkForwardConfig()

    start = config.train_size
    fold = 1
    metrics = []

    all_probs = []
    all_actuals = []
    all_future_returns = []
    all_future_dates = []

    while start + config.test_size <= len(X):
        train_end = start
        test_end = start + config.test_size

        X_train = X.iloc[:train_end]
        y_train = y.iloc[:train_end]

        X_test = X.iloc[train_end:test_end]
        y_test = y.iloc[train_end:test_end]

        future_returns_test = feats["future_return"].iloc[
            train_end:test_end
        ]

        future_dates_test = feats["date"].iloc[
            train_end:test_end
        ]

        positives = (y_train == 1).sum()
        negatives = (y_train == 0).sum()
        scale_pos_weight = negatives / positives

        model = XGBClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=config.random_state,
            eval_metric="logloss",
        )

        model.fit(X_train, y_train)

        probs = model.predict_proba(X_test)[:, 1]
        pred = (probs >= 0.50).astype(int)

        all_probs.extend(probs.tolist())
        all_actuals.extend(y_test.tolist())
        all_future_returns.extend(future_returns_test.tolist())
        all_future_dates.extend(future_dates_test.tolist())

        accuracy = accuracy_score(y_test, pred)
        precision = precision_score(y_test, pred, zero_division=0)
        recall = recall_score(y_test, pred, zero_division=0)
        f1 = f1_score(y_test, pred, zero_division=0)

        baseline = max(y_test.mean(), 1 - y_test.mean())

        top10 = top_bucket_win_rate(probs, y_test, 0.10)
        top20 = top_bucket_win_rate(probs, y_test, 0.20)
        top30 = top_bucket_win_rate(probs, y_test, 0.30)
        avg_prob = np.mean(probs)

        print(f"\nFold {fold}")
        print(f"Accuracy : {accuracy:.4f}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall   : {recall:.4f}")
        print(f"F1 Score : {f1:.4f}")
        print(f"Baseline : {baseline:.4f}")
        print(f"Avg Prob : {avg_prob:.4f}")
        print(f"Top10 Win Rate: {top10:.4f}")
        print(f"Top20 Win Rate: {top20:.4f}")
        print(f"Top30 Win Rate: {top30:.4f}")

        print("\nProbability Deciles")
        print(probability_deciles(probs, y_test))

        print("\nConfidence Analysis")
        print(confidence_analysis(probs, y_test))

        if config.explain_top_prediction:
            _print_top_prediction_explanation(
                model=model,
                X_test=X_test,
                probs=probs,
            )

        metrics.append(
            {
                "fold": fold,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "baseline": baseline,
                "top10": top10,
                "top20": top20,
                "top30": top30,
            }
        )

        fold += 1
        start += config.test_size

    return WalkForwardResult(
        fold_metrics=pd.DataFrame(metrics),
        all_probs=all_probs,
        all_actuals=all_actuals,
        all_future_returns=all_future_returns,
        all_future_dates=all_future_dates,
    )


def _print_top_prediction_explanation(
    model,
    X_test: pd.DataFrame,
    probs: np.ndarray,
) -> None:
    top_index = int(np.argmax(probs))
    top_probability = float(probs[top_index])
    top_row = X_test.iloc[[top_index]]

    prediction = "BUY" if top_probability >= 0.50 else "SELL"

    try:
        explanation = ShapEngine(model).explain_prediction(
            row=top_row,
            prediction=prediction,
            confidence=top_probability,
            top_n=5,
        )

        print(format_explanation_report(explanation))

    except Exception as exc:
        print("\nMODEL EXPLANATION")
        print("-----------------------------------")
        print(f"Explanation unavailable: {exc}")
