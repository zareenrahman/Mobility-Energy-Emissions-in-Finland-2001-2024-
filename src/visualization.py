#!/usr/bin/env python3
"""
Plots: normalized time series, scatters (+trendlines), rolling corr, lag corr.
Why: Separate plotting to keep clean CLI and to allow headless render in CI.
"""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def zscore(s: pd.Series) -> pd.Series:
    # Why: compare unlike scales on one plot
    return (s - s.mean()) / s.std(ddof=0)


def lagged_corr(x: pd.Series, y: pd.Series, max_lag: int = 3) -> pd.DataFrame:
    rows = []
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            corr = x.shift(-lag).corr(y)
        else:
            corr = x.corr(y.shift(lag))
        rows.append({"lag": lag, "corr": corr})
    return pd.DataFrame(rows)


def savefig(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-csv", required=True, help="Path to merged_finland_2001_2024.csv")
    ap.add_argument("--out-dir", required=True, help="Output directory for figures")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    df = pd.read_csv(args.in_csv)

    for c in ["emissions_ktco2e", "electricity_gwh", "vehicles_first_reg"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Derived
    df["emissions_z"] = zscore(df["emissions_ktco2e"])
    df["electricity_z"] = zscore(df["electricity_gwh"])
    df["vehicles_z"] = zscore(df["vehicles_first_reg"])

    roll_elec = df["emissions_ktco2e"].rolling(5).corr(df["electricity_gwh"])
    roll_veh = df["emissions_ktco2e"].rolling(5).corr(df["vehicles_first_reg"])

    lagcorr_elec = lagged_corr(df["electricity_gwh"], df["emissions_ktco2e"], 3)
    lagcorr_veh = lagged_corr(df["vehicles_first_reg"], df["emissions_ktco2e"], 3)

    # 1) Normalized time series
    plt.figure(figsize=(10, 6))
    plt.plot(df["year"], df["emissions_z"], label="Emissions (z)")
    plt.plot(df["year"], df["electricity_z"], label="Electricity (z)")
    plt.plot(df["year"], df["vehicles_z"], label="Vehicles first regs (z)")
    plt.xlabel("Year")
    plt.ylabel("Z-score")
    plt.title("Finland 2001–2024: Normalized Metrics")
    plt.legend()
    savefig(os.path.join(args.out_dir, "fig_timeseries_normalized.png"))

    # 2) Scatter: emissions vs electricity
    plt.figure(figsize=(7, 6))
    plt.scatter(df["electricity_gwh"], df["emissions_ktco2e"], label="Data")
    mask = df[["electricity_gwh", "emissions_ktco2e"]].dropna()
    if len(mask) >= 2:
        p = np.polyfit(mask["electricity_gwh"], mask["emissions_ktco2e"], 1)  # why: quick visual slope
        xfit = np.linspace(mask["electricity_gwh"].min(), mask["electricity_gwh"].max(), 60)
        yfit = p[0] * xfit + p[1]
        plt.plot(xfit, yfit, label="Trend")
    plt.xlabel("Electricity consumption (GWh)")
    plt.ylabel("Road transport emissions (kt CO₂e)")
    plt.title("Emissions vs Electricity consumption")
    plt.legend()
    savefig(os.path.join(args.out_dir, "fig_scatter_emissions_vs_electricity.png"))

    # 3) Scatter: emissions vs vehicles
    plt.figure(figsize=(7, 6))
    plt.scatter(df["vehicles_first_reg"], df["emissions_ktco2e"], label="Data")
    mask = df[["vehicles_first_reg", "emissions_ktco2e"]].dropna()
    if len(mask) >= 2:
        p = np.polyfit(mask["vehicles_first_reg"], mask["emissions_ktco2e"], 1)
        xfit = np.linspace(mask["vehicles_first_reg"].min(), mask["vehicles_first_reg"].max(), 60)
        yfit = p[0] * xfit + p[1]
        plt.plot(xfit, yfit, label="Trend")
    plt.xlabel("Vehicle first registrations")
    plt.ylabel("Road transport emissions (kt CO₂e)")
    plt.title("Emissions vs Vehicle first registrations")
    plt.legend()
    savefig(os.path.join(args.out_dir, "fig_scatter_emissions_vs_vehicles.png"))

    # 4) Rolling correlations
    plt.figure(figsize=(10, 6))
    plt.plot(df["year"], roll_elec, label="Rolling corr: Emissions vs Electricity (5y)")
    plt.plot(df["year"], roll_veh, label="Rolling corr: Emissions vs Vehicles (5y)")
    plt.axhline(0, linewidth=1)
    plt.xlabel("Year")
    plt.ylabel("Pearson r")
    plt.title("5-year Rolling Correlations")
    plt.legend()
    savefig(os.path.join(args.out_dir, "fig_rolling_correlations.png"))

    # 5) Lag correlations
    plt.figure(figsize=(10, 6))
    plt.stem(lagcorr_elec["lag"], lagcorr_elec["corr"], linefmt='-', markerfmt='o', basefmt=' ')
    plt.stem(lagcorr_veh["lag"], lagcorr_veh["corr"], linefmt='--', markerfmt='D', basefmt=' ')
    plt.xlabel("Lag (years). Positive = X lags emissions")
    plt.ylabel("Pearson r")
    plt.title("Lag Correlations (±3y): Electricity & Vehicles vs Emissions")
    savefig(os.path.join(args.out_dir, "fig_lag_correlations.png"))

    print("✅ Figures saved to:", args.out_dir)


if __name__ == "__main__":
    main()