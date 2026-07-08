import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf


def download_history(ticker: str, period: str = "10y") -> None:
    print(f"Downloading {ticker} ({period})...")

    df = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="column",
    )

    if df.empty:
        raise RuntimeError(f"No data returned for {ticker}")

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()

    # Normalize column names
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]

    # Keep only the columns used by the training pipeline
    required = ["date", "open", "high", "low", "close", "volume"]

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise RuntimeError(
            f"Missing expected columns: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    df = df[required]

    df = df.sort_values("date").reset_index(drop=True)

    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "price_history.csv"

    df.to_csv(output_file, index=False)

    print()
    print("Download complete.")
    print(f"Rows       : {len(df)}")
    print(f"From       : {df['date'].min().date()}")
    print(f"To         : {df['date'].max().date()}")
    print(f"Output CSV : {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--period", default="10y")

    args = parser.parse_args()

    download_history(
        ticker=args.ticker,
        period=args.period,
    )