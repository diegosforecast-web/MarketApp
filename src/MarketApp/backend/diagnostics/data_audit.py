"""
DiMarket Dataset Audit

Usage:
    python -m diagnostics.data_audit

This script performs a health check on the historical OHLCV dataset
before feature engineering or model training.
"""

from pathlib import Path

import pandas as pd


DATA_PATH = Path("data") / "price_history.csv"


def print_header(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    print_header("DiMarket Dataset Audit")

    df = pd.read_csv(DATA_PATH)

    df.columns = df.columns.str.lower()

    if "date" not in df.columns:
        raise ValueError("Dataset must contain a 'date' column.")

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values("date").reset_index(drop=True)

    # -------------------------------------------------------------
    # Dataset Summary
    # -------------------------------------------------------------

    print("\nDataset Summary")
    print("-" * 40)

    print(f"Rows                : {len(df):,}")
    print(f"Columns             : {len(df.columns)}")

    # -------------------------------------------------------------
    # Date Information
    # -------------------------------------------------------------

    print("\nDate Range")
    print("-" * 40)

    print(f"Start Date          : {df['date'].min().date()}")
    print(f"End Date            : {df['date'].max().date()}")

    duplicate_dates = df["date"].duplicated().sum()

    print(f"Duplicate Dates     : {duplicate_dates}")

    # -------------------------------------------------------------
    # Missing Values
    # -------------------------------------------------------------

    print("\nMissing Values")
    print("-" * 40)

    missing = df.isna().sum()

    for column, count in missing.items():
        print(f"{column:<20} {count}")

    # -------------------------------------------------------------
    # Duplicate Rows
    # -------------------------------------------------------------

    print("\nDuplicate Rows")
    print("-" * 40)

    print(df.duplicated().sum())

    # -------------------------------------------------------------
    # Data Types
    # -------------------------------------------------------------

    print("\nData Types")
    print("-" * 40)

    print(df.dtypes)

    # -------------------------------------------------------------
    # Numeric Summary
    # -------------------------------------------------------------

    print("\nNumeric Summary")
    print("-" * 40)

    print(df.describe())

    # -------------------------------------------------------------
    # Price Validation
    # -------------------------------------------------------------

    print("\nPrice Validation")
    print("-" * 40)

    invalid_high = (df["high"] < df["low"]).sum()

    invalid_open = (
        (df["open"] < df["low"]) |
        (df["open"] > df["high"])
    ).sum()

    invalid_close = (
        (df["close"] < df["low"]) |
        (df["close"] > df["high"])
    ).sum()

    zero_volume = (df["volume"] <= 0).sum()

    print(f"High < Low          : {invalid_high}")
    print(f"Open outside range  : {invalid_open}")
    print(f"Close outside range : {invalid_close}")
    print(f"Zero Volume Days    : {zero_volume}")

    # -------------------------------------------------------------
    # Audit Result
    # -------------------------------------------------------------

    print_header("Audit Result")

    passed = (
        duplicate_dates == 0
        and missing.sum() == 0
        and invalid_high == 0
        and invalid_open == 0
        and invalid_close == 0
        and zero_volume == 0
    )

    if passed:
        print("✅ DATASET PASSED ALL CHECKS")
    else:
        print("❌ DATASET FAILED ONE OR MORE CHECKS")


if __name__ == "__main__":
    main()