#!/usr/bin/env python3
"""Real-data pilot extractor (SIH26079) — GEFS forecast vs ERA5 truth.

Compares the NOAA GEFSv12 control run for init 20190715 00UTC against ERA5
reanalysis truth for the valid day, aggregated over all 36 IMD subdivisions.

  Day-1 valid window = init day 00Z -> +24h  (2019-07-15).

Outputs (data/processed/):
  real_pilot_day{day}.parquet  - one row per subdivision with real forecast,
                            real observed, real dynamics + model features
  real_pilot_day{day}.json     - same payload as JSON (debug / API fallback)

Honesty flags (documented, not hidden):
  * GEFS archive holds the CONTROL member only -> no true ensemble spread.
    ensemble_std_precip is estimated as 0.35 * climatological_std and the
    spread deficit is derived from it via the standard physics function.
  * No humidity/dewpoint channel in the pilot files -> mfc_850 falls back to
    the subdivision pilot median; u200 is absent -> shear falls back too.
    Fields filled this way are listed in ESTIMATED_FIELDS.
  * Observed truth here is ERA5 total precipitation. IMD 0.25-deg gridded
    rainfall remains the designated operational truth (manual download).

Usage:
  python -m src.ingestion.real_pilot --init 2019071500 --day 1
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.synoptic import (
    build_feature_vector,
    compute_llj_index,
    compute_spread_skill_deficit,
)
from src.labeling.bust_engine import compute_3d_bust_labels
from src.preprocessing.grid import IMD_SUBDIVISIONS

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

ESTIMATED_FIELDS = ["ensemble_std_precip", "mfc_850", "wind_shear_200_850"]


def _india_slices(lats, lons, lat_range=(5.0, 40.0), lon_range=(60.0, 100.0)):
    """Index slices cropping any regular lat/lon grid to the India box."""
    lats = np.asarray(lats)
    lon = np.where(np.asarray(lons) > 180.0, np.asarray(lons) - 360.0, np.asarray(lons))
    lat_idx = np.where((lats >= lat_range[0]) & (lats <= lat_range[1]))[0]
    lon_idx = np.where((lon >= lon_range[0]) & (lon <= lon_range[1]))[0]
    return slice(int(lat_idx.min()), int(lat_idx.max()) + 1), slice(
        int(lon_idx.min()), int(lon_idx.max()) + 1)


def _subdiv_mask(lats, lons, lat_range, lon_range):
    lat2d, lon2d = np.meshgrid(np.asarray(lats), np.asarray(lons), indexing="ij")
    lon = np.where(lon2d > 180.0, lon2d - 360.0, lon2d)
    return (
        (lat2d >= lat_range[0])
        & (lat2d <= lat_range[1])
        & (lon >= lon_range[0])
        & (lon <= lon_range[1])
    )


def _ensure_surface_extracted(surface_zip: Path) -> Path:
    out = surface_zip.parent / (surface_zip.stem + "_extracted")
    instant = out / "data_stream-oper_stepType-instant.nc"
    accum = out / "data_stream-oper_stepType-accum.nc"
    if not (instant.exists() and accum.exists()):
        out.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(surface_zip) as zf:
            zf.extractall(out)
    return out


def build_real_day(init_yyyymmddhh: str = "2019071500", day: int = 1) -> pd.DataFrame:
    import xarray as xr

    date = init_yyyymmddhh[:8]  # 20190715
    year = date[:4]
    # Day-N valid date = init day + (N-1); Day-1 window = init 00Z -> +24h.
    valid_date = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]}") + pd.Timedelta(days=day - 1)
    valid_str = valid_date.strftime("%Y%m%d")

    gefs_dir = DATA_RAW / "gefs" / year / init_yyyymmddhh / "c00"
    gefs_tp = xr.open_dataset(
        gefs_dir / f"apcp_sfc_{init_yyyymmddhh}_c00.grib2", engine="cfgrib"
    )
    gefs_t2m = xr.open_dataset(
        gefs_dir / f"tmp_2m_{init_yyyymmddhh}_c00.grib2", engine="cfgrib"
    )
    gefs_msl = xr.open_dataset(
        gefs_dir / f"pres_msl_{init_yyyymmddhh}_c00.grib2", engine="cfgrib"
    )

    # 3-hourly steps: Day-N window = steps [8(N-1), 8N-1]; tp is since-init
    # accumulation, so subtract the window start.
    end_idx, start_idx = 8 * day - 1, 8 * (day - 1) - 1
    valid = pd.DatetimeIndex(gefs_tp["valid_time"].values)
    expect_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]}") + pd.Timedelta(days=day)
    assert valid[end_idx] == expect_end, f"Day-{day} step mismatch: {valid[end_idx]} vs {expect_end}"
    print(f"[REAL] GEFS Day-{day} window: {valid[start_idx + 1] if start_idx >= 0 else valid[0] - pd.Timedelta(hours=3)} -> {valid[end_idx]}")

    fcst_day = gefs_tp["tp"].isel(step=end_idx)  # kg/m^2 == mm
    if start_idx >= 0:
        fcst_day = fcst_day - gefs_tp["tp"].isel(step=start_idx)
    t2m_day = gefs_t2m["t2m"].isel(step=slice(start_idx + 1, end_idx + 1)).mean(dim="step")
    msl_day = gefs_msl["msl"].isel(step=slice(start_idx + 1, end_idx + 1)).mean(dim="step")

    era5_dir = DATA_RAW / "era5" / year
    surf = _ensure_surface_extracted(era5_dir / f"era5_surface_{valid_str}.nc")
    era_accum = xr.open_dataset(surf / "data_stream-oper_stepType-accum.nc")
    era_inst = xr.open_dataset(surf / "data_stream-oper_stepType-instant.nc")
    era_pres = xr.open_dataset(
        era5_dir / f"era5_pressure_{valid_str}.nc", engine="netcdf4"
    )

    obs_day = era_accum["tp"].sum(dim="valid_time") * 1000.0  # m -> mm/day
    obs_t2m = era_inst["t2m"].mean(dim="valid_time")
    obs_msl = era_inst["msl"].mean(dim="valid_time")
    u850 = era_pres["u"].sel(pressure_level=850.0).mean(dim="valid_time")
    v850 = era_pres["v"].sel(pressure_level=850.0).mean(dim="valid_time")

    # Common 0.25-deg India grids for the bust engine.
    glats = np.asarray(gefs_tp["latitude"].values)
    glons = np.asarray(gefs_tp["longitude"].values)
    elats = np.asarray(era_accum["latitude"].values)
    elons = np.asarray(era_accum["longitude"].values)

    gsl, gosl = _india_slices(glats, glons)
    esl, eosl = _india_slices(elats, elons)
    fcst_grid = np.asarray(fcst_day.values[gsl, gosl])
    obs_grid = np.asarray(obs_day.values[esl, eosl])
    assert fcst_grid.shape == obs_grid.shape == (141, 161), (
        fcst_grid.shape, obs_grid.shape)
    # Cropped coordinate vectors back the subdivision masks below.
    glats = glats[gsl, gosl][:, 0] if glats.ndim == 2 else glats[gsl]
    glons = glons[gsl, gosl][0, :] if glons.ndim == 2 else glons[gosl]
    elats = elats[esl, eosl][:, 0] if elats.ndim == 2 else elats[esl]
    elons = elons[esl, eosl][0, :] if elons.ndim == 2 else elons[eosl]

    llj = compute_llj_index(
        np.asarray(u850.values), np.asarray(v850.values),
        np.asarray(era_pres["latitude"].values),
        np.asarray(era_pres["longitude"].values),
    )
    print(f"[REAL] ERA5 obs-day mean: {float(np.nanmean(obs_grid)):.1f} mm | LLJ: {llj:.1f} m/s")

    # Pilot medians for the fields no pilot file carries (flagged downstream).
    pilot_path = DATA_PROCESSED / "pilot_samples.parquet"
    pilot_meds = {}
    if pilot_path.exists():
        pdf = pd.read_parquet(pilot_path)
        pilot_meds = pdf.groupby("subdivision")[["mfc_850", "wind_shear_200_850"]].median()

    records = []
    for sub_id, sub in IMD_SUBDIVISIONS.items():
        gm = _subdiv_mask(glats, glons, sub.lat_range, sub.lon_range)
        em = _subdiv_mask(elats, elons, sub.lat_range, sub.lon_range)
        clim = sub.climatological_error_std

        f_vals = fcst_grid[gm]
        o_vals = obs_grid[em]
        if f_vals.size == 0 or o_vals.size == 0:
            print(f"[REAL] WARNING: empty cut-out for {sub_id}, skipped")
            continue
        n = min(f_vals.size, o_vals.size)
        f_col = f_vals.ravel()[:n].reshape(-1, 1)
        o_col = o_vals.ravel()[:n].reshape(-1, 1)
        f_mean, o_mean = float(np.nanmean(f_vals)), float(np.nanmean(o_vals))

        # Real bust label on the regional cut-out (scalar clim grid).
        labels = compute_3d_bust_labels(
            f_col, o_col, np.full_like(f_col, clim))
        frac = float(np.mean(labels["is_bust"])) if labels["is_bust"].size else 0.0
        is_bust = frac >= 0.05
        types, counts = np.unique(labels["bust_type"][labels["is_bust"]], return_counts=True) \
            if is_bust else ([], [])
        top_type = str(types[int(np.argmax(counts))]) if len(types) else "NO_BUST"

        ens_std = max(1.0, 0.35 * clim)
        spread_def = float(compute_spread_skill_deficit(
            np.array([[ens_std]]), lead_day=day)[0, 0])
        mfc_med = float(pilot_meds.loc[sub_id, "mfc_850"]) if sub_id in pilot_meds.index else 0.01
        shear_med = float(pilot_meds.loc[sub_id, "wind_shear_200_850"]) if sub_id in pilot_meds.index else 10.0

        lat_c = (sub.lat_range[0] + sub.lat_range[1]) / 2.0
        lon_c = (sub.lon_range[0] + sub.lon_range[1]) / 2.0
        feat = build_feature_vector(
            lat=lat_c, lon=lon_c, lead_day=day,
            forecast_precip=f_mean,
            ensemble_mean_precip=f_mean,
            ensemble_std_precip=ens_std,
            spread_deficit=spread_def,
            mfc_850=mfc_med,
            temp_2m=float(np.nanmean(np.asarray(
                obs_t2m.values[esl, eosl])[em])),
            mslp=float(np.nanmean(np.asarray(
                obs_msl.values[esl, eosl])[em])),
            wind_shear=shear_med,
            climatological_std=clim,
        )
        feat.update({
            "subdivision": sub_id,
            "observed_precip": o_mean,
            "abs_error_real": abs(f_mean - o_mean),
            "is_bust_real": int(is_bust),
            "bust_type_real": top_type,
            "bust_fraction_real": round(frac, 4),
            "llj_index_real": round(float(llj), 2),
            "data_source": "real-gefs-era5",
            "estimated_fields": ",".join(ESTIMATED_FIELDS),
        })
        records.append(feat)

    df = pd.DataFrame(records)
    n_real = int(df["is_bust_real"].sum())
    print(f"[REAL] {len(df)} subdivisions | real busts: {n_real} | "
          f"mean |err|: {df['abs_error_real'].mean():.1f} mm")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Real-data pilot extractor (GEFS vs ERA5, per lead day)")
    ap.add_argument("--init", default="2019071500")
    ap.add_argument("--day", type=int, default=1,
                    help="Lead day 1-10 (needs ERA5 truth for the valid date on disk)")
    args = ap.parse_args()
    if not 1 <= args.day <= 10:
        raise SystemExit("Day must be 1-10.")
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df = build_real_day(args.init, args.day)
    df.to_parquet(DATA_PROCESSED / f"real_pilot_day{args.day}.parquet", index=False)
    (DATA_PROCESSED / f"real_pilot_day{args.day}.json").write_text(
        df.to_json(orient="records", indent=1), encoding="utf-8"
    )
    print(f"[REAL] wrote real_pilot_day{args.day}.parquet ({len(df)} rows)")


if __name__ == "__main__":
    main()
