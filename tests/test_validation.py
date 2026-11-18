import json
import numpy as np
import pandas as pd
import pytest
from src.config import ResearchConfig, TARGET
from src.data_loader import split_dataset
from src.experiment import prepare_experiment, run_experiment
from src.export import export_experiment
from src.station_classification import StationClassifier
from src.validation import (_fold_splits, classification_agreement, corrected_resampled_ttest,
                            paired_error_tests)

UNITS = dict(vehicle_frequency_unit="fixture vehicles/hour", route_distance_unit="fixture km")


def test_paired_tests_detect_difference_and_skip_identical_predictions():
    rng = np.random.default_rng(1)
    actual = rng.normal(20, 3, 60)
    frame = pd.DataFrame({"good": actual + rng.normal(0, .5, 60), "bad": actual + rng.normal(0, 4, 60)})
    frame["same"] = frame.good
    table = paired_error_tests(actual, frame, [("X", "Y", "q", "bad", "good"), ("Y", "Z", "q", "good", "same")])
    different = table[table.Comparison.eq("X vs Y")]
    assert (different["p-value"] < .05).all() and different.Result.str.contains("Y lower error").all()
    assert table[table.Comparison.eq("Y vs Z")].Result.eq("Identical predictions; no difference to test").all()


def test_grouped_cross_validation_never_splits_a_station(fixture_data):
    data = fixture_data.copy()
    data["Station ID"] = [f"ST-{i % 9}" for i in range(len(data))]
    config = ResearchConfig(split_method="grouped", cv_folds=4, cv_repeats=2)
    training, _ = split_dataset(data, config)
    splits = list(_fold_splits(training, config))
    assert len(splits) == 8
    for _, _, fit_rows, validation_rows in splits:
        assert not set(training.iloc[fit_rows]["Station ID"]) & set(training.iloc[validation_rows]["Station ID"])
        assert len(fit_rows) + len(validation_rows) == len(training)


def test_corrected_resampled_ttest_inflates_variance():
    differences = [1.0, 2.0, 1.5, 0.5, 1.2]
    t_value, p_value, df = corrected_resampled_ttest(differences, [80] * 5, [20] * 5)
    d = np.array(differences)
    assert df == 4
    assert t_value == pytest.approx(d.mean() / np.sqrt((1 / 5 + 20 / 80) * d.var(ddof=1)))
    assert t_value < d.mean() / np.sqrt(d.var(ddof=1) / 5)


def test_classification_agreement_is_perfect_when_prediction_equals_actual(fixture_data):
    config = ResearchConfig(**UNITS)
    training, test = split_dataset(fixture_data, config)
    classifier = StationClassifier(config).fit(training)
    summary, confusion = classification_agreement(classifier, test, classifier.classify(test, test[TARGET]))
    values = summary.set_index("Measure").Value
    assert values["Observations resolved under both labels"] > 0
    assert values["Exact agreement (%)"] == 100 and values["Waiting-time factor agreement (%)"] == 100
    counts = confusion.drop(columns=confusion.columns[0]).to_numpy()
    assert counts.trace() == len(test)


def test_run_exports_statistical_checks(tmp_path, fixture_data):
    result = run_experiment(prepare_experiment(fixture_data, ResearchConfig(cv_folds=4, cv_repeats=3, **UNITS)))
    validation = result.validation
    assert len(validation["cv_folds"]) == 12
    assert set(validation["heldout_significance"].Comparison) == {"B vs C", "A vs B", "A vs C"}
    assert {"MAE", "R2"} <= set(result.metrics.columns)
    coefficients = result.models.coefficients()
    assert coefficients.loc[coefficients.Model.eq("Baseline MLR"), "Std. Error"].notna().all()
    directory = export_experiment(result, tmp_path)
    sheets = set(pd.ExcelFile(directory / "experiment.xlsx").sheet_names)
    assert {"vif", "heldout_significance", "cv_summary", "cv_significance", "classification_agreement"} <= sheets
    report = (directory / "METHODOLOGY.md").read_text(encoding="utf-8")
    assert "Nadeau & Bengio" in report and "Variance inflation factors" in report and "centered at their training means" in report
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["statistical_checks"]["cross_validation"]["fitted_folds"] == 12
