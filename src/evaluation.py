"""Held-out metrics use raw OLS predictions, including negative values."""
import math
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

METRICS = ("MSE", "RMSE", "MAE", "R2")
LOWER_IS_BETTER = {"MSE": True, "RMSE": True, "MAE": True, "R2": False}


def metrics(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mse = float(mean_squared_error(actual, predicted))
    if not math.isfinite(mse):
        raise ValueError("MSE is non-finite; check the recorded values and model conditioning.")
    # R² is undefined for fewer than two observations or a constant actual wait.
    r2 = float(r2_score(actual, predicted)) if len(actual) >= 2 and np.ptp(actual) > 0 else float("nan")
    return {"MSE": mse, "RMSE": math.sqrt(mse), "MAE": float(mean_absolute_error(actual, predicted)), "R2": r2}


def compare_models(actual, predictions):
    baseline = metrics(actual, predictions["Baseline Predicted Waiting Time"])
    enhanced = metrics(actual, predictions["Enhanced Predicted Waiting Time"])
    table = pd.DataFrame([{"Model": "Baseline MLR", **baseline}, {"Model": "Enhanced MLR", **enhanced}])
    rows = []
    for key in METRICS:
        change = baseline[key] - enhanced[key]
        lower = LOWER_IS_BETTER[key]
        improvement = (100 * change / baseline[key]) if lower and baseline[key] > 0 else np.nan
        better = bool(change > 0) if lower else bool(change < 0)
        rows.append({"Metric": key, "Baseline minus Enhanced": change, "Improvement (%)": improvement,
                     "Better Direction": "lower" if lower else "higher",
                     "Enhanced Better": better if math.isfinite(change) and not np.isclose(change, 0, atol=1e-12) else False})
    differences = pd.DataFrame(rows)
    if np.isclose(baseline["MSE"], enhanced["MSE"], rtol=1e-9, atol=1e-12):
        conclusion = "Both models have effectively equal held-out error in this experiment."
    elif enhanced["MSE"] < baseline["MSE"]:
        conclusion = "Enhanced MLR has lower held-out MSE and RMSE in this experiment."
    else:
        conclusion = "Enhanced MLR has higher held-out MSE and RMSE in this experiment."
    return table, differences, conclusion
