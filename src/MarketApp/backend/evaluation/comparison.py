from __future__ import annotations


def print_model_comparison(
    model_name: str,
    model_metrics: dict,
    baseline_name: str,
    baseline_metrics: dict,
):
    """
    Compare a trained model against a baseline model.

    Parameters
    ----------
    model_name : str
        Name of the trained model.

    model_metrics : dict
        Metrics returned by calculate_metrics().

    baseline_name : str
        Name of the baseline model.

    baseline_metrics : dict
        Metrics returned by calculate_metrics().
    """

    print("\n========================================")
    print("Model Comparison")
    print("========================================")

    print(f"Model    : {model_name}")
    print(f"Baseline : {baseline_name}")

    print("\nMetric Comparison")
    print("-" * 65)

    header = (
        f"{'Metric':<24}"
        f"{model_name:>14}"
        f"{baseline_name:>14}"
        f"{'Difference':>13}"
    )

    print(header)
    print("-" * 65)

    metric_names = [
        ("mae", "MAE"),
        ("rmse", "RMSE"),
        ("mape", "MAPE"),
        ("r2", "R²"),
        ("directional_accuracy", "Direction"),
        ("bias", "Bias"),
    ]

    for key, label in metric_names:

        model_value = model_metrics.get(key)
        baseline_value = baseline_metrics.get(key)

        if model_value is None or baseline_value is None:
            continue

        difference = model_value - baseline_value

        print(
            f"{label:<24}"
            f"{model_value:>14.4f}"
            f"{baseline_value:>14.4f}"
            f"{difference:>13.4f}"
        )

    print("\nInterpretation")

    if model_metrics["mae"] < baseline_metrics["mae"]:
        print("✓ Lower MAE than the baseline.")
    else:
        print("✗ Higher MAE than the baseline.")

    if model_metrics["rmse"] < baseline_metrics["rmse"]:
        print("✓ Lower RMSE than the baseline.")
    else:
        print("✗ Higher RMSE than the baseline.")

    if model_metrics["mape"] < baseline_metrics["mape"]:
        print("✓ Lower MAPE than the baseline.")
    else:
        print("✗ Higher MAPE than the baseline.")

    if (
        model_metrics["directional_accuracy"]
        > baseline_metrics["directional_accuracy"]
    ):
        print("✓ Better directional accuracy.")
    else:
        print("✗ Worse directional accuracy.")

    if model_metrics["r2"] > baseline_metrics["r2"]:
        print("✓ Better R².")
    else:
        print("✗ Worse R².")

    print("========================================")