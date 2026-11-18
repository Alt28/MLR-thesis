"""Seven-factor classification fitted exclusively on reviewed training data."""
import math
import numpy as np
import pandas as pd
from scipy import stats
from .config import CATEGORICAL, NUMERICAL, PREDICTORS, TARGET, LABELS

CLASSIFICATION_VERSION = 3
INSUFFICIENT = "Insufficient Variation for Classification"
UNDEFINED = "Requires Researcher Decision"
NO_EFFECT = "No detectable adjusted effect"
EFFECT_ALPHA = 0.05
# Both measured predictors need a documented unit before any station label is issued.
REQUIRED_UNITS = {"Vehicle Frequency": "vehicle_frequency_unit", "Route Distance": "route_distance_unit"}
SEVERITIES = ("Normal", "Minor", "Moderate", "Severe")
# Numerical-resolution safeguards, not statistical significance tests.
VARIATION_RTOL = 1e-9
VARIATION_ATOL = 1e-12
CORRELATION_ZERO_TOLERANCE = 1e-12


def numerical_severity(values, quartiles, direction="higher"):
    if direction not in ("higher", "lower"):
        raise ValueError("Numerical severity direction must be higher or lower.")
    scores = np.searchsorted(np.asarray(quartiles, dtype=float), np.asarray(values, dtype=float), side="left")
    return scores if direction == "higher" else 3 - scores


def waiting_time_severity(predictions, thresholds=(15, 20, 25)):
    return np.searchsorted(thresholds, np.maximum(0, predictions), side="left")


def station_label(score, thresholds=(.75, 1.5, 2.25)):
    if not np.isfinite(score) or not 0 <= score <= 3:
        raise ValueError("Combined station score must be finite and between 0 and 3.")
    return LABELS[np.searchsorted(thresholds, score, side="right")]


def aggregate_station_scores(predictions, thresholds=(.75, 1.5, 2.25), station_column="Station ID"):
    columns = ["Station ID", "Test Records", "Classifiable Records", "Unresolved Records",
               "Mean Multi-Factor Station Score", "Overall Station Classification"]
    station_names = {station_column.lower(), "station"}
    source_column = next((column for column in predictions.columns
                          if str(column).strip().lower() in station_names), None)
    if source_column is None:
        return pd.DataFrame(columns=columns), {
            "available": False, "grouping_column": station_column,
            "reason": f"Add a {station_column} column to enable station-level summaries.",
            "station_count": 0, "ungrouped_records": len(predictions),
        }

    identifiers = predictions[source_column]
    has_identifier = identifiers.notna() & identifiers.astype(str).str.strip().ne("")
    grouped = pd.DataFrame({
        "Station ID": identifiers.loc[has_identifier].astype(str).str.strip(),
        "Multi-Factor Station Score": pd.to_numeric(
            predictions.loc[has_identifier, "Multi-Factor Station Score"], errors="coerce"),
    })
    if grouped.empty:
        return pd.DataFrame(columns=columns), {
            "available": False, "grouping_column": source_column,
            "reason": f"No test observations have a nonempty {source_column} value.",
            "station_count": 0, "ungrouped_records": len(predictions),
        }

    summary = grouped.groupby("Station ID", sort=True).agg(
        **{
            "Test Records": ("Multi-Factor Station Score", "size"),
            "Classifiable Records": ("Multi-Factor Station Score", "count"),
            "Mean Multi-Factor Station Score": ("Multi-Factor Station Score", "mean"),
        }
    ).reset_index()
    summary["Unresolved Records"] = summary["Test Records"] - summary["Classifiable Records"]
    summary["Overall Station Classification"] = summary["Mean Multi-Factor Station Score"].map(
        lambda score: station_label(score, thresholds) if pd.notna(score) else "Pending configuration")
    summary = summary[columns]
    return summary, {
        "available": True, "grouping_column": source_column, "reason": None,
        "station_count": len(summary), "ungrouped_records": int((~has_identifier).sum()),
        "aggregation": "Mean of classifiable held-out observation scores per station; unresolved records are counted, not scored.",
    }


def category_evidence(training):
    frames = []
    for col in CATEGORICAL:
        grouped = training.groupby(col, sort=True)[TARGET].agg(["count", "mean", "median"])
        grouped.index.name = "Category"
        grouped = grouped.reset_index().rename(columns={"count": "Training Count", "mean": "Mean Actual Wait", "median": "Median Actual Wait"})
        grouped.insert(0, "Factor", col)
        frames.append(grouped)
    return pd.concat(frames, ignore_index=True)


