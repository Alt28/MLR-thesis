"""Held-out metrics use raw OLS predictions, including negative values."""
import math
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error


def metrics(actual, predicted):
    mse = float(mean_squared_error(actual, predicted))
    if not math.isfinite(mse):
        raise ValueError("MSE is non-finite; check the recorded values and model conditioning.")
    return {"MSE": mse, "RMSE": math.sqrt(mse)}


def compare_models(actual, predictions):
    baseline = metrics(actual, predictions["Baseline Predicted Waiting Time"])
    enhanced = metrics(actual, predictions["Enhanced Predicted Waiting Time"])
    table = pd.DataFrame([{"Model": "Baseline MLR", **baseline}, {"Model": "Enhanced MLR", **enhanced}])
    differences = pd.DataFrame([
        {"Metric": key, "Baseline minus Enhanced": baseline[key] - enhanced[key],
         "Improvement (%)": (100 * (baseline[key] - enhanced[key]) / baseline[key]) if baseline[key] > 0 else np.nan}
        for key in ("MSE", "RMSE")
    ])
    if np.isclose(baseline["MSE"], enhanced["MSE"], rtol=1e-9, atol=1e-12):
        conclusion = "Both models have effectively equal held-out error in this experiment."
    elif enhanced["MSE"] < baseline["MSE"]:
        conclusion = "Enhanced MLR has lower held-out MSE and RMSE in this experiment."
    else:
        conclusion = "Enhanced MLR has higher held-out MSE and RMSE in this experiment."
    return table, differences, conclusion
