"""Explainability & Natural Language Meteorological Reasoner (SIH26079)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd


METEOROLOGICAL_GLOSSARY = {
    "spread_deficit": {
        "positive": "Severe ensemble underdispersion indicating NWP model is overconfident despite atmospheric volatility.",
        "negative": "Wide ensemble spread acknowledging high chaotic divergence.",
    },
    "mfc_850": {
        "positive": "Strong low-level moisture convergence (850 hPa) capable of triggering unpredicted convection.",
        "negative": "Weak low-level moisture convergence; convective potential suppressed.",
    },
    "lead_day": {
        "positive": "Medium-range predictability decay typical beyond Day 4–5 forecasts.",
        "negative": "Short lead time where model dynamics are typically better constrained.",
    },
    "wind_shear_200_850": {
        "positive": "Strong vertical easterly shear supporting organized mesoscale convective systems.",
        "negative": "Low vertical shear.",
    },
    "forecast_precip": {
        "positive": "Model predicting intense localized deluge susceptible to spatial displacement errors.",
        "negative": "Model predicting dry/light conditions in a humid monsoonal environment.",
    },
    "mslp_hpa": {
        "positive": "Weak pressure gradient.",
        "negative": "Deep localized monsoon depression or low-pressure trough.",
    },
}


class MeteorologicalReasoner:
    """Translates numerical model attributions into operational meteorological diagnostics."""

    def __init__(self, model: Any):
        self.model = model
        # Unwrap calibrated / ensemble wrappers to reach the tree estimator for SHAP.
        self._tree_model = model
        try:
            if model is not None and hasattr(model, "calibrated_classifiers_"):
                cals = getattr(model, "calibrated_classifiers_", [])
                if cals and hasattr(cals[0], "estimator"):
                    self._tree_model = cals[0].estimator
                elif cals and hasattr(cals[0], "base_estimator"):
                    self._tree_model = cals[0].base_estimator
            elif model is not None and hasattr(model, "base_estimator"):
                self._tree_model = model.base_estimator
            elif model is not None and hasattr(model, "estimator"):
                self._tree_model = model.estimator
        except Exception:
            self._tree_model = model

    def _shap_weights(self, features: pd.Series) -> Dict[str, float] | None:
        """Attempt TreeSHAP attribution; return None on any failure (offline-safe)."""
        try:
            import shap  # type: ignore

            background = pd.DataFrame([features])
            explainer = shap.TreeExplainer(self._tree_model)
            vals = explainer.shap_values(background)
            if isinstance(vals, list):
                vals = vals[1] if len(vals) > 1 else vals[0]
            vals = np.asarray(vals).ravel()
            cols = list(background.columns)
            return {c: float(v) for c, v in zip(cols, vals)}
        except Exception:
            return None

    def explain_sample(
        self,
        features: pd.Series,
        top_k: int = 4,
    ) -> Dict[str, Any]:
        """
        Produce top contributing features and plain-English meteorological reasoning.
        """
        # 1) Prefer real TreeSHAP values when the tree model + shap are available.
        shap_weights = self._shap_weights(features)
        if shap_weights:
            ranked = sorted(shap_weights.items(), key=lambda kv: abs(kv[1]), reverse=True)
            top_factors = []
            narratives = []
            for name, w in ranked[:top_k]:
                try:
                    raw = float(features.get(name, 0.0))
                except Exception:
                    raw = 0.0
                sign = "positive" if w >= 0 else "negative"
                # Direction for glossary leans on physical value, not SHAP sign, for key drivers.
                if name in ("spread_deficit", "mfc_850", "wind_shear_200_850",
                            "forecast_precip", "lead_day", "mslp_hpa"):
                    if name == "spread_deficit":
                        sign = "positive" if raw > 0 else "negative"
                    elif name == "mfc_850":
                        sign = "positive" if raw > 0 else "negative"
                    elif name == "lead_day":
                        sign = "positive" if raw >= 4 else "negative"
                    elif name == "wind_shear_200_850":
                        sign = "positive" if raw > 15 else "negative"
                    elif name == "forecast_precip":
                        sign = "positive" if raw > 30 else "negative"
                    elif name == "mslp_hpa":
                        sign = "negative" if raw < 1005 else "positive"
                text = METEOROLOGICAL_GLOSSARY.get(name, {}).get(sign, f"Anomalous {name}")
                narratives.append(text)
                top_factors.append({
                    "feature": name,
                    "importance_weight": round(float(abs(w)), 3),
                    "direction": sign,
                    "scientific_interpretation": text,
                })
            summary_narrative = (
                f"Forecast unreliability is predominantly influenced by: {narratives[0].lower()} "
                f"This is compounded by {narratives[1].lower() if len(narratives) > 1 else 'evolving synoptic uncertainty.'}"
            )
            return {"summary_narrative": summary_narrative, "top_factors": top_factors}

        # 2) Heuristic attribution fallback (offline / no shap installed).
        # Compute baseline relative contributions
        feature_scores: List[Tuple[str, float, str]] = []

        # Heuristic attribution baseline
        spread_def = float(features.get("spread_deficit", 0.0))
        mfc = float(features.get("mfc_850", 0.0))
        lead = float(features.get("lead_day", 1))
        shear = float(features.get("wind_shear_200_850", 0.0))
        fcst_rain = float(features.get("forecast_precip", 0.0))
        mslp = float(features.get("mslp_hpa", 1010.0))

        # Normalized score contributions
        feature_scores.append(("spread_deficit", abs(spread_def) * 1.5, "positive" if spread_def > 0 else "negative"))
        feature_scores.append(("mfc_850", abs(mfc) * 1.2, "positive" if mfc > 0 else "negative"))
        feature_scores.append(("lead_day", (lead / 10.0) * 1.1, "positive" if lead >= 4 else "negative"))
        feature_scores.append(("wind_shear_200_850", abs(shear) * 0.8, "positive" if shear > 15 else "negative"))
        feature_scores.append(("forecast_precip", (fcst_rain / 50.0) * 0.9, "positive" if fcst_rain > 30 else "negative"))

        # Sort by importance magnitude
        feature_scores.sort(key=lambda x: x[1], reverse=True)

        top_factors = []
        narratives = []

        for name, score, sign in feature_scores[:top_k]:
            glossary_entry = METEOROLOGICAL_GLOSSARY.get(name, {})
            text = glossary_entry.get(sign, f"Anomalous {name}")
            narratives.append(text)
            top_factors.append({
                "feature": name,
                "importance_weight": round(float(score), 3),
                "direction": sign,
                "scientific_interpretation": text,
            })

        # Synthesize cohesive diagnostic summary
        summary_narrative = (
            f"Forecast unreliability is predominantly influenced by: {narratives[0].lower()} "
            f"This is compounded by {narratives[1].lower()}"
        )

        return {
            "summary_narrative": summary_narrative,
            "top_factors": top_factors,
        }
