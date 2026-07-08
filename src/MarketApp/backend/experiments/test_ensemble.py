"""
Integration test for the Ensemble Decision Engine.

Purpose
-------
Verify that DiMarket can load production models from the Model Registry,
run both models on recent market data, and produce a unified decision.
"""

from __future__ import annotations

import argparse

import pandas as pd

from ensemble.decision_engine import EnsembleDecisionEngine


def load_price_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    df.columns = df.columns.str.lower()

    df["date"] = pd.to_datetime(
        df["date"]
    )

    numeric_cols = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    df[numeric_cols] = df[numeric_cols].apply(
        pd.to_numeric,
        errors="coerce",
    )

    return (
        df.sort_values("date")
        .reset_index(drop=True)
    )

def print_decision(decision) -> None:
    print("\n===================================")
    print("DIMARKET ENSEMBLE DECISION")
    print("===================================")

    print(f"Ticker                : {decision.ticker}")
    print(f"Direction Probability : {decision.direction_probability:.2%}")
    print(f"Expected Return       : {decision.expected_return:.2%}")
    print(f"Recommendation        : {decision.recommendation}")
    print(f"Confidence            : {decision.confidence}")

    print("\nReasons")
    print("-------")
    if decision.reasons:
        for reason in decision.reasons:
            print(f"- {reason}")
    else:
        print("- None")

    print("\nWarnings")
    print("--------")
    if decision.warnings:
        for warning in decision.warnings:
            print(f"- {warning}")
    else:
        print("- None")

    if decision.explanation:
        print("\nExplanation")
        print("-----------")
        print(
            decision.explanation.get(
                "summary",
                "No explanation available.",
            )
        )

        print("\nTop Positive Drivers")
        print("--------------------")
        for item in decision.explanation.get(
            "top_positive_features",
            [],
        ):
            print(
                f"- {item.get('display_name')}: "
                f"{item.get('direction')} "
                f"(impact: {item.get('impact'):.4f})"
            )

        print("\nTop Negative Drivers")
        print("--------------------")
        for item in decision.explanation.get(
            "top_negative_features",
            [],
        ):
            print(
                f"- {item.get('display_name')}: "
                f"{item.get('direction')} "
                f"(impact: {item.get('impact'):.4f})"
            )

    if decision.historical_confidence:
        history = decision.historical_confidence

        print("\nHistorical Confidence")
        print("---------------------")

        print(
            f"Model Version   : {history.get('model_version')}"
        )
        print(
            f"Calibration     : {history.get('calibration_method')}"
        )
        print(
            f"Validation Rows : {history.get('validation_rows')}"
        )

        accuracy = history.get("accuracy")
        precision = history.get("precision")
        recall = history.get("recall")
        f1 = history.get("f1")
        auc = history.get("auc")

        if accuracy is not None:
            print(
                f"Historical Accuracy : {accuracy:.2%}"
            )

        if precision is not None:
            print(
                f"Historical Precision: {precision:.2%}"
            )

        if recall is not None:
            print(
                f"Historical Recall   : {recall:.2%}"
            )

        if f1 is not None:
            print(
                f"Historical F1       : {f1:.2%}"
            )

        if auc is not None:
            print(
                f"Historical AUC      : {auc:.2%}"
            )

        print(
            "\nInterpretation"
        )
        print(
            "--------------"
        )
        print(
            f"When DiMarket reports approximately "
            f"{decision.direction_probability:.0%} confidence, "
            "these validation metrics describe how the production "
            "direction model has historically performed."
        )

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        default="data/price_history.csv",
    )

    parser.add_argument(
        "--ticker",
        default="AAPL",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    df = load_price_data(
        args.csv,
    )

    engine = EnsembleDecisionEngine()

    decision = engine.predict(
        ticker=args.ticker,
        price_df=df,
    )

print_decision(decision)
