"""First look at a local REFIT CSV. Does not change data or run the model."""
import argparse
from pathlib import Path

import pandas as pd


def inspect_csv(path):
    # A DataFrame is pandas' table: rows are readings, columns are measurements.
    df = pd.read_csv(path)
    print("First five rows:")
    print(df.head().to_string(index=False))
    print("\nColumns:", df.columns.tolist())
    print("Rows in this file:", df.shape[0])
    print("\nMissing values per column (zero watts is NOT missing):")
    print(df.isna().sum().to_string())

    # Unix timestamps are seconds. Subtraction reveals the actual sample spacing.
    if "Unix" in df.columns:
        intervals = pd.to_numeric(df["Unix"], errors="raise").diff().dropna()
        if intervals.empty:
            print("\nInterval: unavailable (need two valid timestamps)")
        else:
            print(f"\nMedian interval: {intervals.median()} seconds")
            print(f"Interval range: {intervals.min()} to {intervals.max()} seconds")
            print("Non-increasing intervals:", int((intervals <= 0).sum()))
    print("\nThis describes this file only, not the full REFIT dataset.")
    print("Cleaned REFIT already fills some gaps; no NaNs does not prove no outages.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="Local CSV path (start with a small sample)")
    args = parser.parse_args()
    inspect_csv(args.csv)
