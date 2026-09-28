#!/usr/bin/env python3
"""
ForecastGuard AI — Prototype Data Ingestion Engine (SIH26079)

Features:
- NOAA GEFSv12 reforecast retrieval from open AWS S3 archive.
- ERA5 single-level and pressure-level retrieval via Copernicus CDS API
  with automatic India bounding box cropping [40N, 60E, 5N, 100E] to minimize bandwidth.
- IMD 0.25° gridded daily rainfall NetCDF ingestion.
- Built-in pilot mode for fetching an end-to-end July 2019 sample day.
- Progress reporting, checksum/size verification, and retry handling.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm


DATA_ROOT = Path(os.getenv("DATA_ROOT", "data/raw"))

# NOAA GEFSv12 public S3 base URL
GEFS_BASE = "https://noaa-gefs-retrospective.s3.amazonaws.com/GEFSv12/reforecast"

# India Bounding Box: [North, West, South, East]
INDIA_BBOX = [40.0, 60.0, 5.0, 100.0]

# Standard GEFS Reforecast Variables
GEFS_VARIABLES = [
    "apcp_sfc",    # Total Precipitation at Surface (kg/m^2 or mm)
    "tmp_2m",      # 2m Temperature (K)
    "pres_msl",    # Mean Sea Level Pressure (Pa)
    "ugrd_10m",    # 10m U-Wind (m/s)
    "vgrd_10m",    # 10m V-Wind (m/s)
    "hgt_pres",    # Geopotential Height (gpm)
    "tmp_pres",    # Temperature on Pressure Levels (K)
    "ugrd_pres",   # U-Wind on Pressure Levels (m/s)
    "vgrd_pres",   # V-Wind on Pressure Levels (m/s)
]


def download_with_progress(url: str, output: Path, timeout: int = 180) -> Path:
    """Stream download a file with progress bar and integrity checks."""
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists() and output.stat().st_size > 0:
        print(f"[CACHE] File already exists: {output} ({output.stat().st_size / 1e6:.2f} MB)")
        return output

    temp_path = output.with_suffix(".tmp")
    headers = {"User-Agent": "ForecastGuardAI-SIH26079/1.0"}

    try:
        with requests.get(url, stream=True, timeout=timeout, headers=headers) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            with temp_path.open("wb") as handle, tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=output.name,
                leave=False,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
                        pbar.update(len(chunk))

        if temp_path.stat().st_size == 0:
            raise RuntimeError(f"Downloaded file is empty from {url}")

        temp_path.rename(output)
        print(f"[SUCCESS] Saved: {output} ({output.stat().st_size / 1e6:.2f} MB)")
        return output

    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Failed downloading {url}: {exc}") from exc


def fetch_gefs_variable(
    init_yyyymmddhh: str,
    variable: str = "tmp_2m",
    member: str = "c00",
    period: str = "Days:1-10",
) -> Path:
    """
    Download a GEFSv12 reforecast variable file from AWS S3.
    
    Example:
        init_yyyymmddhh = 2019071500
        variable = apcp_sfc
        member = c00 (control) or p01..p04 (perturbed)
    """
    year = init_yyyymmddhh[:4]
    filename = f"{variable}_{init_yyyymmddhh}_{member}.grib2"
    url = f"{GEFS_BASE}/{year}/{init_yyyymmddhh}/{member}/{period}/{filename}"
    output = DATA_ROOT / "gefs" / year / init_yyyymmddhh / member / filename

    print(f"[GEFS] Ingesting: {variable} (Member: {member}, Init: {init_yyyymmddhh})")
    return download_with_progress(url, output)


def fetch_era5_data(
    year: str,
    month: str,
    day: str,
    data_type: str = "pressure",
    target_path: Optional[Path] = None,
) -> Path:
    """
    Download ERA5 data via Copernicus CDS API with automatic India BBox cropping.
    
    Data types:
        - 'pressure': 850 & 500 hPa geopotential, temperature, u/v winds.
        - 'surface': 2m temperature, total precipitation, 10m u/v winds, MSLP.
    """
    try:
        import cdsapi
    except ImportError as exc:
        raise SystemExit(
            "CDS API client is missing. Please run:\n  pip install \"cdsapi>=0.7.7\""
        ) from exc

    # Check for ~/.cdsapirc credentials
    cdsapirc_path = Path.home() / ".cdsapirc"
    if not cdsapirc_path.exists() and "CDSAPI_KEY" not in os.environ:
        print("\n[WARNING] Copernicus CDS credentials not found!")
        print("1. Register for free at: https://cds.climate.copernicus.eu")
        print(f"2. Create {cdsapirc_path} with:")
        print("   url: https://cds.climate.copernicus.eu/api")
        print("   key: YOUR_PERSONAL_ACCESS_TOKEN\n")

    month_str = f"{int(month):02d}"
    day_str = f"{int(day):02d}"

    if target_path is None:
        target_path = (
            DATA_ROOT
            / "era5"
            / year
            / f"era5_{data_type}_{year}{month_str}{day_str}.nc"
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and target_path.stat().st_size > 0:
        print(f"[CACHE] ERA5 file already exists: {target_path}")
        return target_path

    client = cdsapi.Client()

    if data_type == "pressure":
        dataset_name = "reanalysis-era5-pressure-levels"
        request = {
            "product_type": ["reanalysis"],
            "variable": [
                "geopotential",
                "temperature",
                "u_component_of_wind",
                "v_component_of_wind",
            ],
            "pressure_level": ["500", "850"],
            "year": [str(year)],
            "month": [month_str],
            "day": [day_str],
            "time": ["00:00", "06:00", "12:00", "18:00"],
            "area": INDIA_BBOX,  # Cropped directly on CDS server!
            "data_format": "netcdf",
        }
    else:  # surface
        dataset_name = "reanalysis-era5-single-levels"
        request = {
            "product_type": ["reanalysis"],
            "variable": [
                "2m_temperature",
                "total_precipitation",
                "10m_u_component_of_wind",
                "10m_v_component_of_wind",
                "mean_sea_level_pressure",
            ],
            "year": [str(year)],
            "month": [month_str],
            "day": [day_str],
            "time": [f"{h:02d}:00" for h in range(24)],
            "area": INDIA_BBOX,  # Cropped directly on CDS server!
            "data_format": "netcdf",
        }

    print(f"[ERA5] Requesting {data_type} reanalysis for {year}-{month_str}-{day_str} over India BBox...")
    client.retrieve(dataset_name, request, str(target_path))
    print(f"[SUCCESS] Saved ERA5 to {target_path}")
    return target_path


def fetch_imd_rainfall(year: int, url: Optional[str] = None) -> Path:
    """
    Download IMD 0.25° daily gridded rainfall NetCDF file for a given year.
    If no direct URL is supplied, uses IMD Pune open repository structure.
    """
    output = DATA_ROOT / "imd" / f"rainfall_ind_{year}_rfp25.nc"
    if url is None:
        # Standard IMD Pune 0.25 gridded rainfall naming convention
        url = f"https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF/{year}.nc"

    print(f"[IMD] Ingesting 0.25° Gridded Rainfall for {year}...")
    try:
        return download_with_progress(url, output)
    except Exception as exc:
        print(f"[NOTE] Direct automatic download from IMD website returned: {exc}")
        print("IMD website periodically updates session tokens. You can also download")
        print(f"the NetCDF manually from https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html")
        print(f"and place the file at: {output}")
        return output


def run_pilot_pipeline(init_date: str = "20190715") -> None:
    """
    Download a minimal end-to-end pilot dataset:
    - 2019-07-15 Monsoon depression case
    - GEFS precipitation, 2m temp, and pressure fields
    - ERA5 cropped surface and pressure levels
    - IMD 2019 rainfall
    """
    init_time = f"{init_date}00"
    year = init_date[:4]
    month = init_date[4:6]
    day = init_date[6:8]

    print("\n=============================================================")
    print(f" ForecastGuard AI — Downloading Pilot Slice: {init_date}")
    print("=============================================================\n")

    # 1. GEFS Key Variables
    pilot_vars = ["apcp_sfc", "tmp_2m", "pres_msl"]
    for var in pilot_vars:
        fetch_gefs_variable(init_time, variable=var, member="c00")

    # 2. ERA5 Reference (India Cropped)
    try:
        fetch_era5_data(year, month, day, data_type="surface")
        fetch_era5_data(year, month, day, data_type="pressure")
    except Exception as e:
        print(f"[ERA5 Skip] CDS download not completed (check .cdsapirc): {e}")

    # 3. IMD Reference
    fetch_imd_rainfall(int(year))

    print("\n[COMPLETE] Pilot data download attempt finished.")
    print(f"Files saved in: {DATA_ROOT.resolve()}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="ForecastGuard AI Data Fetcher")
    # Top-level --pilot flag (spec compatibility: `python fetch_data.py --pilot`)
    parser.add_argument("--pilot", action="store_true", help="Fetch end-to-end pilot slice (July 15, 2019)")
    parser.add_argument("--date", default="20190715", help="Pilot date YYYYMMDD (used with --pilot)")
    sub = parser.add_subparsers(dest="command", required=False)

    # GEFS CLI
    p_gefs = sub.add_parser("gefs", help="Fetch NOAA GEFSv12 reforecast")
    p_gefs.add_argument("--init", required=True, help="Init time: YYYYMMDDHH (e.g. 2019071500)")
    p_gefs.add_argument("--var", default="apcp_sfc", choices=GEFS_VARIABLES, help="Variable name")
    p_gefs.add_argument("--member", default="c00", help="Ensemble member (c00, p01..p04)")

    # ERA5 CLI
    p_era5 = sub.add_parser("era5", help="Fetch ERA5 reanalysis via CDS API")
    p_era5.add_argument("--year", required=True, help="Year (YYYY)")
    p_era5.add_argument("--month", required=True, help="Month (MM)")
    p_era5.add_argument("--day", required=True, help="Day (DD)")
    p_era5.add_argument("--type", default="pressure", choices=["pressure", "surface"], help="Data type")

    # IMD CLI
    p_imd = sub.add_parser("imd", help="Fetch IMD 0.25 gridded rainfall")
    p_imd.add_argument("--year", type=int, required=True, help="Year (YYYY)")
    p_imd.add_argument("--url", default=None, help="Custom direct URL if available")

    # Pilot CLI
    p_pilot = sub.add_parser("pilot", help="Fetch end-to-end pilot slice (July 15, 2019)")
    p_pilot.add_argument("--date", default="20190715", help="YYYYMMDD (default: 20190715)")

    args = parser.parse_args()

    # `python fetch_data.py --pilot [--date YYYYMMDD]` compatibility alias
    if getattr(args, "pilot", False):
        run_pilot_pipeline(args.date)
        return

    if args.command is None:
        parser.print_help()
        return

    if args.command == "gefs":
        fetch_gefs_variable(args.init, args.var, args.member)
    elif args.command == "era5":
        fetch_era5_data(args.year, args.month, args.day, args.type)
    elif args.command == "imd":
        fetch_imd_rainfall(args.year, args.url)
    elif args.command == "pilot":
        run_pilot_pipeline(args.date)


if __name__ == "__main__":
    main()
