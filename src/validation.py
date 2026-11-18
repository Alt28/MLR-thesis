"""Statistical checks of the comparison and of the station classification.

These describe variability within the supplied dataset only. They never use the held-out test rows
for fitting, and none of them establishes real-world validity of the models or thresholds.
"""
import math
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import cohen_kappa_score
from sklearn.model_selection import RepeatedKFold
from .config import LABELS, TARGET
from .data_loader import resolve_group_column
from .evaluation import METRICS, LOWER_IS_BETTER, metrics
from .mlr_model import MLRModels

ALPHA = 0.05
PENDING = "Pending configuration"


def _verdict(p_value, mean_difference, second):
    if not math.isfinite(p_value):
        return "Test not applicable"
    direction = f"{second} lower error" if mean_difference > 0 else f"{second} higher error"
    if p_value < ALPHA:
        return f"Statistically significant at α = {ALPHA} ({direction})"
    return f"Not statistically significant at α = {ALPHA}"


def paired_error_tests(actual, predictions, pairs):
    """Wilcoxon signed-rank and paired t-tests on per-observation squared errors of two arms."""
    actual = np.asarray(actual, dtype=float)
    rows = []
    for first, second, question, first_column, second_column in pairs:
        first_error = (actual - np.asarray(predictions[first_column], dtype=float)) ** 2
        second_error = (actual - np.asarray(predictions[second_column], dtype=float)) ** 2
        difference = first_error - second_error
        identical = np.allclose(difference, 0, atol=1e-12)
        base = {"Comparison": f"{first} vs {second}", "Question": question, "Observations": len(difference),
                "Mean Squared-Error Difference (first − second)": float(difference.mean()),
                "Median Squared-Error Difference (first − second)": float(np.median(difference))}
        for test in ("Wilcoxon signed-rank", "Paired t-test"):
            statistic, p_value = np.nan, np.nan
            if not identical and len(difference) >= 2:
                try:
                    outcome = (stats.wilcoxon(first_error, second_error) if test.startswith("Wilcoxon")
                               else stats.ttest_rel(first_error, second_error))
                    statistic, p_value = float(outcome.statistic), float(outcome.pvalue)
                except ValueError:
                    pass
            result = "Identical predictions; no difference to test" if identical else _verdict(
                p_value, base["Mean Squared-Error Difference (first − second)"], second)
            rows.append({**base, "Test": test, "Statistic": statistic, "p-value": p_value, "Result": result})
    return pd.DataFrame(rows)


def _fold_splits(training, config):
    """Yield (repeat, fold, train positions, validation positions); grouped designs keep groups together."""
    folds, repeats, seed = config.cv_folds, config.cv_repeats, config.random_state
    if config.split_method == "grouped":
        column = resolve_group_column(training, config)
        groups = training[column].astype(str).str.strip().to_numpy()
        unique = np.unique(groups)
        folds = min(folds, len(unique))
        if folds < 2:
            raise ValueError(f"Cross-validation needs at least two {column} groups in the training partition.")
        for repeat in range(repeats):
            shuffled = np.random.default_rng(seed + repeat).permutation(unique)
            for fold, chunk in enumerate(np.array_split(shuffled, folds), 1):
                validation = np.isin(groups, chunk)
                yield repeat + 1, fold, np.flatnonzero(~validation), np.flatnonzero(validation)
        return
    folds = min(folds, len(training))
    splitter = RepeatedKFold(n_splits=folds, n_repeats=repeats, random_state=seed)
    for i, (train_rows, validation_rows) in enumerate(splitter.split(training)):
        yield i // folds + 1, i % folds + 1, train_rows, validation_rows


def corrected_resampled_ttest(differences, train_rows, validation_rows):
    """Nadeau & Bengio (2003) t-test for repeated cross-validation, correcting for overlapping training sets."""
    d = np.asarray(differences, dtype=float)
    count = len(d)
    if count < 2:
        return np.nan, np.nan, count - 1
    variance = d.var(ddof=1)
    ratio = float(np.mean(validation_rows)) / float(np.mean(train_rows))
    if variance <= 0:
        return np.nan, (1.0 if np.isclose(d.mean(), 0) else np.nan), count - 1
    t_value = d.mean() / math.sqrt((1 / count + ratio) * variance)
    return float(t_value), float(2 * stats.t.sf(abs(t_value), count - 1)), count - 1


