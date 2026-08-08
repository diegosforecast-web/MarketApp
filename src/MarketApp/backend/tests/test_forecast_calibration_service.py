import json
from pathlib import Path

from services.forecast_calibration_service import (
    ForecastCalibrationService,
    ForecastIntervalCalibration,
)


def _artifact(
    path: Path,
    *,
    sample_count: int = 200,
    validation_sample_count: int = 120,
    model_task: str = "return_forecast_h5",
    model_version: str = "001",
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "calibrations": {
                    "h5:v001": {
                        "horizon": 5,
                        "model_task": model_task,
                        "model_version": model_version,
                        "model_file": "gbm_return_h5_v001.pkl",
                        "method": (
                            "fixed_production_model_post_training_"
                            "residual_quantiles"
                        ),
                        "provenance": "fixed production model evaluation",
                        "residual_definition": (
                            "actual_simple_return - predicted_simple_return"
                        ),
                        "reference_ticker": "AAPL",
                        "training_cutoff": "2024-01-01",
                        "evaluation_tickers": ["MSFT", "NVDA", "VOO"],
                        "lower_quantile": 0.10,
                        "upper_quantile": 0.90,
                        "lower_residual_return": -0.04,
                        "upper_residual_return": 0.06,
                        "sample_count": sample_count,
                        "validation_sample_count": validation_sample_count,
                        "calibration_start": "2024-01-01",
                        "calibration_end": "2025-06-30",
                        "validation_start": "2025-07-01",
                        "validation_end": "2025-12-31",
                        "generated_at": "2026-08-05T00:00:00+00:00",
                        "empirical_coverage": 0.81,
                        "average_interval_width": 0.10,
                        "median_interval_width": 0.10,
                        "calibration_diagnostics": {
                            "mae": 0.02,
                            "rmse": 0.03,
                            "mean_residual": 0.001,
                            "std_residual": 0.03,
                        },
                        "validation_diagnostics": {
                            "mae": 0.021,
                            "rmse": 0.031,
                            "mean_residual": 0.002,
                            "std_residual": 0.031,
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_loads_matching_horizon_and_model_version(tmp_path: Path) -> None:
    artifact = tmp_path / "forecast_intervals.json"
    _artifact(artifact)
    service = ForecastCalibrationService(artifact)

    calibration = service.get(
        horizon=5,
        model_task="return_forecast_h5",
        model_version="001",
    )

    assert calibration is not None
    assert calibration.sample_count == 200
    assert calibration.validation_sample_count == 120
    assert calibration.model_file == "gbm_return_h5_v001.pkl"
    assert calibration.evaluation_tickers == ("MSFT", "NVDA", "VOO")


def test_rejects_model_version_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "forecast_intervals.json"
    _artifact(artifact)
    service = ForecastCalibrationService(artifact)

    assert service.get(
        horizon=5,
        model_task="return_forecast_h5",
        model_version="002",
    ) is None


def test_rejects_model_task_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "forecast_intervals.json"
    _artifact(artifact, model_task="return_forecast_h3")
    service = ForecastCalibrationService(artifact)

    assert service.get(
        horizon=5,
        model_task="return_forecast_h5",
        model_version="001",
    ) is None


def test_rejects_insufficient_calibration_samples(tmp_path: Path) -> None:
    artifact = tmp_path / "forecast_intervals.json"
    _artifact(artifact, sample_count=20)
    service = ForecastCalibrationService(artifact, minimum_samples=100)

    assert service.get(
        horizon=5,
        model_task="return_forecast_h5",
        model_version="001",
    ) is None


def test_rejects_insufficient_validation_samples(tmp_path: Path) -> None:
    artifact = tmp_path / "forecast_intervals.json"
    _artifact(artifact, validation_sample_count=20)
    service = ForecastCalibrationService(
        artifact,
        minimum_validation_samples=100,
    )

    assert service.get(
        horizon=5,
        model_task="return_forecast_h5",
        model_version="001",
    ) is None


def test_builds_asymmetric_bounds_without_changing_expected() -> None:
    service = ForecastCalibrationService("missing.json")
    calibration = ForecastIntervalCalibration(
        horizon=5,
        model_task="return_forecast_h5",
        model_version="001",
        lower_quantile=0.10,
        upper_quantile=0.90,
        lower_residual_return=-0.04,
        upper_residual_return=0.06,
        sample_count=200,
        calibration_start="2024-01-01",
        calibration_end="2025-12-31",
        generated_at="2026-08-05T00:00:00+00:00",
        validation_sample_count=120,
    )

    assert service.build_price_bounds(
        current_price=100.0,
        expected_return=0.02,
        calibration=calibration,
    ) == (98.0, 108.0)