def variation_status(values, quartiles):
    values = np.asarray(values, dtype=float)
    quartiles = np.asarray(quartiles, dtype=float)
    if not len(values) or not np.isfinite(values).all() or not np.isfinite(quartiles).all():
        return INSUFFICIENT
    tolerance = VARIATION_ATOL + VARIATION_RTOL * float(np.max(np.abs(values)))
    if len(np.unique(values)) < 2 or np.ptp(values) <= tolerance:
        return INSUFFICIENT
    q_tolerance = VARIATION_ATOL + VARIATION_RTOL * float(np.max(np.abs(quartiles)))
    return INSUFFICIENT if np.ptp(quartiles) <= q_tolerance else "Valid"


def adjusted_effects(training, config):
    """Additive OLS on reviewed training rows: each factor's effect with the other five held constant.

    Returns per-factor coefficients (minutes) and a partial F-test p-value, or a reason when the fit is unusable.
    """
    from .interaction_terms import FeatureBuilder
    try:
        builder = FeatureBuilder(config).fit(training)
        x = builder.transform(training)
    except ValueError as exc:
        return {"available": False, "reason": str(exc), "factors": {}}
    design = np.column_stack([np.ones(len(x)), x.to_numpy(dtype=float)])
    y = training[TARGET].to_numpy(dtype=float)
    n, k = design.shape
    if np.linalg.matrix_rank(design) < k or n - k <= 0:
        return {"available": False, "reason": "The additive design is rank-deficient or has too few training rows.", "factors": {}}
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    rss = float(np.sum((y - design @ beta) ** 2))
    df = n - k
    columns = list(x.columns)
    factors = {}
    for col in PREDICTORS:
        names = builder.blocks[col]
        if not names:
            continue
        positions = [1 + columns.index(name) for name in names]
        reduced = np.delete(design, positions, axis=1)
        reduced_rss = float(np.sum((y - reduced @ np.linalg.lstsq(reduced, y, rcond=None)[0]) ** 2))
        gain = max(reduced_rss - rss, 0.0)
        if rss > 0:
            p_value = float(stats.f.sf((gain / len(names)) / (rss / df), len(names), df))
        else:
            p_value = 0.0 if gain > 0 else 1.0
        if col in NUMERICAL:
            factors[col] = {"coefficient": float(beta[positions[0]]), "p_value": p_value}
        else:
            effects = {builder.categories[col][0]: 0.0}
            effects.update({category: float(beta[p]) for category, p in zip(builder.categories[col][1:], positions)})
            factors[col] = {"effects": effects, "p_value": p_value}
    return {"available": True, "reason": None, "factors": factors, "residual_df": df}


def scaled_score(effect, low, high):
    """0 for the most favourable category, 3 for the least, proportional (rounded half up) in between."""
    if high - low <= 0:
        return 0
    return int(min(3, math.floor(3 * (effect - low) / (high - low) + 0.5)))


