"""Physical & Synoptic Feature Extraction Engine (SIH26079)."""

from __future__ import annotations

from typing import Dict, List
import numpy as np


def compute_moisture_flux_convergence(
    u_850: np.ndarray,      # 850 hPa zonal wind (m/s)
    v_850: np.ndarray,      # 850 hPa meridional wind (m/s)
    q_850: np.ndarray,      # 850 hPa specific humidity (kg/kg)
    dx: float = 27750.0,    # ~0.25 deg in meters
    dy: float = 27750.0,
) -> np.ndarray:
    """
    Compute Moisture Flux Convergence (MFC) at 850 hPa:
        MFC = - ( d(q*u)/dx + d(q*v)/dy )
    Positive values represent moisture convergence (favorable for convection).
    """
    qu = q_850 * u_850
    qv = q_850 * v_850

    dqu_dx = np.gradient(qu, dx, axis=1)
    dqv_dy = np.gradient(qv, dy, axis=0)

    mfc = -(dqu_dx + dqv_dy)
    return mfc


def compute_spread_skill_deficit(
    ensemble_std: np.ndarray,       # 2D array of ensemble standard deviation
    lead_day: int,
    base_spread_norm: float = 12.0, # Baseline normal spread for lead day
) -> np.ndarray:
    """
    Compute Spread-Skill Deficit:
        Deficit = Expected_Uncertainty - Ensemble_Std
    Positive deficit implies the ensemble is UNDERDISPERSIVE (overconfident),
    which is the classic precursor to NWP forecast busts.
    """
    expected_spread = base_spread_norm * (1.0 + 0.15 * lead_day)
    deficit = expected_spread - ensemble_std
    return deficit


def compute_vertical_wind_shear(
    u_200: np.ndarray,
    u_850: np.ndarray,
) -> np.ndarray:
    """Compute deep-layer vertical zonal wind shear (u200 - u850 in m/s)."""
    return u_200 - u_850


def compute_llj_index(
    u_850: np.ndarray,
    v_850: np.ndarray,
    lats: np.ndarray | None = None,
    lons: np.ndarray | None = None,
) -> float:
    """Low-Level Jet (LLJ) index: mean 850 hPa wind speed over Arabian Sea core.

    Core box: 10-15N, 60-70E. Falls back to domain mean if no coordinates given.
    """
    speed = np.sqrt(np.asarray(u_850) ** 2 + np.asarray(v_850) ** 2)
    if lats is None or lons is None:
        return float(np.nanmean(speed))
    try:
        lat2d, lon2d = np.meshgrid(np.asarray(lats), np.asarray(lons), indexing="ij")
        mask = (lat2d >= 10.0) & (lat2d <= 15.0) & (lon2d >= 60.0) & (lon2d <= 70.0)
        if np.any(mask):
            return float(np.nanmean(speed[mask]))
    except Exception:
        pass
    return float(np.nanmean(speed))


def compute_mslp_gradient_anomaly(
    mslp: np.ndarray,
    lats: np.ndarray | None = None,
    lons: np.ndarray | None = None,
    climatology_gradient: float = 4.0,
) -> float:
    """Monsoon-trough MSLP gradient anomaly (hPa).

    Gradient = mean(North India box 25-30N,75-85E) - mean(Peninsula box 10-18N,75-80E).
    Anomaly = gradient - climatology_gradient. Positive = stronger trough.
    """
    arr = np.asarray(mslp, dtype=float)
    # Normalise to hPa if input looks like Pa
    if np.nanmean(arr) > 50000:
        arr = arr / 100.0
    if lats is None or lons is None:
        grad = float(np.nanstd(arr))
        return grad - climatology_gradient
    try:
        lat2d, lon2d = np.meshgrid(np.asarray(lats), np.asarray(lons), indexing="ij")
        north = (lat2d >= 25.0) & (lat2d <= 30.0) & (lon2d >= 75.0) & (lon2d <= 85.0)
        south = (lat2d >= 10.0) & (lat2d <= 18.0) & (lon2d >= 75.0) & (lon2d <= 80.0)
        if np.any(north) and np.any(south):
            grad = float(np.nanmean(arr[north]) - np.nanmean(arr[south]))
            return grad - climatology_gradient
    except Exception:
        pass
    return float(np.nanstd(arr) - climatology_gradient)


def build_feature_vector(
    lat: float,
    lon: float,
    lead_day: int,
    forecast_precip: float,
    ensemble_mean_precip: float,
    ensemble_std_precip: float,
    spread_deficit: float,
    mfc_850: float,
    temp_2m: float,
    mslp: float,
    wind_shear: float,
    climatological_std: float,
) -> Dict[str, float]:
    """Assemble standardized feature dictionary for one grid cell / region."""
    return {
        "lat": float(lat),
        "lon": float(lon),
        "lead_day": int(lead_day),
        "forecast_precip": float(forecast_precip),
        "ensemble_mean_precip": float(ensemble_mean_precip),
        "ensemble_std_precip": float(ensemble_std_precip),
        "spread_deficit": float(spread_deficit),
        "mfc_850": float(mfc_850),
        "temp_2m_celsius": float(temp_2m - 273.15 if temp_2m > 150 else temp_2m),
        "mslp_hpa": float(mslp / 100.0 if mslp > 50000 else mslp),
        "wind_shear_200_850": float(wind_shear),
        "climatological_std": float(climatological_std),
    }
