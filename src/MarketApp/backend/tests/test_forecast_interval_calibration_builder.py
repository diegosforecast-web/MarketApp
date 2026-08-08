import numpy as np
import pandas as pd

from backtesting.build_forecast_interval_calibration import (
    ResidualObservation,
    build_calibration_record,
    split_calibration_validation,
)


def _observation(ticker: str, date: str, residual: float) -> ResidualObservation:
    return ResidualObservation(
        ticker=ticker,
        date=date,
        actual_return=0.02 + residual,
        predicted_return=0.02,
        residual_return=residual,
    )


def test_split_is_chronological_and_non_overlapping() -> None:
    observations = [
        _observation("MSFT", "2026-01-01", -0.02),
        _observation("VOO", "2026-01-01", 0.01),
        _observation("MSFT", "2026-01-02", -0.01),
        _observation("VOO", "2026-01-02", 0.02),
        _observation("MSFT", "2026-01-03", 0.00),
        _observation("VOO", "2026-01-03", 0.03),
        _observation("MSFT", "2026-01-04", 0.01),
        _observation("VOO", "2026-01-04", 0.04),
    ]

    calibration, validation = split_calibration_validation(
        observations,
        0.50,
    )

    assert max(item.date for item in calibration) < min(
        item.date for item in validation
    )
    assert {item.date for item in calibration} == {
        "2026-01-01",
        "2026-01-02",
    }
    assert {item.date for item in validation} == {
        "2026-01-03",
        "2026-01-04",
    }


def test_empirical_coverage_uses_later_validation_partition() -> None:
    calibration = [
        _observation("MSFT", f"2026-01-{day:02d}", residual)
        for day, residual in enumerate(
            np.linspace(-0.10, 0.10, 10),
            start=1,
        )
    ]
    validation = [
        _observation("VOO", "2026-02-01", -0.20),
        _observation("VOO", "2026-02-02", 0.00),
        _observation("VOO", "2026-02-03", 0.20),
    ]

    record = build_calibration_record(
        calibration_observations=calibration,
        validation_observations=validation,
        horizon=5,
        model_task="return_forecast_h5",
        model_version="001",
        model_file="gbm_return_h5_v001.pkl",
        training_cutoff="2025-01-01",
        reference_ticker="AAPL",
        lower_quantile=0.10,
        upper_quantile=0.90,
    )

    assert record["sample_count"] == 10
    assert record["validation_sample_count"] == 3
    assert record["empirical_coverage"] == 1 / 3
    assert record["method"] == (
        "fixed_production_model_post_training_residual_quantiles"
    )
    assert record["calibration_end"] < record["validation_start"]