class StationClassifier:
    def __init__(self, config):
        self.config = config

    def undeclared_units(self):
        """Factors whose measurement unit has not been documented for this experiment."""
        return [factor for factor, field in REQUIRED_UNITS.items()
                if not str(getattr(self.config, field, "")).strip()]

    def fit(self, training):
        self.config.validate()
        self.method_version = CLASSIFICATION_VERSION
        self.thresholds = training[list(NUMERICAL)].quantile([.25, .5, .75], interpolation="linear").T
        self.thresholds.columns = ["Q1", "Q2", "Q3"]
        self.thresholds.index.name = "Factor"
        self.target_quartiles = training[TARGET].quantile([.25, .5, .75], interpolation="linear").to_numpy(dtype=float)
        self.target_status = variation_status(training[TARGET], self.target_quartiles)
        self.basis = getattr(self.config, "severity_basis", "adjusted")
        self.adjusted = (adjusted_effects(training, self.config) if self.basis == "adjusted" and self.target_status == "Valid"
                         else {"available": False, "reason": "Marginal basis selected." if self.basis == "marginal"
                               else "Actual waiting time has insufficient variation.", "factors": {}})
        adjusted_factors = self.adjusted["factors"] if self.adjusted["available"] else {}
        self.directions = {}
        self.factor_status = {}
        self.no_effect = set()
        for col in NUMERICAL:
            q = self.thresholds.loc[col, ["Q1", "Q2", "Q3"]].to_numpy(dtype=float)
            status = variation_status(training[col], q)
            correlation = None
            if status == "Valid" and self.target_status == "Valid":
                candidate = float(training[col].corr(training[TARGET]))
                if np.isfinite(candidate): correlation = candidate
            configured = self.config.numerical_directions.get(col)
            direction = configured
            adjusted = adjusted_factors.get(col)
            if configured:
                source = "Researcher configuration"
            elif adjusted is not None and status == "Valid":
                if adjusted["p_value"] >= EFFECT_ALPHA:
                    source = f"{NO_EFFECT} (p = {adjusted['p_value']:.3g}); every value scores 0"
                    self.no_effect.add(col)
                else:
                    source = "Adjusted MLR coefficient (other factors held constant)"
                    direction = "higher" if adjusted["coefficient"] > 0 else "lower"
            else:
                source = "Training Pearson correlation"
                if correlation is not None and abs(correlation) > CORRELATION_ZERO_TOLERANCE:
                    direction = "higher" if correlation > 0 else "lower"
            if status == "Valid" and direction is None and col not in self.no_effect:
                status = UNDEFINED
            # Even a configured direction cannot make constant quartiles meaningful.
            self.directions[col] = direction if status == "Valid" else None
            if status != "Valid":
                self.no_effect.discard(col)
            self.factor_status[col] = status
            self.thresholds.loc[col, "Direction"] = self.directions[col]
            self.thresholds.loc[col, "Configured Direction"] = configured
            self.thresholds.loc[col, "Direction Source"] = source
            self.thresholds.loc[col, "Adjusted MLR Coefficient"] = adjusted["coefficient"] if adjusted else None
            self.thresholds.loc[col, "Adjusted Effect p-value"] = adjusted["p_value"] if adjusted else None
            self.thresholds.loc[col, "Training Pearson Correlation"] = correlation
            self.thresholds.loc[col, "Status"] = status
            self.thresholds.loc[col, "Training Unique Values"] = training[col].nunique()
        distance_correlation = self.thresholds.loc["Route Distance", "Training Pearson Correlation"]
        self.distance_correlation = float(distance_correlation) if pd.notna(distance_correlation) else None
        self.category_mappings = {col: {} for col in CATEGORICAL}
        self.evidence = category_evidence(training)
        rows = self.evidence.to_dict(orient="records")
        # Include explicitly configured categories absent from training, without fabricating evidence.
        for col in CATEGORICAL:
            seen = set(training[col])
            for category in self.config.category_severity.get(col, {}):
                if category not in seen:
                    rows.append({"Factor": col, "Category": category, "Training Count": 0,
                                 "Mean Actual Wait": None, "Median Actual Wait": None})
        for row in rows:
            col, category = row["Factor"], row["Category"]
            override = self.config.category_severity.get(col, {}).get(category)
            adjusted = adjusted_factors.get(col)
            effect = p_value = None
            usable = row["Training Count"] and self.target_status == "Valid" and training[col].nunique() > 1
            if adjusted is not None and usable and category in adjusted["effects"]:
                effects = adjusted["effects"]
                low, high = min(effects.values()), max(effects.values())
                effect, p_value = effects[category] - low, adjusted["p_value"]
                no_effect = p_value >= EFFECT_ALPHA
                derived = 0 if no_effect else scaled_score(effects[category], low, high)
                derived_source = (f"{NO_EFFECT} (p = {p_value:.3g})" if no_effect
                                  else "Adjusted MLR effect (other factors held constant)")
            else:
                derived = int(numerical_severity([row["Mean Actual Wait"]], self.target_quartiles)[0]) if usable else None
                derived_source = "Training category mean"
            score, status = override if override is not None else derived, "Valid"
            source = "Researcher configuration" if override is not None else derived_source
            if score is None: status = INSUFFICIENT
            if score is not None: self.category_mappings[col][category] = score
            row.update({"Q1": self.target_quartiles[0], "Q2": self.target_quartiles[1], "Q3": self.target_quartiles[2],
                        "Threshold Variable": TARGET, "Direction": "higher", "Mapping Source": source,
                        "Adjusted Effect vs Most Favourable (min)": effect, "Adjusted Effect p-value": p_value,
                        "Status": status, "Severity Score": score, "Derived Severity Score": derived,
                        "Severity": SEVERITIES[score] if score is not None else status})
        self.evidence = pd.DataFrame(rows)
        self.rule_metadata = {
            "classification_version": self.method_version, "training_rows": len(training),
            "quartile_source": "reviewed training data only", "quantile_interpolation": "linear",
            "actual_wait_quartiles": dict(zip(("Q1", "Q2", "Q3"), self.target_quartiles.tolist())),
            "actual_wait_variation_status": self.target_status,
            "category_mappings": self.category_mappings, "numerical_directions": self.directions,
            "severity_basis": self.basis,
            "adjusted_model": {"available": self.adjusted["available"], "reason": self.adjusted["reason"],
                               "effect_alpha": EFFECT_ALPHA,
                               "factor_p_values": {c: f["p_value"] for c, f in adjusted_factors.items()},
                               "no_detectable_effect": sorted(self.no_effect | {
                                   c for c, f in adjusted_factors.items() if c in CATEGORICAL and f["p_value"] >= EFFECT_ALPHA})},
            "direction_method": ("Configured direction takes precedence; otherwise the sign of the additive OLS coefficient "
                                 "(other factors held constant). A factor whose partial F-test p-value is at least "
                                 f"{EFFECT_ALPHA} has no detectable effect and scores 0. Falls back to the training Pearson "
                                 "correlation sign when the additive fit is unavailable or the marginal basis is selected."),
            "variation_relative_tolerance": VARIATION_RTOL, "variation_absolute_tolerance": VARIATION_ATOL,
            "correlation_zero_tolerance": CORRELATION_ZERO_TOLERANCE,
            "measurement_units": {factor: str(getattr(self.config, field, "")).strip()
                                  for factor, field in REQUIRED_UNITS.items()},
            "wait_thresholds": list(self.config.wait_thresholds), "station_thresholds": list(self.config.station_thresholds),
        }
        return self

    def classify(self, observations, predicted_wait):
        predictions = np.asarray(predicted_wait, dtype=float)
        if len(predictions) != len(observations) or not np.isfinite(predictions).all():
            raise ValueError("Classification requires one finite predicted wait per observation.")
        output = pd.DataFrame(index=observations.index)
        for col in CATEGORICAL:
            evidence = self.evidence[self.evidence.Factor.eq(col)].set_index("Category")
            output[f"{col} Severity"] = observations[col].map(self.category_mappings[col]).astype(float)
            output[f"{col} Classification Status"] = observations[col].map(evidence.Status).fillna(UNDEFINED)
            output[f"{col} Category Mean"] = observations[col].map(evidence["Mean Actual Wait"])
        for col in NUMERICAL:
            direction = self.directions[col]
            if col in getattr(self, "no_effect", set()):
                output[f"{col} Severity"] = 0.0
            else:
                output[f"{col} Severity"] = (
                    numerical_severity(observations[col], self.thresholds.loc[col, ["Q1", "Q2", "Q3"]], direction)
                    if direction else np.nan)
            output[f"{col} Classification Status"] = self.factor_status[col]
        output["Waiting Time Used for Classification"] = np.maximum(0, predictions)
        output["Predicted Waiting Time Severity"] = waiting_time_severity(predictions, self.config.wait_thresholds)
        output["Predicted Waiting Time Classification Status"] = "Valid"
        severity_columns = [f"{c} Severity" for c in PREDICTORS] + ["Predicted Waiting Time Severity"]
        complete = output[severity_columns].notna().all(axis=1)
        undeclared = self.undeclared_units()
        if undeclared: complete[:] = False
        output["Multi-Factor Station Score"] = output[severity_columns].sum(axis=1, min_count=7).div(7).where(complete)
        output["Overall Station Classification"] = output["Multi-Factor Station Score"].map(
            lambda score: station_label(score, self.config.station_thresholds) if pd.notna(score) else "Pending configuration")
        reasons = []
        for rid in observations.index:
            missing = [f"{col}: {output.at[rid, col + ' Classification Status']}" for col in PREDICTORS
                       if pd.isna(output.at[rid, col + " Severity"])]
            missing.extend(f"{factor} unit: {UNDEFINED}" for factor in undeclared)
            reasons.append("; ".join(missing))
        output["Missing Classification Definitions"] = reasons
        return output
