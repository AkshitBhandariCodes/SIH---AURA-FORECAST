# SIH26079 — Product Requirements Document (PRD)

## 1. Product Overview

### Product Name
**ForecastGuard AI**

### Problem Statement
**SIH26079 — AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts**

### Organization & Department
- **Ministry:** Ministry of Earth Sciences (MoES)
- **Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)

### Product Type
AI/ML software prototype featuring a reproducible data ingestion pipeline, synoptic physical feature engine, bust prediction models, explainability microservice, and an interactive operational forecast-confidence dashboard.

---

## 2. Problem Definition & Operational Context

Medium-range numerical weather predictions (NWP) frequently experience severe local forecast failures—termed **forecast busts**—during rapidly evolving weather systems (such as monsoon depressions, western disturbances, cyclones, active/break phases, and convective cloudbursts). 

Such failures erode forecaster trust and derail disaster preparedness. The system answers:
> **Which geographical regions and lead times (Day 1 to Day 10) is the operational NWP forecast likely to have high uncertainty or large error, why is the forecast failing, and how confident should decision-makers be?**

ForecastGuard AI serves as an **intelligent verification and reliability wrapper** on top of NWP models (NCUM, NEPS, IMD GFS, and surrogate reforecasts), NOT a replacement weather model.

---

## 3. Goals & Success Criteria

### Primary Goals
1. **Bust Probability Estimation:** Output calibrated probability $P(\text{Bust}) \in [0, 1]$ for each grid point and lead time (Day 1 to Day 10).
2. **Forecast Confidence Index (FCI):** Produce a standardized 0–100% confidence rating (High/Green, Moderate/Yellow, Low/Red) per district/subdivision.
3. **Error-Prone Area Detection:** Cluster high-risk cells ($P(\text{Bust}) > 0.60$) into discrete operational warning polygons (GeoJSON).
4. **Meteorological Explainability:** Provide natural-language explanations powered by TreeSHAP that point to actual atmospheric drivers (e.g., ensemble underdispersion, moisture flux convergence mismatch).
5. **NCMRWF Alignment:** Provide a two-tier architecture: 20-year open historical reforecasts (NOAA GEFS) for surrogate pre-training + operational GRIB2 adapters for NCUM/NEPS and IMD-GFS.
6. **Operational API & Dashboard:** Deliver high-performance REST APIs and an intuitive GIS dashboard with Day 1–10 scrub controls.

---

## 4. Multi-Criteria "Forecast Bust" Definition Matrix

To eliminate the "double-penalty" problem and distinguish between catastrophic misses and harmless discrepancies, ForecastGuard AI employs a **3-Dimensional Bust Definition Matrix**:

### 1. Categorical / Event-Based Busts (IMD Standards)
Using official IMD daily rainfall criteria:
- **Light:** $< 15.5\text{ mm/day}$
- **Moderate:** $15.6 - 64.4\text{ mm/day}$
- **Heavy:** $64.5 - 115.5\text{ mm/day}$
- **Very Heavy / Extreme:** $> 115.5\text{ mm/day}$

- **Type I Bust (Miss / False Negative — High Disaster Risk):**
  $$\text{Forecast} < 15.5\text{ mm (Light/Dry)} \quad\text{and}\quad \text{Observed} \ge 64.5\text{ mm (Heavy)}$$
- **Type II Bust (False Alarm — High Economic/Logistic Cost):**
  $$\text{Forecast} \ge 64.5\text{ mm (Heavy)} \quad\text{and}\quad \text{Observed} < 10.0\text{ mm (Dry)}$$

### 2. Normalized Intensity Bust (Percentile-Based)
To prevent arid regions (e.g., Rajasthan) from being judged with the same absolute error thresholds as high-precipitation zones (e.g., Meghalaya):
$$\text{Normalized Absolute Error (NAE)} = \frac{|\text{Forecast} - \text{Observed}|}{\sigma_{\text{clim}}(\text{region}, \text{month}) + \epsilon}$$
A cell is flagged as an intensity bust if $\text{NAE} \ge 90\text{th percentile}$ of the historical lead-time error distribution.

### 3. Spatial Displacement & Neighborhood Metric (Anti-Double Penalty)
Using a $3 \times 3$ grid cell ($0.75^\circ \times 0.75^\circ \approx 75\text{ km}$) neighborhood filter:
- If a forecasted storm is observed within the immediate neighborhood, it is classified as a **Displacement Error** rather than a Total Failure Bust.
- Incorporates Fractions Skill Score (FSS) at regional scales.

---

## 5. Physical & Meteorological Feature Engineering

Unlike black-box models, ForecastGuard AI extracts meteorologically grounded indicators of atmospheric instability and NWP failure:

### A. Ensemble Dynamics & Spread-Skill Deficit
1. **Ensemble Mean & Standard Deviation ($\sigma_{\text{ens}}$):** Spread across ensemble members.
2. **Spread-Skill Deficit:**
   $$\Delta_{\text{spread}} = \sigma_{\text{ens}} - \overline{\text{Historical Error}}(\text{Lead Day}, \text{Month})$$
   *Physical Meaning:* Unusually small spread in chaotic situations indicates **model overconfidence (underdispersion)**, a primary driver of busts.

### B. Synoptic Moisture & Instability
3. **Moisture Flux Convergence (MFC) at 850 hPa:**
   $$\text{MFC} = -\left( \frac{\partial (qu)}{\partial x} + \frac{\partial (qv)}{\partial y} \right)$$
   Identifies unrepresented deep convection and monsoonal moisture surge.
