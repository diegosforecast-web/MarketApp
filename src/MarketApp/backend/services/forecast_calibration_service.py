from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


class ForecastCalibrationError(RuntimeError):
    """Raised when a calibration artifact is invalid or incompatible."""


@dataclass(frozen=True)
class ForecastIntervalCalibration:
    horizon: int
    model_task: str
    model_version: str
    lower_quantile: float
    upper_quantile: float
    lower_residual_return: float
    upper_residual_return: float
    sample_count: int
    calibration_start: str
    calibration_end: str
    generated_at: str
    method: str = "out_of_sample_return_residual_quantiles"
    model_file: str | None = None
    provenance: str | None = None
    residual_definition: str | None = None
    reference_ticker: str | None = None
    training_cutoff: str | None = None
    evaluation_tickers: tuple[str, ...] = ()
    validation_sample_count: int | None = None
    validation_start: str | None = None
    validation_end: str | None = None
    empirical_coverage: float | None = None
    average_interval_width: float | None = None
    median_interval_width: float | None = None
    calibration_diagnostics: dict[str, float] | None = None
    validation_diagnostics: dict[str, float] | None = None

    def metadata(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "model_task": self.model_task,
            "model_version": self.model_version,
            "model_file": self.model_file,
            "horizon": self.horizon,
            "lower_quantile": self.lower_quantile,
            "upper_quantile": self.upper_quantile,
            "intended_coverage": round(
                self.upper_quantile - self.lower_quantile,
                6,
            ),
            "sample_count": self.sample_count,
            "validation_sample_count": self.validation_sample_count,
            "calibration_start": self.calibration_start,
            "calibration_end": self.calibration_end,
            "validation_start": self.validation_start,
            "validation_end": self.validation_end,
            "generated_at": self.generated_at,
            "empirical_coverage": self.empirical_coverage,
            "average_interval_width": self.average_interval_width,
            "median_interval_width": self.median_interval_width,
            "residual_definition": self.residual_definition,
            "reference_ticker": self.reference_ticker,
            "training_cutoff": self.training_cutoff,
            "evaluation_tickers": list(self.evaluation_tickers),
            "provenance": self.provenance,
            "calibration_diagnostics": self.calibration_diagnostics,
            "validation_diagnostics": self.validation_diagnostics,
        }


