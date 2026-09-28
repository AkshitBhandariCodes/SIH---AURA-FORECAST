"""ForecastGuard AI — REST API Service (FastAPI) (SIH26079)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import numpy as np
import pandas as pd

from src.explainability.reasoner import MeteorologicalReasoner
from src.features.synoptic import build_feature_vector
from src.models.pipeline import ForecastBustClassifier, FEATURE_COLS
from src.preprocessing.grid import IMD_SUBDIVISIONS, Subdivision


app = FastAPI(
    title="ForecastGuard AI API",
    description="Operational Forecast Bust Detection & Confidence Intelligence for MoES / NCMRWF",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path("data/processed")
MODEL_PATH = DATA_DIR / "model.joblib"
PARQUET_PATH = DATA_DIR / "pilot_samples.parquet"

# Global state for loaded model and data
classifier = ForecastBustClassifier()
reasoner: Optional[MeteorologicalReasoner] = None
pilot_df: Optional[pd.DataFrame] = None
real_days: Dict[int, pd.DataFrame] = {}


def _real_row(sub_id: str, date: str, lead_day: int) -> Optional[Dict[str, Any]]:
    """Real GEFS+ERA5 row for init 2019-07-15 + lead day on disk, else None."""
    df = real_days.get(lead_day)
    if df is None or date != "2019-07-15":
        return None
    try:
        return df.loc[sub_id].to_dict()
    except KeyError:
        return None


@app.on_event("startup")
def load_artifacts():
    global reasoner, pilot_df
    if MODEL_PATH.exists():
        try:
            classifier.load(MODEL_PATH)
            reasoner = MeteorologicalReasoner(classifier.model)
            print(f"[API] Loaded trained model from {MODEL_PATH}")
        except Exception as e:
            print(f"[API Warning] Could not load model: {e}")

    if PARQUET_PATH.exists():
        try:
            pilot_df = pd.read_parquet(PARQUET_PATH)
            print(f"[API] Loaded pilot dataset with {len(pilot_df)} samples.")
        except Exception as e:
            print(f"[API Warning] Could not load parquet: {e}")

    for _n in range(1, 11):
        _p = DATA_DIR / f"real_pilot_day{_n}.parquet"
        if _p.exists():
            try:
                real_days[_n] = pd.read_parquet(_p).set_index("subdivision")
                print(f"[API] Loaded REAL Day-{_n} rows for {len(real_days[_n])} subdivisions.")
            except Exception as e:
                print(f"[API Warning] Could not load real Day-{_n}: {e}")


# Serve the React build's static assets (dashboard/assets/*) if present.
_dashboard_assets = Path("dashboard/assets")
if _dashboard_assets.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_dashboard_assets)), name="assets")


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    dashboard_file = Path("dashboard/index.html")
    if dashboard_file.exists():
        return HTMLResponse(content=dashboard_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>ForecastGuard AI API Running. Dashboard file not found.</h1>")


@app.get("/api/v1/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "ForecastGuard AI",
        "model_loaded": classifier.model is not None,
        "pilot_data_loaded": pilot_df is not None,
        "supported_subdivisions": len(IMD_SUBDIVISIONS),
    }


@app.get("/api/v1/forecast/dates")
def get_available_dates() -> Dict[str, List[str]]:
    return {
        "dates": [
            "2019-07-15",
            "2019-07-16",
            "2019-07-17",
            "2019-07-18",
            "2019-07-19",
            "2019-07-20",
        ]
    }


@app.get("/api/v1/confidence-map")
def get_confidence_map(
    date: str = Query("2019-07-15", description="Forecast initialization date (YYYY-MM-DD)"),
    lead_day: int = Query(4, ge=1, le=10, description="Forecast lead time (Day 1 to 10)"),
) -> Dict[str, Any]:
    """Return region-wise Forecast Confidence Index (FCI) and bust probabilities."""
    results = []

    for sub_id, subdiv in IMD_SUBDIVISIONS.items():
        # Real GEFS+ERA5 Day-1 row takes precedence over synthetic pilot rows.
        _rr = _real_row(sub_id, date, lead_day)
        sample_row = dict(_rr) if _rr is not None else None
        if sample_row is None and pilot_df is not None:
            matches = pilot_df[
                (pilot_df["subdivision"] == sub_id) & (pilot_df["lead_day"] == lead_day)
            ]
            if not matches.empty:
                sample_row = matches.iloc[0].to_dict()

        if sample_row is None:
            # Deterministic simulation based on synoptic risk
            is_active_monsoon = sub_id in [
                "KONKAN_GOA", "SAURASHTRA_KUTCH", "ODISHA", "VIDARBHA", "COASTAL_KARNATAKA",
                "CHHATTISGARH", "MADHYA_MAHARASHTRA", "JHARKHAND", "MARATHWADA",
            ]
            fcst_rain = 55.0 if is_active_monsoon else 12.0
            spread_def = 14.0 if is_active_monsoon else -2.0
            mfc = 0.12 if is_active_monsoon else 0.01

            sample_row = build_feature_vector(
                lat=(subdiv.lat_range[0] + subdiv.lat_range[1]) / 2.0,
                lon=(subdiv.lon_range[0] + subdiv.lon_range[1]) / 2.0,
                lead_day=lead_day,
                forecast_precip=fcst_rain,
                ensemble_mean_precip=fcst_rain + 2.0,
                ensemble_std_precip=18.0 if is_active_monsoon else 6.0,
                spread_deficit=spread_def,
                mfc_850=mfc,
                temp_2m=298.0,
                mslp=100200.0 if is_active_monsoon else 100800.0,
                wind_shear=22.0 if is_active_monsoon else 8.0,
                climatological_std=subdiv.climatological_error_std,
            )
            sample_row["subdivision"] = sub_id
            sample_row["observed_precip"] = fcst_rain + (80.0 if is_active_monsoon else 5.0)

        # Predict probability
        sample_df = pd.DataFrame([sample_row])
        if classifier.model is not None:
            prob = float(classifier.predict_proba(sample_df)[0])
        else:
            prob = 0.82 if sub_id in ["KONKAN_GOA", "SAURASHTRA_KUTCH"] else 0.18

        # Confidence Index calculation: FCI = 100 * (1 - P(bust))
        fci = round((1.0 - prob) * 100.0, 1)

        if fci >= 80.0:
            category = "HIGH_CONFIDENCE"
            color = "#10b981"  # Emerald green
        elif fci >= 50.0:
            category = "MODERATE_CONFIDENCE"
            color = "#f59e0b"  # Amber
        else:
            category = "LOW_CONFIDENCE_BUST_RISK"
            color = "#ef4444"  # Red

        is_real = sample_row.get("data_source") == "real-gefs-era5"
        results.append({
            "subdivision_id": sub_id,
            "subdivision_name": subdiv.name,
            "center": [
                (subdiv.lat_range[0] + subdiv.lat_range[1]) / 2.0,
                (subdiv.lon_range[0] + subdiv.lon_range[1]) / 2.0,
            ],
            "lat_range": list(subdiv.lat_range),
            "lon_range": list(subdiv.lon_range),
            "lead_day": lead_day,
            "forecast_precip_mm": round(float(sample_row.get("forecast_precip", 0.0)), 1),
            "observed_precip_mm": round(float(sample_row.get("observed_precip", 0.0)), 1)
            if is_real else None,
            "bust_probability": round(prob, 3),
            "confidence_index": fci,
            "confidence_category": category,
            "status_color": color,
            "is_bust_warning": prob >= 0.50,
            "bust_real": int(sample_row.get("is_bust_real", 0)) if is_real else None,
            "bust_type_real": sample_row.get("bust_type_real") if is_real else None,
            "data_source": "real-gefs-era5" if is_real else "pilot-synthetic",
        })

    return {
        "init_date": date,
        "lead_day": lead_day,
        "total_regions": len(results),
        "bust_warning_count": sum(1 for r in results if r["is_bust_warning"]),
        "regions": results,
    }


@app.get("/api/v1/polygons/warning-zones")
def get_warning_polygons(
    date: str = Query("2019-07-15"),
    lead_day: int = Query(4, ge=1, le=10),
) -> Dict[str, Any]:
    """Return GeoJSON feature collection of error-prone areas exceeding bust thresholds."""
    conf_map = get_confidence_map(date=date, lead_day=lead_day)
    features = []

    for reg in conf_map["regions"]:
        if reg["bust_probability"] >= 0.50:
            lat_min, lat_max = reg["lat_range"]
            lon_min, lon_max = reg["lon_range"]

            # Construct rectangular GeoJSON polygon for subdivision
            polygon_coords = [[
                [lon_min, lat_min],
                [lon_max, lat_min],
                [lon_max, lat_max],
                [lon_min, lat_max],
                [lon_min, lat_min],
            ]]

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": polygon_coords,
                },
                "properties": {
                    "subdivision_id": reg["subdivision_id"],
                    "subdivision_name": reg["subdivision_name"],
                    "bust_probability": reg["bust_probability"],
                    "confidence_index": reg["confidence_index"],
                    "forecast_precip_mm": reg["forecast_precip_mm"],
                    "severity": "CRITICAL" if reg["bust_probability"] >= 0.75 else "WARNING",
                },
            })

    return {
        "type": "FeatureCollection",
        "init_date": date,
        "lead_day": lead_day,
        "features": features,
    }


@app.get("/api/v1/explain")
def explain_subdivision(
    subdivision: str = Query("KONKAN_GOA", description="Subdivision ID"),
    lead_day: int = Query(4, ge=1, le=10),
) -> Dict[str, Any]:
    """Return plain-English meteorological reasoning and SHAP-like attribution weights."""
    subdiv = IMD_SUBDIVISIONS.get(subdivision)
    if not subdiv:
        raise HTTPException(status_code=404, detail="Subdivision not found.")

    # Find sample (real Day-1 row first)
    _rr = _real_row(subdivision, "2019-07-15", lead_day)
    sample_row = dict(_rr) if _rr is not None else None
    if sample_row is None and pilot_df is not None:
        matches = pilot_df[
            (pilot_df["subdivision"] == subdivision) & (pilot_df["lead_day"] == lead_day)
        ]
        if not matches.empty:
            sample_row = matches.iloc[0].to_dict()

    if sample_row is None:
        sample_row = build_feature_vector(
            lat=(subdiv.lat_range[0] + subdiv.lat_range[1]) / 2.0,
            lon=(subdiv.lon_range[0] + subdiv.lon_range[1]) / 2.0,
            lead_day=lead_day,
            forecast_precip=48.0,
            ensemble_mean_precip=50.0,
            ensemble_std_precip=14.0,
            spread_deficit=12.5,
            mfc_850=0.15,
            temp_2m=297.5,
            mslp=100100.0,
            wind_shear=24.0,
            climatological_std=subdiv.climatological_error_std,
        )

    local_reasoner = reasoner or MeteorologicalReasoner(None)
    explanation = local_reasoner.explain_sample(pd.Series(sample_row))

    return {
        "subdivision_id": subdivision,
        "subdivision_name": subdiv.name,
        "lead_day": lead_day,
        "diagnosis": explanation["summary_narrative"],
        "contributing_factors": explanation["top_factors"],
    }
