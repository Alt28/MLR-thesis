"""Two ordinary least squares regressions, sharing a training-only design builder."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from .config import TARGET
from .interaction_terms import FeatureBuilder


class MLRModels:
    def __init__(self, config):
        self.config = config

    def fit(self, training, selection="both"):
        if selection not in ("baseline", "enhanced", "both"):
            raise ValueError("Select baseline, enhanced, or both models.")
        self.features = FeatureBuilder(self.config).fit(training)
        self.models = {}
        self.diagnostics = []
        self.warnings = []
        for label, enhanced in [("Baseline MLR", False), ("Enhanced MLR", True)]:
            if selection != "both" and enhanced != (selection == "enhanced"):
                continue
            x = self.features.transform(training, enhanced=enhanced)
            model = LinearRegression().fit(x, training[TARGET])
            self.models[label] = model
            rank = int(model.rank_)
            singular = model.singular_
            condition = float(singular[0] / singular[-1]) if len(singular) and singular[-1] > 0 else None
            self.diagnostics.append({"Model": label, "Training Rows": len(training), "Feature Count": x.shape[1],
                                     "Centered Design Rank": rank, "Residual Degrees of Freedom": len(training) - rank - 1,
                                     "Condition Number": condition})
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

    def predict(self, data):
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
        output["Unseen Categories"] = self.features.unknown_categories(data)
        return output

    def coefficients(self):
        result = []
        for label, model in self.models.items():
            result.append({"Model": label, "Term": "Intercept", "Type": "intercept", "Coefficient": model.intercept_})
            for term, coefficient in zip(model.feature_names_in_, model.coef_):
                factors = self.features.interaction_columns.get(term)
                term_type = "main effect" if factors is None else ("pairwise" if len(factors) == 2 else "higher-order")
                result.append({"Model": label, "Term": term, "Type": term_type, "Coefficient": coefficient})
        return pd.DataFrame(result)
