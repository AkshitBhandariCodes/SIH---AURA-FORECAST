"""Pilot Benchmark Generator & Model Pre-trainer (SIH26079).

Generates a realistic synoptic pilot dataset representing the July 2019 monsoon
depression episode over Central & Peninsular India, computes physical features and 3D
bust labels, trains and calibrates the classifier, and saves the trained model artifact.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from src.features.synoptic import build_feature_vector
from src.labeling.bust_engine import compute_3d_bust_labels
from src.models.pipeline import ForecastBustClassifier, FEATURE_COLS
from src.preprocessing.grid import IMD_SUBDIVISIONS, CANONICAL_LATS, CANONICAL_LONS


DATA_DIR = Path("data/processed")
MODEL_PATH = DATA_DIR / "model.joblib"


def generate_pilot_monsoon_dataset(num_samples_per_subdiv: int = 150) -> pd.DataFrame:
    """Generate realistic physical feature samples for India monsoon conditions."""
    np.random.seed(42)
    records = []

    subdiv_list = list(IMD_SUBDIVISIONS.values())

    for subdiv in subdiv_list:
        lat_min, lat_max = subdiv.lat_range
        lon_min, lon_max = subdiv.lon_range
        clim_std = subdiv.climatological_error_std

        for _ in range(num_samples_per_subdiv):
            lat = float(np.random.uniform(lat_min, lat_max))
            lon = float(np.random.uniform(lon_min, lon_max))
            lead_day = int(np.random.randint(1, 11))  # Day 1 to Day 10

            # Synoptic simulation: Higher bust probability in active coastal/monsoon zones
            is_depression_zone = subdiv.id in [
                "KONKAN_GOA", "SAURASHTRA_KUTCH", "ODISHA", "VIDARBHA", "COASTAL_KARNATAKA",
                "CHHATTISGARH", "MADHYA_MAHARASHTRA", "JHARKHAND", "MARATHWADA",
            ]

            # Forecast precipitation (mm)
            if is_depression_zone:
                fcst_rain = float(np.random.exponential(scale=35.0))
                # Simulated observation with occasional extreme bust
                if np.random.rand() < (0.15 + 0.03 * lead_day):
                    # Bust case (either catastrophic miss or false alarm)
                    if np.random.rand() < 0.6:
                        obs_rain = fcst_rain + np.random.uniform(60.0, 150.0)  # Type I Miss
                    else:
                        obs_rain = max(0.0, fcst_rain - np.random.uniform(40.0, 90.0))  # Type II False Alarm
                    spread_deficit = float(np.random.uniform(8.0, 25.0))  # High overconfidence!
                    mfc = float(np.random.uniform(0.05, 0.25))            # Strong convergence!
                else:
                    # Normal forecast error
                    obs_rain = max(0.0, fcst_rain + np.random.normal(0, clim_std * 0.5))
                    spread_deficit = float(np.random.normal(0, 4.0))
                    mfc = float(np.random.normal(0.01, 0.03))
            else:
                fcst_rain = float(np.random.exponential(scale=10.0))
                obs_rain = max(0.0, fcst_rain + np.random.normal(0, clim_std * 0.3))
                spread_deficit = float(np.random.normal(-3.0, 3.0))
                mfc = float(np.random.normal(-0.01, 0.02))

            ens_mean = fcst_rain + np.random.normal(0, 3.0)
            ens_std = max(1.0, clim_std * (0.2 + 0.05 * lead_day) - spread_deficit * 0.3)
            temp_2m = 295.0 + np.random.normal(4.0, 3.0)
            mslp = 100400.0 - (1500.0 if is_depression_zone else 0.0) + np.random.normal(0, 300)
            shear = 22.0 if is_depression_zone else np.random.normal(10.0, 5.0)

            # Determine bust label
            abs_err = abs(fcst_rain - obs_rain)
            norm_err = abs_err / (clim_std + 1.0)
            is_bust = int(
                (fcst_rain < 15.5 and obs_rain >= 64.5) or
                (fcst_rain >= 64.5 and obs_rain < 10.0) or
                (norm_err >= 2.2 and abs_err >= 25.0)
            )

            feat = build_feature_vector(
                lat=lat,
                lon=lon,
                lead_day=lead_day,
                forecast_precip=fcst_rain,
                ensemble_mean_precip=ens_mean,
                ensemble_std_precip=ens_std,
                spread_deficit=spread_deficit,
                mfc_850=mfc,
                temp_2m=temp_2m,
                mslp=mslp,
                wind_shear=shear,
                climatological_std=clim_std,
            )
            feat["subdivision"] = subdiv.id
            feat["is_bust"] = is_bust
            feat["observed_precip"] = obs_rain
            feat["abs_error"] = abs_err
            records.append(feat)

    df = pd.DataFrame(records)
    return df


def load_real_training_rows() -> "pd.DataFrame | None":
    """Real GEFS-vs-ERA5 rows (real_pilot_dayN.parquet) mapped to training schema."""
    import glob
    import pandas as pd

    frames = []
    for path in sorted(glob.glob(str(DATA_DIR / "real_pilot_day*.parquet"))):
        rdf = pd.read_parquet(path)
        rdf = rdf.copy()
        rdf["is_bust"] = rdf["is_bust_real"].astype(int)
        frames.append(rdf)
    if not frames:
        return None
    real = pd.concat(frames, ignore_index=True)
    print(f"[Pilot] Blending {len(real)} REAL GEFS/ERA5 rows into training "
          f"({int(real['is_bust'].sum())} real busts).")
    return real


def train_and_export_pilot_model() -> Dict[str, float]:
    """Generate pilot dataset, train calibrated model, and export artifact."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_pilot_monsoon_dataset(num_samples_per_subdiv=180)

    # Blend real truth rows when present — the model then learns real bust
    # patterns (modest spread signals, dry-forecast misses), not just loud
    # synthetic ones. Real rows are truth, never synthetic augmentation.
    real = load_real_training_rows()
    if real is not None:
        use_cols = list(df.columns.intersection(real.columns))
        df = pd.concat([df, real[use_cols]], ignore_index=True)

    # Stratified shuffle split (seeded) — preserves chronological-spirit (no
    # duplicate rows across splits) while avoiding subdivision-ordered leakage
    # where validation would contain zero busts. Strict time-split should be
    # applied on real reforecast years (train 2000-2014 / val 2015-2016).
    df_shuffled = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    train_size = int(len(df_shuffled) * 0.75)
    train_df = df_shuffled.iloc[:train_size].copy()
    val_df = df_shuffled.iloc[train_size:].copy()

    X_train = train_df[FEATURE_COLS]
    y_train = train_df["is_bust"]
    X_val = val_df[FEATURE_COLS]
    y_val = val_df["is_bust"]

    clf = ForecastBustClassifier(random_state=42)
    metrics = clf.train(X_train, y_train, X_val, y_val)

    clf.save(MODEL_PATH)

    # Save benchmark sample parquet
    df.to_parquet(DATA_DIR / "pilot_samples.parquet", index=False)

    print("\n=========================================================")
    print(" ForecastGuard AI — Pilot Model Trained & Exported")
    print("=========================================================")
    print(f"Artifact: {MODEL_PATH}")
    print(f"ROC-AUC:  {metrics['roc_auc']:.3f}")
    print(f"PR-AUC:   {metrics['pr_auc']:.3f}")
    print(f"Brier:    {metrics['brier_score']:.4f}")
    print(f"F1 Score: {metrics['f1']:.3f}")
    print(f"Dataset:  {len(df)} regional samples generated across {df['subdivision'].nunique()} IMD subdivisions.")
    print("=========================================================\n")

    return metrics


if __name__ == "__main__":
    train_and_export_pilot_model()
