"""Canonical spatial grid definitions and IMD meteorological subdivisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np


# Canonical domain bounds over South Asia / India
LAT_MIN, LAT_MAX = 5.0, 40.0
LON_MIN, LON_MAX = 60.0, 100.0
RESOLUTION = 0.25

CANONICAL_LATS = np.arange(LAT_MIN, LAT_MAX + RESOLUTION / 2.0, RESOLUTION)
CANONICAL_LONS = np.arange(LON_MIN, LON_MAX + RESOLUTION / 2.0, RESOLUTION)


@dataclass
class Subdivision:
    name: str
    id: str
    lat_range: Tuple[float, float]
    lon_range: Tuple[float, float]
    climatological_error_std: float  # mm/day standard deviation for normalization


# Major IMD Meteorological Subdivisions frequently vulnerable to busts
IMD_SUBDIVISIONS: Dict[str, Subdivision] = {
    "KONKAN_GOA": Subdivision(
        name="Konkan & Goa",
        id="KONKAN_GOA",
        lat_range=(14.5, 20.2),
        lon_range=(72.5, 74.5),
        climatological_error_std=32.5,
    ),
    "COASTAL_KARNATAKA": Subdivision(
        name="Coastal Karnataka",
        id="COASTAL_KARNATAKA",
        lat_range=(12.5, 15.0),
        lon_range=(74.0, 75.5),
        climatological_error_std=35.0,
    ),
    "SAURASHTRA_KUTCH": Subdivision(
        name="Saurashtra & Kutch",
        id="SAURASHTRA_KUTCH",
        lat_range=(20.5, 24.5),
        lon_range=(68.5, 72.5),
        climatological_error_std=18.0,
    ),
    "GUJARAT_REGION": Subdivision(
        name="Gujarat Region",
        id="GUJARAT_REGION",
        lat_range=(20.5, 24.5),
        lon_range=(72.5, 74.5),
        climatological_error_std=22.0,
    ),
    "ODISHA": Subdivision(
        name="Odisha",
        id="ODISHA",
        lat_range=(17.5, 22.5),
        lon_range=(81.5, 87.5),
        climatological_error_std=26.0,
    ),
    "GANGETIC_WB": Subdivision(
        name="Gangetic West Bengal",
        id="GANGETIC_WB",
        lat_range=(21.5, 24.5),
        lon_range=(86.5, 89.5),
        climatological_error_std=24.5,
    ),
    "VIDARBHA": Subdivision(
        name="Vidarbha",
        id="VIDARBHA",
        lat_range=(19.5, 22.0),
        lon_range=(76.0, 80.5),
        climatological_error_std=20.0,
    ),
    "MARATHWADA": Subdivision(
        name="Marathwada",
        id="MARATHWADA",
        lat_range=(17.5, 20.0),
        lon_range=(74.5, 78.0),
        climatological_error_std=16.5,
    ),
    "EAST_MP": Subdivision(
        name="East Madhya Pradesh",
        id="EAST_MP",
        lat_range=(21.5, 25.0),
        lon_range=(78.5, 83.0),
        climatological_error_std=22.5,
    ),
    "WEST_MP": Subdivision(
        name="West Madhya Pradesh",
        id="WEST_MP",
        lat_range=(21.5, 26.0),
        lon_range=(74.0, 78.5),
        climatological_error_std=19.0,
    ),
    "EAST_RAJASTHAN": Subdivision(
        name="East Rajasthan",
        id="EAST_RAJASTHAN",
        lat_range=(23.5, 28.5),
        lon_range=(73.5, 78.0),
        climatological_error_std=14.0,
    ),
    "WEST_RAJASTHAN": Subdivision(
        name="West Rajasthan",
        id="WEST_RAJASTHAN",
        lat_range=(24.5, 30.5),
        lon_range=(69.5, 75.0),
        climatological_error_std=10.0,
    ),
    "HARYANA_DELHI": Subdivision(
        name="Haryana, Chandigarh & Delhi",
        id="HARYANA_DELHI",
        lat_range=(27.5, 31.0),
        lon_range=(74.5, 77.5),
        climatological_error_std=15.0,
    ),
    "WEST_UP": Subdivision(
        name="West Uttar Pradesh",
        id="WEST_UP",
        lat_range=(26.0, 30.5),
        lon_range=(77.0, 81.0),
        climatological_error_std=16.5,
    ),
    "EAST_UP": Subdivision(
        name="East Uttar Pradesh",
        id="EAST_UP",
        lat_range=(24.5, 28.5),
        lon_range=(81.0, 85.0),
        climatological_error_std=18.5,
    ),
    "TELANGANA": Subdivision(
        name="Telangana",
        id="TELANGANA",
        lat_range=(15.5, 20.0),
        lon_range=(77.0, 81.5),
        climatological_error_std=20.5,
    ),
    "COASTAL_ANDHRA": Subdivision(
        name="Coastal Andhra Pradesh",
        id="COASTAL_ANDHRA",
        lat_range=(13.5, 19.5),
        lon_range=(79.5, 85.0),
        climatological_error_std=23.0,
    ),
    "KERALA": Subdivision(
        name="Kerala & Mahe",
        id="KERALA",
        lat_range=(8.0, 12.8),
        lon_range=(75.0, 77.5),
        climatological_error_std=30.0,
    ),
    # --- Remaining IMD subdivisions: full all-India (36) coverage ---
    "MADHYA_MAHARASHTRA": Subdivision(
        name="Madhya Maharashtra",
        id="MADHYA_MAHARASHTRA",
        lat_range=(15.5, 21.0),
        lon_range=(73.5, 77.0),
        climatological_error_std=18.0,
    ),
    "CHHATTISGARH": Subdivision(
        name="Chhattisgarh",
        id="CHHATTISGARH",
        lat_range=(17.5, 24.0),
        lon_range=(80.0, 84.5),
        climatological_error_std=23.0,
    ),
    "JHARKHAND": Subdivision(
        name="Jharkhand",
        id="JHARKHAND",
        lat_range=(21.5, 25.5),
        lon_range=(83.0, 88.0),
        climatological_error_std=22.0,
    ),
    "BIHAR": Subdivision(
        name="Bihar",
        id="BIHAR",
        lat_range=(24.0, 27.5),
        lon_range=(83.0, 88.5),
        climatological_error_std=21.0,
    ),
    "UTTARAKHAND": Subdivision(
        name="Uttarakhand",
        id="UTTARAKHAND",
        lat_range=(28.5, 31.5),
        lon_range=(77.5, 81.5),
        climatological_error_std=24.0,
    ),
    "PUNJAB": Subdivision(
        name="Punjab",
        id="PUNJAB",
        lat_range=(29.5, 32.5),
        lon_range=(73.5, 77.0),
        climatological_error_std=13.0,
    ),
    "HIMACHAL": Subdivision(
        name="Himachal Pradesh",
        id="HIMACHAL",
        lat_range=(30.0, 33.5),
        lon_range=(75.5, 79.5),
        climatological_error_std=22.0,
    ),
    "JAMMU_KASHMIR_LADAKH": Subdivision(
        name="Jammu, Kashmir & Ladakh",
        id="JAMMU_KASHMIR_LADAKH",
        lat_range=(32.0, 37.0),
        lon_range=(72.5, 80.5),
        climatological_error_std=16.0,
    ),
    "RAYALASEEMA": Subdivision(
        name="Rayalaseema",
        id="RAYALASEEMA",
        lat_range=(12.5, 16.5),
        lon_range=(76.5, 80.5),
        climatological_error_std=17.0,
    ),
    "TAMIL_NADU": Subdivision(
        name="Tamil Nadu, Puducherry & Karaikal",
        id="TAMIL_NADU",
        lat_range=(8.0, 13.5),
        lon_range=(76.0, 80.5),
        climatological_error_std=19.0,
    ),
    "NORTH_KARNATAKA": Subdivision(
        name="North Interior Karnataka",
        id="NORTH_KARNATAKA",
        lat_range=(14.5, 18.5),
        lon_range=(74.0, 78.0),
        climatological_error_std=15.0,
    ),
    "SOUTH_KARNATAKA": Subdivision(
        name="South Interior Karnataka",
        id="SOUTH_KARNATAKA",
        lat_range=(11.5, 15.0),
        lon_range=(74.5, 78.5),
        climatological_error_std=21.0,
    ),
    "ASSAM_MEGHALAYA": Subdivision(
        name="Assam & Meghalaya",
        id="ASSAM_MEGHALAYA",
        lat_range=(24.0, 28.0),
        lon_range=(89.5, 96.0),
        climatological_error_std=30.0,
    ),
    "ARUNACHAL": Subdivision(
        name="Arunachal Pradesh",
        id="ARUNACHAL",
        lat_range=(26.5, 29.5),
        lon_range=(90.5, 97.5),
        climatological_error_std=32.0,
    ),
    "NMMT": Subdivision(
        name="Nagaland, Manipur, Mizoram & Tripura",
        id="NMMT",
        lat_range=(21.5, 27.0),
        lon_range=(91.5, 95.5),
        climatological_error_std=26.0,
    ),
    "SHWB_SIKKIM": Subdivision(
        name="Sub-Himalayan WB & Sikkim",
        id="SHWB_SIKKIM",
        lat_range=(25.5, 28.0),
        lon_range=(87.5, 90.0),
        climatological_error_std=30.0,
    ),
    "ANDAMAN_NICOBAR": Subdivision(
        name="Andaman & Nicobar Islands",
        id="ANDAMAN_NICOBAR",
        lat_range=(6.0, 14.0),
        lon_range=(90.0, 95.0),
        climatological_error_std=30.0,
    ),
    "LAKSHADWEEP": Subdivision(
        name="Lakshadweep",
        id="LAKSHADWEEP",
        lat_range=(8.0, 12.5),
        lon_range=(71.0, 75.0),
        climatological_error_std=28.0,
    ),
}


def get_subdivision_for_point(lat: float, lon: float) -> str:
    """Find the matching IMD subdivision for a given lat/lon point."""
    for sub_id, sub in IMD_SUBDIVISIONS.items():
        if (sub.lat_range[0] <= lat <= sub.lat_range[1]) and (
            sub.lon_range[0] <= lon <= sub.lon_range[1]
        ):
            return sub_id
    return "OTHER_INDIA"


def get_subdivision_climatology(sub_id: str) -> float:
    """Return climatological error std dev for normalization."""
    if sub_id in IMD_SUBDIVISIONS:
        return IMD_SUBDIVISIONS[sub_id].climatological_error_std
    return 20.0  # Default all-India monsoon error standard deviation
