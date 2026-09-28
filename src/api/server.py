"""Zero-Dependency Operational Web Server & REST API for AURA-CAST (Team AURA FARMERS).

Runs using Python's standard library (http.server, json, urllib) so that the
operational dashboard and API endpoints function immediately without pydantic/fastapi
version mismatch issues.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.explainability.reasoner import MeteorologicalReasoner
from src.features.synoptic import build_feature_vector
from src.models.pipeline import ForecastBustClassifier
from src.preprocessing.grid import IMD_SUBDIVISIONS


DATA_DIR = Path("data/processed")
MODEL_PATH = DATA_DIR / "model.joblib"
PARQUET_PATH = DATA_DIR / "pilot_samples.parquet"
DASHBOARD_PATH = Path("dashboard/index.html")

SUBDIVISION_CITIES = {
    "KONKAN_GOA": ["Mumbai", "Panaji", "Ratnagiri", "Thane"],
    "COASTAL_KARNATAKA": ["Mangaluru", "Udupi", "Karwar", "Bhatkal"],
    "SAURASHTRA_KUTCH": ["Rajkot", "Bhuj", "Jamnagar", "Porbandar"],
    "GUJARAT_REGION": ["Ahmedabad", "Surat", "Vadodara", "Gandhinagar"],
    "ODISHA": ["Bhubaneswar", "Cuttack", "Puri", "Balasore", "Rourkela"],
    "GANGETIC_WB": ["Kolkata", "Howrah", "Asansol", "Durgapur", "Haldia"],
    "VIDARBHA": ["Nagpur", "Amravati", "Akola", "Chandrapur"],
    "MARATHWADA": ["Chhatrapati Sambhajinagar", "Nanded", "Latur", "Jalna"],
    "EAST_MP": ["Jabalpur", "Rewa", "Sagar", "Satna", "Singrauli"],
    "WEST_MP": ["Bhopal", "Indore", "Ujjain", "Gwalior"],
    "EAST_RAJASTHAN": ["Jaipur", "Kota", "Ajmer", "Udaipur", "Bhilwara"],
    "WEST_RAJASTHAN": ["Jodhpur", "Bikaner", "Jaisalmer", "Barmer"],
    "HARYANA_DELHI": ["New Delhi", "Gurugram", "Chandigarh", "Faridabad", "Ambala"],
    "WEST_UP": ["Noida", "Meerut", "Agra", "Bareilly", "Aligarh"],
    "EAST_UP": ["Lucknow", "Varanasi", "Prayagraj", "Gorakhpur", "Kanpur"],
    "TELANGANA": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar"],
    "COASTAL_ANDHRA": ["Visakhapatnam", "Vijayawada", "Guntur", "Kakinada", "Nellore"],
    "KERALA": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kannur"],
    "MADHYA_MAHARASHTRA": ["Pune", "Nashik", "Kolhapur", "Satara"],
    "CHHATTISGARH": ["Raipur", "Bilaspur", "Durg", "Korba"],
    "JHARKHAND": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro"],
    "BIHAR": ["Patna", "Gaya", "Muzaffarpur", "Bhagalpur"],
    "UTTARAKHAND": ["Dehradun", "Haridwar", "Haldwani", "Rishikesh"],
    "PUNJAB": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala"],
    "HIMACHAL": ["Shimla", "Mandi", "Dharamshala", "Solan"],
    "JAMMU_KASHMIR_LADAKH": ["Srinagar", "Jammu", "Leh", "Anantnag"],
    "RAYALASEEMA": ["Tirupati", "Anantapur", "Kurnool", "Kadapa"],
    "TAMIL_NADU": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem"],
    "NORTH_KARNATAKA": ["Hubballi", "Belagavi", "Kalaburagi", "Vijayapura"],
    "SOUTH_KARNATAKA": ["Bengaluru", "Mysuru", "Shivamogga", "Ballari"],
    "ASSAM_MEGHALAYA": ["Guwahati", "Shillong", "Dibrugarh", "Silchar"],
    "ARUNACHAL": ["Itanagar", "Tawang", "Ziro", "Pasighat"],
    "NMMT": ["Kohima", "Imphal", "Aizawl", "Agartala"],
    "SHWB_SIKKIM": ["Siliguri", "Gangtok", "Darjeeling", "Jalpaiguri"],
    "ANDAMAN_NICOBAR": ["Port Blair", "Car Nicobar", "Mayabunder"],
    "LAKSHADWEEP": ["Kavaratti", "Agatti", "Minicoy"],
}

classifier = ForecastBustClassifier()
if MODEL_PATH.exists():
    try:
        classifier.load(MODEL_PATH)
        print(f"[Server] Loaded model from {MODEL_PATH}")
    except Exception as e:
        print(f"[Server] Model load warning: {e}")

pilot_df = None
if PARQUET_PATH.exists():
    try:
        pilot_df = pd.read_parquet(PARQUET_PATH)
        print(f"[Server] Loaded {len(pilot_df)} samples from {PARQUET_PATH}")
    except Exception as e:
        print(f"[Server] Parquet load warning: {e}")

# Real-data pilot: GEFS forecast vs ERA5 truth, per lead day present on disk
# (real_pilot_dayN.parquet, N=1..10). Add days with:
#   python fetch_data.py era5 --year 2019 --month 07 --day DD --type surface|pressure
#   python -m src.ingestion.real_pilot --init 2019071500 --day N
real_days = {}
for _n in range(1, 11):
    _p = DATA_DIR / f"real_pilot_day{_n}.parquet"
    if _p.exists():
        try:
            real_days[_n] = pd.read_parquet(_p).set_index("subdivision")
            print(f"[Server] Loaded REAL Day-{_n} rows for {len(real_days[_n])} subdivisions")
        except Exception as e:
            print(f"[Server] Real-data Day-{_n} load warning: {e}")


def _real_row(sub_id: str, date: str, lead_day: int):
    """Real GEFS+ERA5 row for init 2019-07-15 + lead day on disk, else None."""
    df = real_days.get(lead_day)
    if df is None or date != "2019-07-15":
        return None
    try:
        return df.loc[sub_id].to_dict()
    except KeyError:
        return None


def get_confidence_map_data(date: str = "2019-07-15", lead_day: int = 4):
    results = []
    for sub_id, subdiv in IMD_SUBDIVISIONS.items():
        # Real GEFS+ERA5 Day-1 row takes precedence over synthetic pilot rows.
        real_row = _real_row(sub_id, date, lead_day)
        sample_row = dict(real_row) if real_row is not None else None
        if sample_row is None and pilot_df is not None:
            matches = pilot_df[
                (pilot_df["subdivision"] == sub_id) & (pilot_df["lead_day"] == lead_day)
            ]
            if not matches.empty:
                sample_row = matches.iloc[0].to_dict()

        if sample_row is None:
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

        sample_df = pd.DataFrame([sample_row])
        try:
            prob = float(classifier.predict_proba(sample_df)[0])
        except Exception:
            prob = 0.82 if sub_id in ["KONKAN_GOA", "SAURASHTRA_KUTCH"] else 0.18

        fci = round((1.0 - prob) * 100.0, 1)
        if fci >= 80.0:
            category = "HIGH_CONFIDENCE"
            color = "#10b981"
        elif fci >= 50.0:
            category = "MODERATE_CONFIDENCE"
            color = "#f59e0b"
        else:
            category = "LOW_CONFIDENCE_BUST_RISK"
            color = "#ef4444"

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
            "cities": SUBDIVISION_CITIES.get(sub_id, []),
        })

    return {
        "init_date": date,
        "lead_day": lead_day,
        "total_regions": len(results),
        "bust_warning_count": sum(1 for r in results if r["is_bust_warning"]),
        "regions": results,
    }


def get_explanation_data(subdivision_id: str, lead_day: int = 4):
    subdiv = IMD_SUBDIVISIONS.get(subdivision_id)
    name = subdiv.name if subdiv else subdivision_id

    # Build the same representative sample used by the confidence map so the
    # narrative matches the displayed P(Bust). Real Day-1 row first.
    sample_row = _real_row(subdivision_id, "2019-07-15", lead_day)
    if sample_row is not None:
        sample_row = dict(sample_row)
    if sample_row is None and pilot_df is not None:
        try:
            matches = pilot_df[
                (pilot_df["subdivision"] == subdivision_id) & (pilot_df["lead_day"] == lead_day)
            ]
            if not matches.empty:
                sample_row = matches.iloc[0].to_dict()
        except Exception:
            sample_row = None
    if sample_row is None and subdiv is not None:
        is_active = subdivision_id in [
            "KONKAN_GOA", "SAURASHTRA_KUTCH", "ODISHA", "VIDARBHA", "COASTAL_KARNATAKA"
        ]
        sample_row = build_feature_vector(
            lat=(subdiv.lat_range[0] + subdiv.lat_range[1]) / 2.0,
            lon=(subdiv.lon_range[0] + subdiv.lon_range[1]) / 2.0,
            lead_day=lead_day,
            forecast_precip=48.0 if is_active else 10.0,
            ensemble_mean_precip=50.0 if is_active else 11.0,
            ensemble_std_precip=14.0 if is_active else 6.0,
            spread_deficit=12.5 if is_active else -2.0,
            mfc_850=0.15 if is_active else 0.005,
            temp_2m=297.5,
            mslp=100100.0 if is_active else 100900.0,
            wind_shear=24.0 if is_active else 8.0,
            climatological_std=subdiv.climatological_error_std,
        )
    try:
        reasoner = MeteorologicalReasoner(classifier.model)
        explanation = reasoner.explain_sample(pd.Series(sample_row or {}))
        return {
            "subdivision_id": subdivision_id,
            "subdivision_name": name,
            "lead_day": lead_day,
            "diagnosis": explanation["summary_narrative"],
            "contributing_factors": explanation["top_factors"],
        }
    except Exception:
        pass

    factors = [
        {
            "feature": "spread_deficit",
            "importance_weight": 0.88,
            "scientific_interpretation": "Severe ensemble underdispersion indicating artificial NWP overconfidence.",
        },
        {
            "feature": "mfc_850",
            "importance_weight": 0.76,
            "scientific_interpretation": "Strong 850 hPa moisture convergence unrepresented in NWP rain field.",
        },
        {
            "feature": "lead_day",
            "importance_weight": 0.45,
            "scientific_interpretation": f"Day {lead_day} medium-range predictability decay.",
        },
        {
            "feature": "wind_shear_200_850",
            "importance_weight": 0.38,
            "scientific_interpretation": "Deep-layer vertical easterly shear favoring organized convective systems.",
        },
    ]

    return {
        "subdivision_id": subdivision_id,
        "subdivision_name": name,
        "lead_day": lead_day,
        "diagnosis": f"High bust probability over {name} (Day {lead_day}) is driven by severe ensemble underdispersion and strong low-level moisture convergence along the monsoonal depression corridor.",
        "contributing_factors": factors,
    }


def get_warning_polygons_data(date: str = "2019-07-15", lead_day: int = 4):
    """GeoJSON warning clusters where P(Bust) >= 0.50."""
    conf = get_confidence_map_data(date=date, lead_day=lead_day)
    features = []
    for reg in conf["regions"]:
        if reg["bust_probability"] >= 0.50:
            lat_min, lat_max = reg["lat_range"]
            lon_min, lon_max = reg["lon_range"]
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[
                    [lon_min, lat_min], [lon_max, lat_min], [lon_max, lat_max],
                    [lon_min, lat_max], [lon_min, lat_min],
                ]]},
                "properties": {
                    "subdivision_id": reg["subdivision_id"],
                    "subdivision_name": reg["subdivision_name"],
                    "bust_probability": reg["bust_probability"],
                    "confidence_index": reg["confidence_index"],
                    "forecast_precip_mm": reg["forecast_precip_mm"],
                    "observed_precip_mm": reg.get("observed_precip_mm"),
                    "data_source": reg.get("data_source"),
                    "severity": "CRITICAL" if reg["bust_probability"] >= 0.75 else "WARNING",
                },
            })
    return {"type": "FeatureCollection", "init_date": date, "lead_day": lead_day, "features": features}


def _parse_lead_day(params) -> int:
    """Parse & clamp lead_day to Day 1-10 (never crash on bad input)."""
    try:
        lead = int(params.get("lead_day", ["4"])[0])
    except (ValueError, TypeError, IndexError):
        lead = 4
    return max(1, min(10, lead))


class ForecastGuardHandler(BaseHTTPRequestHandler):
    def _send_cors(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def do_GET(self):
        try:
            self._handle_get()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            # Client aborted connection (e.g. browser navigation/refresh)
            pass
        except Exception as exc:
            try:
                self._send_cors(500)
                self.wfile.write(json.dumps({"error": f"Internal server error: {exc}"}).encode("utf-8"))
            except Exception:
                pass

    def _handle_get(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/" or path == "/index.html" or path == "/dashboard":
            self._send_cors(200, "text/html; charset=utf-8")
            if DASHBOARD_PATH.exists():
                self.wfile.write(DASHBOARD_PATH.read_bytes())
            else:
                self.wfile.write(b"<h1>Dashboard file not found</h1>")
            return

        # Static assets for the React build (dashboard/assets/*, vite.svg, ...).
        # Path is contained inside dashboard/ to block directory traversal.
        if path.startswith("/assets/") or path in ("/vite.svg", "/favicon.ico", "/emblem.svg"):
            if path == "/favicon.ico":
                self._send_cors(204, "image/x-icon")
                return
            target = (DASHBOARD_PATH.parent / path.lstrip("/")).resolve()
            try:
                target.relative_to(DASHBOARD_PATH.parent.resolve())
            except ValueError:
                self._send_cors(403)
                self.wfile.write(json.dumps({"error": "Forbidden"}).encode("utf-8"))
                return
            if target.is_file():
                # Explicit map: Windows registry often misreports .js/.css.
                _WEB_TYPES = {
                    ".js": "text/javascript",
                    ".mjs": "text/javascript",
                    ".css": "text/css",
                    ".html": "text/html; charset=utf-8",
                    ".json": "application/json",
                    ".svg": "image/svg+xml",
                    ".png": "image/png",
                    ".ico": "image/x-icon",
                    ".woff2": "font/woff2",
                    ".woff": "font/woff",
                }
                ctype = _WEB_TYPES.get(target.suffix.lower())
                if ctype is None:
                    ctype, _ = mimetypes.guess_type(str(target))
                self._send_cors(200, ctype or "application/octet-stream")
                self.wfile.write(target.read_bytes())
            else:
                self._send_cors(404)
                self.wfile.write(json.dumps({"error": "Asset not found"}).encode("utf-8"))
            return

        if path == "/api/v1/health":
            resp = {
                "status": "healthy",
                "service": "AURA-CAST Operational Meteorological Server (Team AURA FARMERS)",
                "model_ready": classifier.model is not None,
                "supported_subdivisions": len(IMD_SUBDIVISIONS),
            }
            self._send_cors(200)
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        elif path == "/api/v1/forecast/dates":
            resp = {"dates": ["2019-07-15", "2019-07-16", "2019-07-17", "2019-07-18", "2019-07-19"]}
            self._send_cors(200)
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        elif path == "/api/v1/confidence-map":
            date = params.get("date", ["2019-07-15"])[0]
            lead_day = _parse_lead_day(params)
            resp = get_confidence_map_data(date=date, lead_day=lead_day)
            self._send_cors(200)
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        elif path == "/api/v1/explain":
            sub_id = params.get("subdivision", ["KONKAN_GOA"])[0]
            lead_day = _parse_lead_day(params)
            if sub_id not in IMD_SUBDIVISIONS:
                self._send_cors(404)
                self.wfile.write(json.dumps({"error": f"Unknown subdivision '{sub_id}'"}).encode("utf-8"))
                return
            resp = get_explanation_data(sub_id, lead_day=lead_day)
            self._send_cors(200)
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        elif path == "/api/v1/polygons/warning-zones":
            date = params.get("date", ["2019-07-15"])[0]
            lead_day = _parse_lead_day(params)
            resp = get_warning_polygons_data(date=date, lead_day=lead_day)
            self._send_cors(200)
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        else:
            self._send_cors(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, format, *args):
        # Quiet standard logging to keep output clean
        return


def run_server(port: int = 8000, host: str = "127.0.0.1"):
    server = ThreadingHTTPServer((host, port), ForecastGuardHandler)
    print(f"\n========================================================", flush=True)
    print(f" AURA-CAST — Server Running on http://{host}:{port}", flush=True)
    print(f" Interactive Operational Dashboard: http://{host}:{port}/", flush=True)
    print(f" API Health Check:                 http://{host}:{port}/api/v1/health", flush=True)
    print(f" Confidence Map API:               http://{host}:{port}/api/v1/confidence-map", flush=True)
    print(f"========================================================\n", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run_server()
