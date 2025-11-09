# src/preprocess.py
#!/usr/bin/env python
"""
Preprocess StatsFin-style CSVs into a merged Finland 2001–2024 dataset.
Reads from --data-dir (your `dataset/`) and writes to --out-dir (e.g., `results/`).
"""

import argparse
import os
import re
from typing import Dict

import pandas as pd

YEARS = list(range(2001, 2025))


def _read_statsfin_csv(path: str, skiprows: int, encoding: str) -> pd.DataFrame:
    """Thin wrapper so we can standardize how we read StatsFin CSV exports."""
    return pd.read_csv(path, skiprows=skiprows, encoding=encoding)


def load_emissions(data_dir: str) -> pd.DataFrame:
    """
    Reads Greenhouse_gas_emissions.csv (UTF-8); filters road transportation; returns year + emissions_ktco2e.
    """
    fp = os.path.join(data_dir, "Greenhouse_gas_emissions.csv")
    if not os.path.exists(fp):
        raise FileNotFoundError(f"Missing file: {fp}")

    df = _read_statsfin_csv(fp, skiprows=2, encoding="utf-8")
    df.columns = [re.sub(r"\s+", " ", c).strip().lower() for c in df.columns]

    # Expect: 'year', 'emission category', 'greenhouse gas',
    # 'emission, thousand tonnes of co2 eq. (gwp=ar5)'
    if "emission category" not in df.columns:
        raise ValueError("Unexpected schema for emissions file: no 'emission category' column.")

    df = df[df["emission category"].astype(str).str.contains(r"\broad\b", case=False, na=False)].copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    val_col = next((c for c in df.columns if c.startswith("emission,")), None)
    if not val_col:
        raise ValueError("Cannot find emissions numeric column (starts with 'emission,').")

    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    out = (
        df.groupby("year", as_index=False)[val_col]
        .sum()
        .rename(columns={val_col: "emissions_ktco2e"})
    )
    out = out[out["year"].isin(YEARS)]
    return out


def load_electricity(data_dir: str) -> pd.DataFrame:
    """
    Reads Electricity_consumption.csv (latin-1); picks 'total' sector if present; returns year + electricity_gwh.
    """
    fp = os.path.join(data_dir, "Electricity_consumption.csv")
    if not os.path.exists(fp):
        raise FileNotFoundError(f"Missing file: {fp}")

    df = _read_statsfin_csv(fp, skiprows=2, encoding="latin-1")
    df.columns = [re.sub(r"\s+", " ", c).strip().lower() for c in df.columns]

    if "electricity consumption sector" not in df.columns:
        raise ValueError("Unexpected schema for electricity file: no 'electricity consumption sector' column.")

    if df["electricity consumption sector"].astype(str).str.contains(r"\btotal\b", case=False, na=False).any():
        df = df[df["electricity consumption sector"].astype(str).str.contains(r"\btotal\b", case=False, na=False)].copy()

    qty_col = next((c for c in df.columns if "quantity" in c), None)
    if not qty_col:
        raise ValueError("Cannot find electricity quantity column (contains 'quantity').")

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce")

    out = (
        df.groupby("year", as_index=False)[qty_col]
        .sum()
        .rename(columns={qty_col: "electricity_gwh"})
    )
    out = out[out["year"].isin(YEARS)]
    return out


def load_vehicles(data_dir: str) -> pd.DataFrame:
    """
    Reads Reg_vehicles.csv (latin-1); extracts 'All automobiles' + 'MAINLAND FINLAND';
    returns year + vehicles_first_reg (first registrations).
    """
    fp = os.path.join(data_dir, "Reg_vehicles.csv")
    if not os.path.exists(fp):
        raise FileNotFoundError(f"Missing file: {fp}")

    df = _read_statsfin_csv(fp, skiprows=2, encoding="latin-1")

    # Columns like: "Vehicle class","Region","2001 Number","2002 Number",..., "2025 Number"
    if "Vehicle class" not in df.columns or "Region" not in df.columns:
        raise ValueError("Unexpected schema for vehicles file: no 'Vehicle class' and/or 'Region'.")

    pick = df[
        df["Vehicle class"].astype(str).str.contains(r"All automobiles", case=False, na=False)
        & df["Region"].astype(str).str.contains(r"MAINLAND FINLAND", case=False, na=False)
    ].copy()

    if pick.empty:
        raise ValueError("Could not find 'All automobiles' & 'MAINLAND FINLAND' in vehicles file.")

    # Map "YYYY Number" columns to year ints
    year_map: Dict[str, int] = {}
    for c in pick.columns:
        m = re.match(r"^\s*(20\d{2})\s+Number\s*$", str(c))
        if m:
            year_map[c] = int(m.group(1))

    if not year_map:
        raise ValueError(
            "No 'YYYY Number' columns detected in vehicles file. "
            "Confirm column headers follow the '2001 Number' pattern."
        )

    rows = []
    for col, yr in year_map.items():
        if yr in YEARS:
            val = pd.to_numeric(pick[col], errors="coerce").iloc[0]
            rows.append({"year": yr, "vehicles_first_reg": val})

    out = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True, help="Input folder with dataset CSVs (e.g., dataset)")
    ap.add_argument("--out-dir", required=True, help="Output folder for results (e.g., results)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    emissions = load_emissions(args.data_dir)
    electricity = load_electricity(args.data_dir)
    vehicles = load_vehicles(args.data_dir)

    # Write intermediates for transparency
    emissions.to_csv(os.path.join(args.out_dir, "emissions_ktco2e.csv"), index=False)
    electricity.to_csv(os.path.join(args.out_dir, "electricity_gwh.csv"), index=False)
    vehicles.to_csv(os.path.join(args.out_dir, "vehicles_first_reg.csv"), index=False)

    merged = emissions.merge(electricity, on="year", how="outer").merge(vehicles, on="year", how="outer")
    merged = merged[(merged["year"] >= YEARS[0]) & (merged["year"] <= YEARS[-1])].sort_values("year")
    merged.to_csv(os.path.join(args.out_dir, "merged_finland_2001_2024.csv"), index=False)

    print("Preprocess done.")
    print(f"- {os.path.join(args.out_dir, 'emissions_ktco2e.csv')}")
    print(f"- {os.path.join(args.out_dir, 'electricity_gwh.csv')}")
    print(f"- {os.path.join(args.out_dir, 'vehicles_first_reg.csv')}")
    print(f"- {os.path.join(args.out_dir, 'merged_finland_2001_2024.csv')}")


if __name__ == "__main__":
    main()