def cross_validate(training, config):
    """Repeated k-fold comparison of Baseline (B) and Enhanced (C) MLR within the reviewed training partition."""
    rows, failures = [], []
    for repeat, fold, train_rows, validation_rows in _fold_splits(training, config):
        fold_train, fold_validation = training.iloc[train_rows], training.iloc[validation_rows]
        try:
            fitted = MLRModels(config).fit(fold_train, inference=False)
            predicted = fitted.predict(fold_validation)
            row = {"Repeat": repeat, "Fold": fold, "Training Rows": len(fold_train), "Validation Rows": len(fold_validation)}
            for prefix in ("Baseline", "Enhanced"):
                for key, value in metrics(fold_validation[TARGET], predicted[f"{prefix} Predicted Waiting Time"]).items():
                    row[f"{prefix} {key}"] = value
            row["MSE Difference (Baseline − Enhanced)"] = row["Baseline MSE"] - row["Enhanced MSE"]
            rows.append(row)
        except ValueError as exc:
            failures.append(f"repeat {repeat}, fold {fold}: {exc}")
    folds = pd.DataFrame(rows)
    if folds.empty:
        raise ValueError("No cross-validation fold could be fitted. " + "; ".join(failures[:3]))
    summary = []
    for key in METRICS:
        base, enhanced = folds[f"Baseline {key}"], folds[f"Enhanced {key}"]
        valid = base.notna() & enhanced.notna()
        better = (enhanced[valid] < base[valid]) if LOWER_IS_BETTER[key] else (enhanced[valid] > base[valid])
        summary.append({"Metric": key, "Better Direction": "lower" if LOWER_IS_BETTER[key] else "higher",
                        "Baseline Mean": base.mean(), "Baseline SD": base.std(ddof=1),
                        "Enhanced Mean": enhanced.mean(), "Enhanced SD": enhanced.std(ddof=1),
                        "Mean Difference (Baseline − Enhanced)": (base - enhanced).mean(),
                        "Folds Where Enhanced Is Better (%)": 100 * better.mean() if valid.any() else np.nan})
    t_value, p_value, df = corrected_resampled_ttest(folds["MSE Difference (Baseline − Enhanced)"],
                                                     folds["Training Rows"], folds["Validation Rows"])
    mean_difference = folds["MSE Difference (Baseline − Enhanced)"].mean()
    test = pd.DataFrame([{
        "Comparison": "B vs C (Baseline vs Enhanced MLR)", "Test": "Corrected resampled t-test (Nadeau & Bengio, 2003)",
        "Folds": len(folds), "Mean MSE Difference (Baseline − Enhanced)": mean_difference,
        "SD of MSE Difference": folds["MSE Difference (Baseline − Enhanced)"].std(ddof=1),
        "t Statistic": t_value, "Degrees of Freedom": df, "p-value": p_value,
        "Result": _verdict(p_value, mean_difference, "C"),
    }])
    design = "grouped" if config.split_method == "grouped" else "random"
    metadata = {"design": f"{design} repeated k-fold", "folds": int(folds.Fold.max()), "repeats": int(folds.Repeat.max()),
                "fitted_folds": len(folds), "failed_folds": failures, "seed": config.random_state,
                "partition": "reviewed training partition only; test observations are never used"}
    return folds, pd.DataFrame(summary), test, metadata


def classification_agreement(classifier, test, predicted_classification):
    """Compare station labels computed from the actual wait with labels computed from the predicted wait."""
    reference = classifier.classify(test, test[TARGET])
    actual_label = reference["Overall Station Classification"]
    predicted_label = predicted_classification["Overall Station Classification"]
    order = [*LABELS, PENDING]
    confusion = pd.crosstab(actual_label, predicted_label).reindex(index=order, columns=order, fill_value=0)
    confusion.index.name = "Label from actual wait"
    confusion = confusion.reset_index().rename(columns={c: f"Predicted-wait label: {c}" for c in order})
    resolved = actual_label.isin(LABELS) & predicted_label.isin(LABELS)
    rank = {label: i for i, label in enumerate(LABELS)}
    a, p = actual_label[resolved].map(rank), predicted_label[resolved].map(rank)
    wait_actual = reference["Predicted Waiting Time Severity"]
    wait_predicted = predicted_classification["Predicted Waiting Time Severity"]

    def kappa(weights=None):
        if len(a) < 2 or len(set(a) | set(p)) < 2:
            return np.nan
        with np.errstate(divide="ignore", invalid="ignore"):
            value = cohen_kappa_score(a, p, labels=list(range(len(LABELS))), weights=weights)
        return float(value) if np.isfinite(value) else np.nan

    resolved_count = int(resolved.sum())
    summary = pd.DataFrame([
        {"Measure": "Test observations", "Value": len(test), "Note": ""},
        {"Measure": "Observations resolved under both labels", "Value": resolved_count,
         "Note": "Agreement is computed only where both labels are one of the four conditions."},
        {"Measure": "Exact agreement (%)", "Value": 100 * float((a == p).mean()) if resolved_count else np.nan, "Note": ""},
        {"Measure": "Agreement within one condition level (%)", "Value": 100 * float(((a - p).abs() <= 1).mean()) if resolved_count else np.nan, "Note": ""},
        {"Measure": "Cohen's kappa", "Value": kappa(), "Note": "Chance-corrected agreement; undefined when only one condition occurs."},
        {"Measure": "Linear-weighted Cohen's kappa", "Value": kappa("linear"), "Note": "Partial credit for adjacent conditions."},
        {"Measure": "Waiting-time factor agreement (%)", "Value": 100 * float((wait_actual == wait_predicted).mean()),
         "Note": "Agreement of the predicted-wait severity score alone, across all test observations."},
    ])
    return summary, confusion


def validation_report(prepared, training, models, classifier, predictions, study):
    """Every statistical check of one run; failures are recorded instead of stopping the experiment."""
    report, notes = {}, []
    pairs = [("B", "C", "Effect of selected interaction terms", "B Predicted Wait", "C Predicted Wait"),
             ("A", "B", "Effect of recorded data-review decisions", "A Predicted Wait", "B Predicted Wait"),
             ("A", "C", "Combined workflow comparison", "A Predicted Wait", "C Predicted Wait")]
    report["heldout_significance"] = paired_error_tests(study["predictions"][TARGET], study["predictions"], pairs)
    try:
        folds, summary, test, metadata = cross_validate(training, prepared.config)
        report.update(cv_folds=folds, cv_summary=summary, cv_significance=test, cv_metadata=metadata)
    except ValueError as exc:
        notes.append(f"Cross-validation unavailable: {exc}")
    report["classification_agreement"], report["classification_confusion"] = classification_agreement(
        classifier, prepared.test, predictions)
    report["vif"] = models.vif_table()
    report["notes"] = notes
    return report
