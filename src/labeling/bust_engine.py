"""3-Dimensional Forecast Bust Labeling Engine (SIH26079)."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Tuple
import numpy as np
from scipy.ndimage import maximum_filter


class BustType(str, Enum):
    NONE = "NO_BUST"
    TYPE_I_MISS = "TYPE_I_MISS"            # Model predicted light/dry, but extreme rain occurred (High risk)
    TYPE_II_FALSE_ALARM = "TYPE_II_FALSE_ALARM"  # Model predicted extreme storm, but nothing occurred
    INTENSITY_BUST = "INTENSITY_BUST"      # 90th percentile normalized error exceeded
    DISPLACEMENT_ERROR = "DISPLACEMENT"    # Event happened within immediate spatial neighborhood


# Official IMD rainfall classification thresholds (mm / 24 hours)
IMD_LIGHT_RAIN_MAX = 15.5       # mm/day
IMD_HEAVY_RAIN_MIN = 64.5       # mm/day
IMD_VERY_HEAVY_MIN = 115.5      # mm/day

# Default 90th percentile normalized absolute error cutoff
DEFAULT_NORMALIZED_PERCENTILE_THRESHOLD = 2.2  # ~90th percentile in z-score equivalent


def compute_3d_bust_labels(
    forecast_rain: np.ndarray,      # 2D array (lat, lon) in mm/day
    observed_rain: np.ndarray,      # 2D array (lat, lon) in mm/day
    climatological_std: np.ndarray, # 2D array of local error std dev
    neighborhood_size: int = 3,     # 3x3 grid cells (~75 km anti-double-penalty window)
    nae_threshold: float = DEFAULT_NORMALIZED_PERCENTILE_THRESHOLD,
) -> Dict[str, np.ndarray]:
    """
    Compute comprehensive 3D bust labels across spatial grids.
    
    Returns:
        dict with:
            - is_bust: bool 2D array (True if catastrophic failure)
            - bust_type: string 2D array indicating failure category
            - raw_error: forecast - observed (mm)
            - abs_error: |forecast - observed| (mm)
            - normalized_error: abs_error / (climatological_std + 1.0)
    """
    raw_error = forecast_rain - observed_rain
    abs_error = np.abs(raw_error)
    normalized_error = abs_error / (climatological_std + 1.0)

    # Neighborhood peak observation (to detect displacement vs complete miss)
    obs_neighborhood_max = maximum_filter(observed_rain, size=neighborhood_size)
    fcst_neighborhood_max = maximum_filter(forecast_rain, size=neighborhood_size)

    shape = forecast_rain.shape
    is_bust = np.zeros(shape, dtype=bool)
    bust_type = np.full(shape, BustType.NONE.value, dtype=object)

    for i in range(shape[0]):
        for j in range(shape[1]):
            fc = forecast_rain[i, j]
            obs = observed_rain[i, j]
            nae = normalized_error[i, j]

            # 1. Check for Type I Disaster Miss (Forecast light/dry, Observed heavy/deluge)
            if fc < IMD_LIGHT_RAIN_MAX and obs >= IMD_HEAVY_RAIN_MIN:
                # Check if it was merely displaced from an adjacent cell
                if fcst_neighborhood_max[i, j] >= IMD_HEAVY_RAIN_MIN:
                    bust_type[i, j] = BustType.DISPLACEMENT_ERROR.value
                    # Displacement is a warning but not a total operational blindspot
                    is_bust[i, j] = False
                else:
                    bust_type[i, j] = BustType.TYPE_I_MISS.value
                    is_bust[i, j] = True
                continue

            # 2. Check for Type II False Alarm (Forecast heavy storm, Observed dry)
            if fc >= IMD_HEAVY_RAIN_MIN and obs < 10.0:
                if obs_neighborhood_max[i, j] >= IMD_HEAVY_RAIN_MIN:
                    bust_type[i, j] = BustType.DISPLACEMENT_ERROR.value
                    is_bust[i, j] = False
                else:
                    bust_type[i, j] = BustType.TYPE_II_FALSE_ALARM.value
                    is_bust[i, j] = True
                continue

            # 3. Check for Statistical Normalized Intensity Bust
            if nae >= nae_threshold and abs_error[i, j] >= 25.0:
                bust_type[i, j] = BustType.INTENSITY_BUST.value
                is_bust[i, j] = True

    return {
        "is_bust": is_bust,
        "bust_type": bust_type,
        "raw_error": raw_error,
        "abs_error": abs_error,
        "normalized_error": normalized_error,
    }
