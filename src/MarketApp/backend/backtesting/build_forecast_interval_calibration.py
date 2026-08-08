from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from features.engineered_features import build_14_feature_frame
from services.model_registry import ModelRegistry
from training.training_gbm import load_price_data


@dataclass(frozen=True)
class ResidualObservation:
    ticker: str
    date: str
    actual_return: float
    predicted_return: float
    residual_return: float


def build_dataset_with_dates(
    df: pd.DataFrame,
    horizon: int,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Build the production-aligned return dataset while preserving dates."""
    feats = build_14_feature_frame(df).dropna().reset_index(drop=True)
    future_close = feats["close"].shift(-horizon)
    feats["target"] = np.log(future_close / feats["close"])
    feats = feats.dropna().reset_index(drop=True)

    dates = pd.to_datetime(feats["date"], utc=False)
    X = feats.drop(columns=["target", "date"])
    y = feats["target"]
    return X, y, dates


def production_training_cutoff(
    *,
    reference_csv: str,
    horizon: int,
    training_rows: int,
) -> pd.Timestamp:
    """Return the first date not used to fit the registered production model.

    The horizon-specific GBMs were trained chronologically.  Their registry
    records retain the exact training row count.  Rebuilding the same feature
    dataset against the reference training CSV therefore identifies the first
    post-training observation without retraining or inspecting future labels.
    """
    df = load_price_data(reference_csv)
    X, _, dates = build_dataset_with_dates(df, horizon)

    if training_rows <= 0 or training_rows >= len(X):
        raise ValueError(
            f"Invalid production training_rows={training_rows} for "
            f"horizon={horizon}; dataset rows={len(X)}."
        )
    return pd.Timestamp(dates.iloc[training_rows])


def load_production_bundle(
    *,
    registry: ModelRegistry,
    model_task: str,
) -> tuple[dict, dict]:
    model_info = registry.get_model_info(model_task)
    model_path = registry.models_dir / model_info["file"]
    bundle = joblib.load(model_path)

    if int(bundle.get("horizon", 0)) <= 0:
        raise ValueError(f"Production model bundle is missing a valid horizon: {model_path}")
    if "model" not in bundle:
        raise ValueError(f"Production model bundle has no model object: {model_path}")

    return model_info, bundle


def collect_production_model_residuals(
    *,
    csv_paths: list[Path],
    horizon: int,
    model_bundle: dict,
    training_cutoff: pd.Timestamp,
    excluded_tickers: set[str],
) -> list[ResidualObservation]:
    """Evaluate the fixed production model on post-training, unseen assets.

    No estimator is fitted here.  Each residual comes from the exact registered
    production model.  Samples are restricted to dates on/after the production
    training cutoff and tickers explicitly excluded from training provenance
    (AAPL by default) are omitted.
    """
    model = model_bundle["model"]
    feature_names = list(model_bundle.get("feature_names") or [])
    observations: list[ResidualObservation] = []

    for csv_path in sorted(csv_paths):
        ticker = csv_path.stem.upper()
        if ticker in excluded_tickers:
            continue

        df = load_price_data(str(csv_path))
        X, y_log_return, dates = build_dataset_with_dates(df, horizon)
        if X.empty:
            continue

        mask = dates >= training_cutoff
        X_eval = X.loc[mask].copy()
        y_eval = y_log_return.loc[mask]
        dates_eval = dates.loc[mask]
        if X_eval.empty:
            continue

        if feature_names:
            missing = [name for name in feature_names if name not in X_eval.columns]
            if missing:
                raise ValueError(
                    f"{csv_path} is missing production model features: {missing}"
                )
            X_eval = X_eval[feature_names]

        predicted_return = np.expm1(model.predict(X_eval))
        actual_return = np.expm1(y_eval.to_numpy())
        residuals = actual_return - predicted_return

        for date_value, actual, predicted, residual in zip(
            dates_eval,
            actual_return,
            predicted_return,
            residuals,
        ):
            observations.append(
                ResidualObservation(
                    ticker=ticker,
                    date=pd.Timestamp(date_value).date().isoformat(),
                    actual_return=float(actual),
                    predicted_return=float(predicted),
                    residual_return=float(residual),
                )
            )

    if not observations:
        raise ValueError(
            "No fixed-production-model residuals were produced from the "
            "post-training evaluation universe."
        )

    return observations


def split_calibration_validation(
    observations: list[ResidualObservation],
    calibration_fraction: float,
) -> tuple[list[ResidualObservation], list[ResidualObservation]]:
    """Chronologically split pooled observations into calibration/validation."""
    if not 0.50 <= calibration_fraction < 1.0:
        raise ValueError("calibration_fraction must satisfy 0.50 <= value < 1.0")

    ordered = sorted(observations, key=lambda item: (item.date, item.ticker))
    unique_dates = sorted({item.date for item in ordered})
    if len(unique_dates) < 2:
        raise ValueError("At least two evaluation dates are required.")

    split_index = int(len(unique_dates) * calibration_fraction)
    split_index = min(max(split_index, 1), len(unique_dates) - 1)
    validation_start = unique_dates[split_index]

    calibration = [item for item in ordered if item.date < validation_start]
    validation = [item for item in ordered if item.date >= validation_start]
    if not calibration or not validation:
        raise ValueError("Calibration/validation split produced an empty partition.")
    return calibration, validation


def _diagnostics(observations: list[ResidualObservation]) -> dict[str, float]:
    residuals = np.asarray(
        [item.residual_return for item in observations],
        dtype=float,
    )
    return {
        "mae": float(np.mean(np.abs(residuals))),
        "rmse": float(np.sqrt(np.mean(np.square(residuals)))),
        "mean_residual": float(np.mean(residuals)),
        "std_residual": float(np.std(residuals)),
    }


def build_calibration_record(
    *,
    calibration_observations: list[ResidualObservation],
    validation_observations: list[ResidualObservation],
    horizon: int,
    model_task: str,
    model_version: str,
    model_file: str,
    training_cutoff: str,
    reference_ticker: str,
    lower_quantile: float,
    upper_quantile: float,
) -> dict:
    calibration_residuals = np.asarray(
        [item.residual_return for item in calibration_observations],
        dtype=float,
    )
    validation_residuals = np.asarray(
        [item.residual_return for item in validation_observations],
        dtype=float,
    )

    lower = float(np.quantile(calibration_residuals, lower_quantile))
    upper = float(np.quantile(calibration_residuals, upper_quantile))
    validation_covered = (
        (validation_residuals >= lower)
        & (validation_residuals <= upper)
    )
    interval_width = upper - lower

    calibration_tickers = sorted(
        {item.ticker for item in calibration_observations}
    )
    validation_tickers = sorted(
        {item.ticker for item in validation_observations}
    )
    calibration_dates = [item.date for item in calibration_observations]
    validation_dates = [item.date for item in validation_observations]

    return {
        "horizon": int(horizon),
        "model_task": model_task,
        "model_version": str(model_version),
        "model_file": model_file,
        "method": "fixed_production_model_post_training_residual_quantiles",
        "provenance": (
            "Exact registered production model evaluated without retraining on "
            "post-training observations from evaluation tickers that exclude "
            "the reference training ticker. Quantiles are fit on an earlier "
            "chronological calibration partition and coverage is measured on "
            "a later independent validation partition."
        ),
        "residual_definition": (
            "actual_simple_return - predicted_simple_return"
        ),
        "reference_ticker": reference_ticker.upper(),
        "training_cutoff": training_cutoff,
        "evaluation_tickers": sorted(
            set(calibration_tickers) | set(validation_tickers)
        ),
        "lower_quantile": float(lower_quantile),
        "upper_quantile": float(upper_quantile),
        "lower_residual_return": lower,
        "upper_residual_return": upper,
        "sample_count": int(calibration_residuals.size),
        "validation_sample_count": int(validation_residuals.size),
        "calibration_start": min(calibration_dates),
        "calibration_end": max(calibration_dates),
        "validation_start": min(validation_dates),
        "validation_end": max(validation_dates),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "empirical_coverage": float(validation_covered.mean()),
        "average_interval_width": float(interval_width),
        "median_interval_width": float(interval_width),
        "calibration_diagnostics": _diagnostics(calibration_observations),
        "validation_diagnostics": _diagnostics(validation_observations),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reference-csv",
        default="data/price_history.csv",
        help="CSV used to reproduce the production model training cutoff.",
    )
    parser.add_argument(
        "--evaluation-glob",
        default="data/market_cache/*.csv",
        help="Glob for candidate out-of-sample evaluation assets.",
    )
    parser.add_argument(
        "--horizons",
        type=int,
        nargs="+",
        default=[1, 2, 3, 5, 15],
    )
    parser.add_argument(
        "--reference-ticker",
        default="AAPL",
        help="Ticker represented by the reference training CSV.",
    )
    parser.add_argument(
        "--exclude-ticker",
        action="append",
        default=[],
        help="Additional evaluation ticker to exclude. May be repeated.",
    )
    parser.add_argument("--calibration-fraction", type=float, default=0.70)
    parser.add_argument("--lower-quantile", type=float, default=0.10)
    parser.add_argument("--upper-quantile", type=float, default=0.90)
    parser.add_argument("--minimum-calibration-samples", type=int, default=100)
    parser.add_argument("--minimum-validation-samples", type=int, default=100)
    parser.add_argument(
        "--output",
        default="calibrations/forecast_intervals.json",
    )
    args = parser.parse_args()

    if not 0 <= args.lower_quantile < args.upper_quantile <= 1:
        raise ValueError("Quantiles must satisfy 0 <= lower < upper <= 1.")

    evaluation_paths = sorted(Path().glob(args.evaluation_glob))
    if not evaluation_paths:
        raise ValueError(
            f"No evaluation files matched: {args.evaluation_glob}"
        )

    excluded_tickers = {
        args.reference_ticker.upper(),
        *(ticker.upper() for ticker in args.exclude_ticker),
    }
    registry = ModelRegistry()
    artifact = {"schema_version": 1, "calibrations": {}}

    for horizon in args.horizons:
        model_task = registry.task_for_horizon("return_forecast", horizon)
        model_info, model_bundle = load_production_bundle(
            registry=registry,
            model_task=model_task,
        )
        bundle_horizon = int(model_bundle.get("horizon", 0))
        if bundle_horizon != int(horizon):
            raise ValueError(
                f"{model_task} bundle horizon={bundle_horizon}, expected {horizon}."
            )

        training_rows = int(model_bundle.get("training_rows", 0))
        cutoff = production_training_cutoff(
            reference_csv=args.reference_csv,
            horizon=horizon,
            training_rows=training_rows,
        )
        observations = collect_production_model_residuals(
            csv_paths=evaluation_paths,
            horizon=horizon,
            model_bundle=model_bundle,
            training_cutoff=cutoff,
            excluded_tickers=excluded_tickers,
        )
        calibration_rows, validation_rows = split_calibration_validation(
            observations,
            args.calibration_fraction,
        )

        if len(calibration_rows) < args.minimum_calibration_samples:
            raise ValueError(
                f"h{horizon} has only {len(calibration_rows)} calibration "
                f"samples; minimum is {args.minimum_calibration_samples}."
            )
        if len(validation_rows) < args.minimum_validation_samples:
            raise ValueError(
                f"h{horizon} has only {len(validation_rows)} validation "
                f"samples; minimum is {args.minimum_validation_samples}."
            )

        record = build_calibration_record(
            calibration_observations=calibration_rows,
            validation_observations=validation_rows,
            horizon=horizon,
            model_task=model_task,
            model_version=str(model_info["version"]),
            model_file=str(model_info["file"]),
            training_cutoff=cutoff.date().isoformat(),
            reference_ticker=args.reference_ticker,
            lower_quantile=args.lower_quantile,
            upper_quantile=args.upper_quantile,
        )
        key = f"h{horizon}:v{model_info['version']}"
        artifact["calibrations"][key] = record
        print(json.dumps({"key": key, **record}, indent=2))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {len(artifact['calibrations'])} calibrations to {output}")


if __name__ == "__main__":
    main()
