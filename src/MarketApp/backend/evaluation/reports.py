from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def save_training_report(
    model_name: str,
    model_version: str,
    metrics: dict,
    metadata: dict,
    output_path: str,
):
    """
    Save a JSON report describing a trained model.

    Parameters
    ----------
    model_name : str
        Name of the model (GBM, LSTM, GRU...)

    model_version : str
        Version string.

    metrics : dict
        Output from calculate_metrics().

    metadata : dict
        Additional training metadata.

    output_path : str
        JSON file path.
    """

    report = {
        "model": model_name,
        "version": model_version,
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "metrics": metrics,
        "metadata": metadata,
    }

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=4,
        )

    print("\nTraining report saved:")
    print(output_path)


def load_training_report(
    report_path: str,
):
    """
    Load a previously saved training report.
    """

    report_path = Path(report_path)

    with open(
        report_path,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def print_training_report(
    report: dict,
):
    """
    Pretty-print a training report.
    """

    print("\n==============================")
    print("Training Report")
    print("==============================")

    print(f"Model   : {report['model']}")
    print(f"Version : {report['version']}")
    print(f"Trained : {report['trained_at']}")

    print("\nMetrics")

    for key, value in report["metrics"].items():

        if isinstance(value, float):

            print(f"{key:24} {value:.4f}")

        else:

            print(f"{key:24} {value}")

    print("\nMetadata")

    for key, value in report["metadata"].items():

        print(f"{key:24} {value}")