class ForecastCalibrationService:
    """Load and apply horizon- and model-version-specific calibrations.

    The service fails closed. Missing, stale, malformed, under-sampled, or
    model-incompatible calibration data produces no interval instead of
    fabricated bounds.
    """

    DEFAULT_MINIMUM_SAMPLES = 100
    DEFAULT_MINIMUM_VALIDATION_SAMPLES = 100

    def __init__(
        self,
        artifact_path: str | Path | None = None,
        *,
        minimum_samples: int = DEFAULT_MINIMUM_SAMPLES,
        minimum_validation_samples: int = DEFAULT_MINIMUM_VALIDATION_SAMPLES,
    ) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.artifact_path = Path(
            artifact_path
            or base_dir / "calibrations" / "forecast_intervals.json"
        )
        self.minimum_samples = int(minimum_samples)
        self.minimum_validation_samples = int(minimum_validation_samples)
        self._artifact = self._load_artifact()

    def _load_artifact(self) -> dict[str, Any]:
        if not self.artifact_path.exists():
            return {"schema_version": 1, "calibrations": {}}

        try:
            payload = json.loads(
                self.artifact_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ForecastCalibrationError(
                f"Unable to load calibration artifact: {exc}"
            ) from exc

        if payload.get("schema_version") != 1:
            raise ForecastCalibrationError(
                "Unsupported forecast calibration schema version."
            )
        if not isinstance(payload.get("calibrations"), dict):
            raise ForecastCalibrationError(
                "Calibration artifact must contain a calibrations object."
            )
        return payload

    @staticmethod
    def _key(horizon: int, model_version: str) -> str:
        return f"h{int(horizon)}:v{str(model_version)}"

    @staticmethod
    def _optional_float_dict(value: Any) -> dict[str, float] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("Diagnostics must be an object.")
        return {str(key): float(raw) for key, raw in value.items()}

    def get(
        self,
        *,
        horizon: int,
        model_task: str,
        model_version: str,
    ) -> ForecastIntervalCalibration | None:
        raw = self._artifact["calibrations"].get(
            self._key(horizon, model_version)
        )
        if not isinstance(raw, dict):
            return None

        try:
            calibration = ForecastIntervalCalibration(
                horizon=int(raw["horizon"]),
                model_task=str(raw["model_task"]),
                model_version=str(raw["model_version"]),
                lower_quantile=float(raw["lower_quantile"]),
                upper_quantile=float(raw["upper_quantile"]),
                lower_residual_return=float(raw["lower_residual_return"]),
                upper_residual_return=float(raw["upper_residual_return"]),
                sample_count=int(raw["sample_count"]),
                calibration_start=str(raw["calibration_start"]),
                calibration_end=str(raw["calibration_end"]),
                generated_at=str(raw["generated_at"]),
                method=str(
                    raw.get(
                        "method",
                        "out_of_sample_return_residual_quantiles",
                    )
                ),
                model_file=(
                    str(raw["model_file"])
                    if raw.get("model_file") is not None
                    else None
                ),
                provenance=(
                    str(raw["provenance"])
                    if raw.get("provenance") is not None
                    else None
                ),
                residual_definition=(
                    str(raw["residual_definition"])
                    if raw.get("residual_definition") is not None
                    else None
                ),
                reference_ticker=(
                    str(raw["reference_ticker"])
                    if raw.get("reference_ticker") is not None
                    else None
                ),
                training_cutoff=(
                    str(raw["training_cutoff"])
                    if raw.get("training_cutoff") is not None
                    else None
                ),
                evaluation_tickers=tuple(
                    str(value)
                    for value in raw.get("evaluation_tickers", [])
                ),
                validation_sample_count=(
                    int(raw["validation_sample_count"])
                    if raw.get("validation_sample_count") is not None
                    else None
                ),
                validation_start=(
                    str(raw["validation_start"])
                    if raw.get("validation_start") is not None
                    else None
                ),
                validation_end=(
                    str(raw["validation_end"])
                    if raw.get("validation_end") is not None
                    else None
                ),
                empirical_coverage=(
                    float(raw["empirical_coverage"])
                    if raw.get("empirical_coverage") is not None
                    else None
                ),
                average_interval_width=(
                    float(raw["average_interval_width"])
                    if raw.get("average_interval_width") is not None
                    else None
                ),
                median_interval_width=(
                    float(raw["median_interval_width"])
                    if raw.get("median_interval_width") is not None
                    else None
                ),
                calibration_diagnostics=self._optional_float_dict(
                    raw.get("calibration_diagnostics")
                ),
                validation_diagnostics=self._optional_float_dict(
                    raw.get("validation_diagnostics")
                ),
            )
        except (KeyError, TypeError, ValueError):
            return None

        if calibration.horizon != int(horizon):
            return None
        if calibration.model_task != str(model_task):
            return None
        if calibration.model_version != str(model_version):
            return None
        if calibration.method != (
            "fixed_production_model_post_training_residual_quantiles"
        ):
            return None
        if calibration.sample_count < self.minimum_samples:
            return None
        if calibration.validation_sample_count is None:
            return None
        if (
            calibration.validation_sample_count
            < self.minimum_validation_samples
        ):
            return None
        if not 0 <= calibration.lower_quantile < calibration.upper_quantile <= 1:
            return None
        if calibration.lower_residual_return > calibration.upper_residual_return:
            return None
        if (
            calibration.empirical_coverage is not None
            and not 0 <= calibration.empirical_coverage <= 1
        ):
            return None

        try:
            datetime.fromisoformat(
                calibration.generated_at.replace("Z", "+00:00")
            )
        except ValueError:
            return None

        return calibration

    def build_price_bounds(
        self,
        *,
        current_price: float,
        expected_return: float,
        calibration: ForecastIntervalCalibration,
    ) -> tuple[float, float] | None:
        current = float(current_price)
        expected = float(expected_return)
        if current <= 0:
            return None

        lower_return = expected + calibration.lower_residual_return
        upper_return = expected + calibration.upper_residual_return
        lower_price = max(0.01, current * (1 + lower_return))
        expected_price = current * (1 + expected)
        upper_price = max(0.01, current * (1 + upper_return))

        if not lower_price <= expected_price <= upper_price:
            return None

        return round(lower_price, 2), round(upper_price, 2)
