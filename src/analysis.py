#!/usr/bin/env python3
# File: analysis.py
"""
Core analytics for Finland mobility-energy-emissions (2001–2024).

Outputs:
- correlations_summary.csv
- merged_with_derivatives.csv
- lagcorr_electricity.csv
- lagcorr_vehicles.csv
- ols_summary.txt

Why comments: Only to flag decisions users may need to revisit.
"""

import argparse
import os
from typing import List

import numpy as np
import pandas as pd
import statsmodels.api as sm


def zscore(s: pd.Series) -> pd.Series:
    """Population z-score; ddof=0 to normalize shape-dependent std."""
    return (s - s.mean()) / s.std(ddof=0)


def yoy(s: pd.Series) -> pd.Series:
    """Year-over-year deltas."""
    return s.diff()


def lagged_corr(x: pd.Series, y: pd.Series, max_lag: int = 3) -> pd.DataFrame:
    """Symmetric lag correlation; positive lag = X lags Y."""
    rows = []
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            corr = x.shift(-lag).corr(y)
        else:
            corr = x.corr(y.shift(lag))
        rows.append({"lag": lag, "corr": corr})
    return pd.DataFrame(rows)


def fit_ols(df: pd.DataFrame, y: str, xcols: List[str]) -> sm.regression.linear_model.RegressionResultsWrapper:
    """Plain OLS with constant; drops NA rows only for relevant columns."""
    frame = df.dropna(subset=[y] + xcols).copy()
    if frame.empty:
        raise ValueError("No rows available for OLS after dropping NA.")
    X = sm.add_constant(frame[xcols], has_constant="add")
    return sm.OLS(frame[y], X).fit()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run core analytics on merged dataset.")
    ap.add_argument("--in-csv", required=True, help="Path to merged_finland_2001_2024.csv")
    ap.add_argument("--out-dir", required=True, help="Output folder for analytics artifacts")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    if not os.path.isfile(args.in_csv):
        raise FileNotFoundError(f"Input CSV not found: {args.in_csv}")
    os.makedirs(args.out_dir, exist_ok=True)

    df = pd.read_csv(args.in_csv)
    required_cols = ["year", "emissions_ktco2e", "electricity_gwh", "vehicles_first_reg"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in input CSV: {missing}")

    for c in ["emissions_ktco2e", "electricity_gwh", "vehicles_first_reg"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Derived metrics
    df["emissions_z"] = zscore(df["emissions_ktco2e"])
    df["electricity_z"] = zscore(df["electricity_gwh"])
    df["vehicles_z"] = zscore(df["vehicles_first_reg"])

    df["d_emissions"] = yoy(df["emissions_ktco2e"])
    df["d_electricity"] = yoy(df["electricity_gwh"])
    df["d_vehicles"] = yoy(df["vehicles_first_reg"])

    # Correlations
    corr_levels = (
        df[["emissions_ktco2e", "electricity_gwh", "vehicles_first_reg"]]
        .corr()
        .loc["emissions_ktco2e", ["electricity_gwh", "vehicles_first_reg"]]
    )
    corr_deltas = (
        df[["d_emissions", "d_electricity", "d_vehicles"]]
        .corr()
        .loc["d_emissions", ["d_electricity", "d_vehicles"]]
    )

    corr_summary = pd.DataFrame(
        {
            "metric": ["levels_electricity", "levels_vehicles", "deltas_electricity", "deltas_vehicles"],
            "pearson_r": [
                float(corr_levels["electricity_gwh"]),
                float(corr_levels["vehicles_first_reg"]),
                float(corr_deltas["d_electricity"]),
                float(corr_deltas["d_vehicles"]),
            ],
        }
    ).round(3)
    corr_summary.to_csv(os.path.join(args.out_dir, "correlations_summary.csv"), index=False)

    # Rolling corr (5y) + lag corr (±3) helpers
    df["roll_corr_elec"] = df["emissions_ktco2e"].rolling(5).corr(df["electricity_gwh"])
    df["roll_corr_veh"] = df["emissions_ktco2e"].rolling(5).corr(df["vehicles_first_reg"])
    df.to_csv(os.path.join(args.out_dir, "merged_with_derivatives.csv"), index=False)

    lagcorr_elec = lagged_corr(df["electricity_gwh"], df["emissions_ktco2e"], 3)
    lagcorr_veh = lagged_corr(df["vehicles_first_reg"], df["emissions_ktco2e"], 3)
    lagcorr_elec.to_csv(os.path.join(args.out_dir, "lagcorr_electricity.csv"), index=False)
    lagcorr_veh.to_csv(os.path.join(args.out_dir, "lagcorr_vehicles.csv"), index=False)

    # OLS (levels) & (deltas)
    ols_levels = fit_ols(df, "emissions_ktco2e", ["electricity_gwh", "vehicles_first_reg"])
    ols_deltas = fit_ols(df, "d_emissions", ["d_electricity", "d_vehicles"])

    with open(os.path.join(args.out_dir, "ols_summary.txt"), "w", encoding="utf-8") as f:
        f.write("=== OLS (levels): emissions_ktco2e ~ electricity_gwh + vehicles_first_reg ===\n")
        f.write(str(ols_levels.summary()))
        f.write("\n\n=== OLS (deltas): d_emissions ~ d_electricity + d_vehicles ===\n")
        f.write(str(ols_deltas.summary()))

    print("✅ Analysis done.")
    print(f"- {os.path.join(args.out_dir, 'correlations_summary.csv')}")
    print(f"- {os.path.join(args.out_dir, 'merged_with_derivatives.csv')}")
    print(f"- {os.path.join(args.out_dir, 'lagcorr_electricity.csv')}")
    print(f"- {os.path.join(args.out_dir, 'lagcorr_vehicles.csv')}")
    print(f"- {os.path.join(args.out_dir, 'ols_summary.txt')}")


if __name__ == "__main__":
    main()