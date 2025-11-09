# Mobility-Energy-Emissions-in-Finland-2001-2024

---

## ⚙️ Setup & Run

### Create a virtual environment

**Windows (PowerShell)**

```
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
````

**macOS / Linux**
```
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2) Place data files

Add these StatsFin CSV exports to the `dataset/` folder:  
- Greenhouse_gas_emissions.csv  
- Electricity_consumption.csv  
- Reg_vehicles.csv  

Encodings handled internally: UTF-8 for emissions; Latin-1 for electricity and vehicles.  
Files have two preamble lines before headers.

### 3) Run the pipeline

**1) Parse and merge**
```
python src/preprocess.py --data-dir dataset --out-dir results
```

**2) Analytics (correlations, lag/rolling, OLS)**
```
python src/analysis.py --in-csv results/merged_finland_2001_2024.csv --out-dir results
```

**3) Plots**
```
python src/visualization.py --in-csv results/merged_finland_2001_2024.csv --out-dir results/figures
```
---

## What the Code Does (Succinct)

**src/preprocess.py** 
Filters road transportation emissions (kt CO₂e), selects total electricity consumption (GWh), extracts all automobiles (Mainland Finland first registrations), and merges by year (2001–2024).

**src/analysis.py**  
Computes z-scores and year-over-year deltas, Pearson correlations (levels and deltas), 5-year rolling correlations, ±3-year lag correlations, and runs OLS regressions:  
- emissions_ktco2e ~ electricity_gwh + vehicles_first_reg  
- d_emissions ~ d_electricity + d_vehicles

**src/visualization.py**  
Saves five figures: time series, two scatter plots with trendlines, rolling correlations, and lag correlations.

---

## Core Results (from Artifacts)

**1) Time series (normalized)**  
File: `results/figures/fig_timeseries_normalized.png`  
Emissions peak in the mid-2000s, then trend downward from the 2010s. Electricity and registrations fluctuate more.  
From ~2015 onward, emissions fall while electricity and registrations do not move in lockstep, showing decoupling.

**2) Emissions vs Electricity (scatter)**  
File: `results/figures/fig_scatter_emissions_vs_electricity.png`  
Moderate positive slope, substantial spread. In OLS (levels), electricity is not significant (p≈0.29).  
Interpretation: Total grid demand is a poor direct predictor of road transport emissions.

**3) Emissions vs Vehicle First Registrations (scatter)**  
File: `results/fig_scatter_emissions_vs_vehicles.png`  
Stronger positive association, steeper and tighter trendline. OLS (levels): vehicles significant (coef≈0.027, p=0.004).  
Interpretation: Vehicle activity dominates emission levels over 2001–2024.

**4) 5-year Rolling Correlations**  
File: `results/figures/fig_rolling_correlations.png`  
Emissions–Electricity: generally positive, dips around 2020–2022.  
Emissions–Vehicles: mostly high and positive; dip in late-2000s (crisis period), then high again post-2018–2020.  
Interpretation: Relationship structure changes over time; policy and technology shocks matter.

**5) Lag Correlations (±3y)**  
File: `results/figures/fig_lag_correlations.png`  
Peaks near lag=0 for both electricity (~0.6) and vehicles (~0.75); fairly symmetric.  
Interpretation: No strong lead–lag; series co-move within the same year.

**6) OLS Regression (levels and deltas)**  
File: `results/ols_summary.txt`  
Levels model: R²=0.584 (Adj R²=0.542). Vehicles significant (p=0.004); electricity not (p=0.288).  
Deltas model: R²=0.251 (Adj R²=0.172). ΔElectricity marginal (p≈0.073); ΔVehicles not significant.  
Interpretation: Activity (registrations) explains levels of emissions.  
Short-term changes in energy or registrations do not linearly drive year-over-year emissions, consistent with efficiency gains and EV uptake after 2015.

---

## Interpretation and Policy Takeaways

Decoupling is underway: emissions fall despite variability in electricity and vehicles, consistent with fleet efficiency, hybrid/EV adoption, and policy impacts.  
Electricity is not a direct driver: using total grid demand as an EV proxy is noisy; EV stock or charging data would improve inference.  
Data governance in Finland supports reproducible, transparent climate accountability.

---

## Limitations

- Vehicle metric = first registrations (activity proxy). Consider total vehicle stock, vehicle-kilometres, or fuel sales.  
- Electricity metric = total consumption, not transport-specific. Add EV charging load and grid CO₂ intensity.  
- Small sample size (2001–2024): complement p-values with structural break or Bayesian models.

---

## Extensions (Next Commits)

- Integrate EV registrations/stock and biofuel share; re-estimate models.  
- Include electricity mix CO₂ intensity to separate electrification from grid greening.  
- Add a Streamlit app for interactive exploration.  
- Add GitHub Actions to auto-run the pipeline and publish figures to GitHub Pages.

---

## Troubleshooting (Windows / Cursor)

Activate virtual environment:
..venv\Scripts\Activate.ps1

yaml
Copy code

Install dependencies:
python -m pip install -r requirements.txt

yaml
Copy code

If vehicle headers differ (e.g., “2001 number”), adjust the regex in `load_vehicles()` to match the header.

---

## Citation

Zareen Rahman (2025). *Mobility–Energy–Emissions in Finland (2001–2024):  
A Reproducible Analysis of Road-Transport Emissions.*

---

## License

MIT