4. **Low-Level Jet (LLJ) Index & Wind Shear:**
   - 850 hPa wind speed across the Arabian Sea core ($10^\circ–15^\circ\text{N}, 60^\circ–70^\circ\text{E}$).
   - Vertical shear between 200 hPa and 850 hPa zonal winds ($u_{200} - u_{850}$).
5. **Monsoon Trough Gradient Anomaly:**
   - Mean Sea Level Pressure (MSLP) gradient between Peninsular India and Northern Plains.
6. **Upper-Tropospheric Baroclinicity:**
   - 500 hPa geopotential height anomalies indicating Western Disturbances or mid-latitude wave intrusions.

---

## 6. Two-Tier Data & Model Architecture

```text
               TIER 1: Pre-training & Training Corpus
          ┌───────────────────────────────────────────────┐
          │  NOAA GEFSv12 Reforecasts (2000-2019)        │
          │  - 0.25° Global, 00 UTC, 5 Ensemble Members   │
          │  - AWS S3 Open Data (Cropped to India BBox)   │
          └───────────────────────┬───────────────────────┘
                                  │
                                  ▼
               TIER 2: Operational Ingestion Adapter
          ┌───────────────────────────────────────────────┐
          │  NCMRWF NCUM / NEPS & IMD GFS GRIB2 Streams   │
          │  - Unified Variable Mapping Engine            │
          │  - Canonical Grid (0.25° Lat/Lon, India BBox) │
          └───────────────────────┬───────────────────────┘
                                  │
                                  ▼
                    Reference Ground Truth
          ┌───────────────────────────────────────────────┐
          │  ERA5 Reanalysis (Atmospheric Dynamics)       │
          │  IMD 0.25° Gridded Rainfall (Ground Truth)    │
          └───────────────────────┬───────────────────────┘
                                  │
                                  ▼
          ┌───────────────────────────────────────────────┐
          │  Error Computation & 3D Bust Labeling         │
          └───────────────────────┬───────────────────────┘
                                  │
                                  ▼
          ┌───────────────────────────────────────────────┐
          │  ML Model: LightGBM / XGBoost + Isotonic Calib│
          └───────────────────────┬───────────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
     ┌─────────────────────────┐     ┌─────────────────────────┐
     │  Bust Probability Map   │     │  Explainability Engine  │
     │  & Warning Polygons     │     │  TreeSHAP + NL Reasoner │
     └────────────┬────────────┘     └────────────┬────────────┘
                  └───────────────┬───────────────┘
                                  ▼
                     FastAPI Backend Service
                                  ▼
                  Interactive Operational Dashboard
```

---

## 7. Operational Outputs & Interfaces

### 1. Forecast Confidence Index (FCI)
$$\text{FCI} = 100 \times (1 - P(\text{Bust}))$$
- **Green (80% – 100%):** High Confidence — Reliable for operational decisions.
- **Yellow (50% – 79%):** Moderate Confidence — Elevated variance, monitor ensemble spreads.
- **Red (0% – 49%):** Low Confidence / Bust Alert — High likelihood of severe forecast failure.

### 2. Error-Prone Area Warning Polygons
- Automatic spatial clustering (DBSCAN / connected components) of adjacent grid cells where $P(\text{Bust}) \ge 0.60$.
- Exported as GeoJSON layers for direct ingestion into MoES/IMD GIS decision systems.

### 3. Natural Language Meteorological Reasoner
Translates numerical SHAP feature attributions into forecaster-actionable synoptic sentences:
> *"Bust probability is 82% over Coastal Saurashtra (Day 4). Primary factors: severe ensemble underdispersion (spread deficit +0.34), strong 850 hPa moisture convergence along the Arabian Sea branch without convective triggering, and a southward-displaced monsoon trough anomaly."*

---

## 8. Functional Specifications

- **FR-01 Modular Ingestion:** Connectors for GEFS S3, ERA5 CDS API, and IMD Pune NetCDF archives with spatial bounding box subsetting ($5^\circ\text{N}–40^\circ\text{N}, 60^\circ\text{E}–100^\circ\text{E}$).
- **FR-02 Regridding Engine:** Bilinear/conservative regridding to canonical $0.25^\circ \times 0.25^\circ$ coordinate space.
- **FR-03 Strict Chronological Split:**
  - Training: 2000–2014
  - Validation: 2015–2016
  - Testing / Case Studies: 2017–2019 (Pilot test: July 2019 Monsoon Depression)
  - **Zero spatial leakage across dates.**
- **FR-04 Calibration Layer:** Isotonic regression / Platt scaling to ensure predicted probabilities match real empirical bust frequencies.
- **FR-05 REST API:**
  - `GET /api/v1/forecast/dates`
  - `GET /api/v1/bust-risk?init_time=...&lead_day=...&bbox=...`
  - `GET /api/v1/polygons/warning-zones`
  - `GET /api/v1/explain?lat=...&lon=...&lead_day=...`

---

## 9. Pilot Experiment Focus: July 2019 Monsoon

Rather than downloading 20 years upfront, the initial validation and hackathon demo slice focuses on **July 2019**:
- Multiple intense monsoon low-pressure systems and depressions over Central India.
- High operational value and well-documented ground truth from IMD reports.
- Proves end-to-end functionality within feasible disk and bandwidth budgets.
