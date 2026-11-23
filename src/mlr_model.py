"""Two ordinary least squares regressions, sharing a training-only design builder."""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from .config import TARGET, SCHEMA_VERSION
from .interaction_terms import FeatureBuilder

INFERENCE_COLUMNS = ["Std. Error", "t Statistic", "p-value", "95% CI Lower", "95% CI Upper"]


def ols_inference(x, y, model):
    """Classical OLS standard errors, t statistics, p-values, and 95% intervals (intercept first)."""
    design = np.column_stack([np.ones(len(x)), x.to_numpy(dtype=float)])
    n, width = design.shape
    rank = np.linalg.matrix_rank(design)
    df = n - rank
    estimates = np.concatenate([[model.intercept_], model.coef_])
    empty = {"Std. Error": np.nan, "t Statistic": np.nan, "p-value": np.nan, "95% CI Lower": np.nan, "95% CI Upper": np.nan}
    if rank < width or df <= 0:
        return [dict(empty) for _ in estimates], df
    residuals = np.asarray(y, dtype=float) - model.predict(x)
    sigma2 = float(residuals @ residuals) / df
    covariance = sigma2 * np.linalg.pinv(design.T @ design)
    errors = np.sqrt(np.clip(np.diag(covariance), 0, None))
    critical = stats.t.ppf(.975, df)
    rows = []
    with np.errstate(divide="ignore", invalid="ignore"):
        for estimate, error in zip(estimates, errors):
            t_value = estimate / error if error > 0 else np.nan
            rows.append({"Std. Error": error, "t Statistic": t_value,
                         "p-value": float(2 * stats.t.sf(abs(t_value), df)) if np.isfinite(t_value) else np.nan,
                         "95% CI Lower": estimate - critical * error, "95% CI Upper": estimate + critical * error})
    return rows, df


def _vif_from_inverse(values):
    """Exact identity VIF_j = [inv(R)]_jj for the correlation matrix R of the non-constant columns.

    One matrix inverse replaces one regression per column (hundreds with station dummies).
    Returns None when R is near-singular, so the per-column regressions decide collinearity.
    """
    keep = np.ptp(values, axis=0) > 0 if len(values) else np.zeros(values.shape[1], bool)
    result = np.full(values.shape[1], np.nan)
    if not keep.any():
        return result
    centered = values[:, keep] - values[:, keep].mean(axis=0)
    scale = np.sqrt((centered ** 2).sum(axis=0))
    corr = (centered / scale).T @ (centered / scale)
    if np.linalg.eigvalsh(corr).min() < 1e-9:
        return None
    result[keep] = np.diag(np.linalg.inv(corr))
    return result


def variance_inflation(x):
    """VIF_j = 1 / (1 - R²_j), regressing column j on the other design columns with an intercept."""
    rows = []
    values = x.to_numpy(dtype=float)
    fast = _vif_from_inverse(values)
    if fast is not None:
        for term, vif in zip(x.columns, fast):
            if np.isnan(vif):
                rows.append({"Term": term, "VIF": np.nan, "Note": "Constant in training data"})
            elif vif >= 1e12:
                rows.append({"Term": term, "VIF": np.nan, "Note": "Perfectly collinear with other terms"})
            else:
                rows.append({"Term": term, "VIF": vif, "Note": "High (> 10)" if vif > 10 else "Moderate (5–10)" if vif > 5 else ""})
        return rows
    for j, term in enumerate(x.columns):
        target = values[:, j]
        if np.ptp(target) == 0:
            rows.append({"Term": term, "VIF": np.nan, "Note": "Constant in training data"})
            continue
        others = np.column_stack([np.ones(len(values)), np.delete(values, j, axis=1)])
        fitted = others @ np.linalg.lstsq(others, target, rcond=None)[0]
        r2 = 1 - np.sum((target - fitted) ** 2) / np.sum((target - target.mean()) ** 2)
        if r2 >= 1 - 1e-12:
            rows.append({"Term": term, "VIF": np.nan, "Note": "Perfectly collinear with other terms"})
        else:
            vif = 1 / (1 - r2)
            rows.append({"Term": term, "VIF": vif, "Note": "High (> 10)" if vif > 10 else "Moderate (5–10)" if vif > 5 else ""})
    return rows


