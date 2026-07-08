"""
===============================================================================
DiMarket
Module: pipeline.py

Description:
    Central evaluation pipeline used by all forecasting models.

    Responsibilities:
        - Calculate metrics
        - Evaluate persistence benchmark
        - Print comparison
        - Save JSON report

Author: Diego
===============================================================================
"""

# =============================================================================
# Imports
# =============================================================================

from evaluation.metrics import calculate_metrics
from evaluation.benchmark import evaluate_persistence
from evaluation.comparison import print_model_comparison
from evaluation.reports import save_training_report


# =============================================================================
# Public Functions
# =============================================================================

def evaluate_model(
    *,
    model_name: str,
    version: str,
    predictions,
    actual,
    current_close,
    metadata: dict,
    report_path,
):
    """
    Complete evaluation pipeline for a forecasting model.
    """

    # -------------------------------------------------------------------------
    # Model metrics
    # -------------------------------------------------------------------------

    metrics = calculate_metrics(
        actual=actual,
        predicted=predictions,
        current_close=current_close,
    )

    # -------------------------------------------------------------------------
    # Persistence benchmark
    # -------------------------------------------------------------------------

    benchmark = evaluate_persistence(
        actual=actual,
        current_close=current_close,
    )

    # -------------------------------------------------------------------------
    # Console comparison
    # -------------------------------------------------------------------------

    print_model_comparison(
        model_name=model_name,
        model_metrics=metrics,
        baseline_name=benchmark["model"],
        baseline_metrics=benchmark["metrics"],
    )

    # -------------------------------------------------------------------------
    # Save report
    # -------------------------------------------------------------------------

    save_training_report(
        model_name=model_name,
        version=version,
        metrics=metrics,
        metadata=metadata,
        report_path=report_path,
    )

    return {
        "metrics": metrics,
        "benchmark": benchmark,
    }