class MLRModels:
    def __init__(self, config):
        self.config = config

    def fit(self, training, selection="both", inference=True):
        self.schema_version = SCHEMA_VERSION
        if selection not in ("baseline", "enhanced", "both"):
            raise ValueError("Select baseline, enhanced, or both models.")
        self.features = FeatureBuilder(self.config).fit(training)
        self.models = {}
        self.diagnostics = []
        self.warnings = []
        self.inference = {}
        self.vif = {}
        for label, enhanced in [("Baseline MLR", False), ("Enhanced MLR", True)]:
            if selection != "both" and enhanced != (selection == "enhanced"):
                continue
            x = self.features.transform(training, enhanced=enhanced)
            model = LinearRegression().fit(x, training[TARGET])
            self.models[label] = model
            rank = int(model.rank_)
            singular = model.singular_
            condition = float(singular[0] / singular[-1]) if len(singular) and singular[-1] > 0 else None
            diagnostic = {"Model": label, "Training Rows": len(training), "Feature Count": x.shape[1],
                          "Centered Design Rank": rank, "Residual Degrees of Freedom": len(training) - rank - 1,
                          "Condition Number": condition,
                          "Interaction Factors Centered": bool(enhanced and getattr(self.features, "centers", {}))}
            if inference:
                self.inference[label], _ = ols_inference(x, training[TARGET], model)
                self.vif[label] = variance_inflation(x)
                finite = [row["VIF"] for row in self.vif[label] if np.isfinite(row["VIF"])]
                diagnostic["Maximum VIF"] = max(finite) if finite else None
                if any(v > 10 for v in finite):
                    self.warnings.append(f"{label}: at least one term has VIF above 10; individual coefficients are imprecise even if predictions are stable.")
            self.diagnostics.append(diagnostic)
            if rank < x.shape[1]:
                self.warnings.append(f"{label}: rank-deficient design; coefficients are not uniquely identifiable.")
            if len(training) <= x.shape[1] + 1:
                self.warnings.append(f"{label}: too few training rows relative to the feature count for reliable interpretation.")
            if condition is None or condition > 1e8:
                self.warnings.append(f"{label}: poorly conditioned design; coefficient estimates may be unstable.")
        for col, categories in self.features.categories.items():
            if len(categories) == 1:
                self.warnings.append(f"{col}: only one training category, so its contrast and corresponding interactions cannot be estimated.")
        return self

    def predict(self, data, strict_categories=False):
        if getattr(self, "schema_version", None) != SCHEMA_VERSION:
            raise ValueError("Incompatible saved model schema. Train new models using the current six predictors.")
        unknown = self.features.unknown_categories(data)
        if strict_categories and unknown.ne("").any():
            raise ValueError("Unseen station or category: " + "; ".join(unknown[unknown.ne("")].unique()[:5]) +
                             ". This model has no fitted contrast for these values. Use a model trained on these stations/categories or retrain with recorded waits.")
        output = pd.DataFrame(index=data.index)
        for label, enhanced, prefix in [("Baseline MLR", False, "Baseline"), ("Enhanced MLR", True, "Enhanced")]:
            if label not in self.models:
                continue
            prediction = self.models[label].predict(self.features.transform(data, enhanced))
            if not np.isfinite(prediction).all():
                raise ValueError("Model produced non-finite predictions.")
            output[f"{prefix} Predicted Waiting Time"] = prediction
            output[f"{prefix} Negative Prediction"] = prediction < 0
            if TARGET in data:
                output[f"{prefix} Error (actual - predicted)"] = data[TARGET] - prediction
        output["Unseen Categories"] = unknown
        return output

    def coefficients(self):
        result = []
        inference = getattr(self, "inference", {})
        added = getattr(self.features, "hierarchy_columns", set())
        for label, model in self.models.items():
            rows = [{"Model": label, "Term": "Intercept", "Type": "intercept", "Added for Hierarchy": False, "Coefficient": model.intercept_}]
            for term, coefficient in zip(model.feature_names_in_, model.coef_):
                factors = self.features.interaction_columns.get(term)
                term_type = "main effect" if factors is None else ("pairwise" if len(factors) == 2 else "higher-order")
                rows.append({"Model": label, "Term": term, "Type": term_type, "Added for Hierarchy": term in added,
                             "Coefficient": coefficient})
            for row, extra in zip(rows, inference.get(label, [{}] * len(rows))):
                row.update({column: extra.get(column, np.nan) for column in INFERENCE_COLUMNS})
            result.extend(rows)
        return pd.DataFrame(result, columns=["Model", "Term", "Type", "Added for Hierarchy", "Coefficient", *INFERENCE_COLUMNS])

    def vif_table(self):
        vif = getattr(self, "vif", {})
        return pd.DataFrame([{"Model": label, **row} for label in self.models for row in vif.get(label, [])],
                            columns=["Model", "Term", "VIF", "Note"])
