import json
import numpy as np
import pandas as pd
import pytest
from src.config import ResearchConfig, TARGET
from src.experiment import prepare_experiment, run_experiment
from src.export import export_experiment, spreadsheet_safe
from src.evaluation import metrics
from src.station_classification import aggregate_station_scores


def test_complete_export(tmp_path, fixture_data):
    prepared = prepare_experiment(fixture_data, ResearchConfig())
    result = run_experiment(prepared)
    directory = export_experiment(result, tmp_path)
    assert (directory / "experiment.xlsx").exists()
    assert (directory / "models.joblib").exists()
    assert len(list((directory / "figures").glob("*.png"))) == 8
    loaded = pd.read_csv(directory / "csv" / "predictions.csv")
    assert len(loaded) == len(prepared.test)
    assert loaded["Overall Station Classification"].eq("Pending configuration").all()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["training_original"] == 64
    assert len(manifest["source_sha256"]) == 64
    assert "category_evidence" in pd.ExcelFile(directory / "experiment.xlsx").sheet_names
    rules = json.loads((directory / "classification_rules.json").read_text(encoding="utf-8"))
    assert rules["classification_version"] == 2
    assert rules["category_mappings"] == result.classifier.category_mappings
    evidence = pd.read_excel(directory / "experiment.xlsx", sheet_name="category_evidence")
    assert {"Q1", "Q2", "Q3", "Severity Score", "Mapping Source", "Status"} <= set(evidence.columns)
    import joblib
    saved = joblib.load(directory / "models.joblib")
    restored = saved["classifier"]
    assert saved["original_baseline"] is not None
    pd.testing.assert_frame_equal(saved["original_baseline"].coefficients(), result.study["original_model"].coefficients())
    protocol = json.loads((directory / "research_protocol.json").read_text(encoding="utf-8"))
    assert protocol["test_record_ids"] == list(prepared.test.index)
    assert (directory / "data_provenance.json").exists()
    assert pd.read_csv(directory / "csv" / "study_metrics.csv").Arm.tolist() == ["A", "B", "C"]
    assert "study_comparisons" in pd.ExcelFile(directory / "experiment.xlsx").sheet_names
    pd.testing.assert_frame_equal(restored.classify(prepared.test, result.predictions["Enhanced Predicted Waiting Time"]),
                                  result.classifier.classify(prepared.test, result.predictions["Enhanced Predicted Waiting Time"]))
    specification = pd.read_excel(directory / "experiment.xlsx", sheet_name="selected_interactions")
    assert specification["Order"].tolist() == ["pairwise", "higher-order"]
    assert specification["Predictors"].tolist() == [" × ".join(t) for t in
        [*prepared.config.pairwise_interactions, *prepared.config.higher_order_interactions]]
    assert specification["Main Effects Retained"].all()


def test_methodology_report_states_the_applied_methods(tmp_path, fixture_data):
    data = fixture_data.copy()
    data["Station ID"] = [f"ST-{i % 8:02d}" for i in range(len(data))]
    config = ResearchConfig(split_method="grouped", vehicle_frequency_unit="fixture vehicles/hour",
                            route_distance_unit="fixture km")
    result = run_experiment(prepare_experiment(data, config))
    report = (export_experiment(result, tmp_path) / "METHODOLOGY.md").read_text(encoding="utf-8")
    assert "grouped holdout" in report and "Station ID" in report
    assert f"test fraction {config.test_size}, seed {config.random_state}" in report
    assert "fixture vehicles/hour" in report and "fixture km" in report
    assert "Passenger Volume × Vehicle Frequency (pairwise)" in report
    assert "Ordinary Least Squares" in report
    for arm in ("Arm A:", "Arm B:", "Arm C:"):
        assert arm in report
    assert f"Multi-Factor Station Score = (sum of the seven severity scores) / 7" in report
    assert all(str(bound) in report for bound in config.station_thresholds)
    assert f"All arms are scored on the same {len(result.prepared.test)} test observations." in report
    for warning in result.warnings:
        assert warning in report


def test_test_set_perturbation_cannot_change_training_artifacts(fixture_data):
    prepared = prepare_experiment(fixture_data, ResearchConfig())
    first = run_experiment(prepared)
    prepared.test["Passenger Volume"] = 999999
    prepared.test[TARGET] = 999999
    prepared.test["Traffic Condition"] = "TEST_CATEGORY"
    second = run_experiment(prepared)
    pd.testing.assert_frame_equal(first.models.coefficients(), second.models.coefficients())
    pd.testing.assert_frame_equal(first.classifier.thresholds, second.classifier.thresholds)
    pd.testing.assert_frame_equal(first.classifier.evidence, second.classifier.evidence)
    assert first.models.features.categories == second.models.features.categories


def test_mode_metrics_and_station_summary_use_only_test_predictions(fixture_data):
    data = fixture_data.copy()
    data["Transport Mode"] = ["Bus", "Train"] * (len(data) // 2)
    data["Station ID"] = ["ST-01", "ST-02"] * (len(data) // 2)
    result = run_experiment(prepare_experiment(data, ResearchConfig()))
    assert set(result.mode_metrics["Transport Mode"]) == {"Bus", "Train"}
    assert result.mode_metrics.groupby("Transport Mode")["Test Rows"].nunique().eq(1).all()
    assert result.mode_metrics.groupby("Transport Mode").size().eq(2).all()
    assert result.station_aggregation["available"]
    assert result.station_aggregation["station_count"] == 2
    assert result.station_summary["Test Records"].sum() == len(result.prepared.test)
    assert result.station_summary["Classifiable Records"].sum() == 0
    assert result.station_summary["Unresolved Records"].sum() == len(result.prepared.test)
    test_modes = result.prepared.test["Transport Mode"].str.lower()
    for mode in ("Bus", "Train"):
        selected = test_modes.eq(mode.lower())
        actual = result.prepared.test.loc[selected, TARGET]
        for prefix, model in (("Baseline", "Baseline MLR"), ("Enhanced", "Enhanced MLR")):
            row = result.mode_metrics[
                result.mode_metrics["Transport Mode"].eq(mode)
                & result.mode_metrics["Model"].eq(model)
            ].iloc[0]
            expected = metrics(actual, result.predictions.loc[selected, f"{prefix} Predicted Waiting Time"])
            assert row["MSE"] == pytest.approx(expected["MSE"])
            assert row["RMSE"] == pytest.approx(expected["RMSE"])


def test_station_aggregation_averages_classifiable_scores_and_counts_unresolved():
    predictions = pd.DataFrame({
        "Station": ["A", "A", "A", None],
        "Multi-Factor Station Score": [0.0, 2.0, np.nan, 3.0],
    })
    summary, metadata = aggregate_station_scores(predictions)
    assert metadata["available"] and metadata["ungrouped_records"] == 1
    assert summary.loc[0, "Mean Multi-Factor Station Score"] == pytest.approx(1.0)
    assert summary.loc[0, "Classifiable Records"] == 2
    assert summary.loc[0, "Unresolved Records"] == 1
    assert summary.loc[0, "Overall Station Classification"] == "Minor Delay"


def test_corrections_shared_by_models_but_test_unchanged(fixture_data):
    data = fixture_data.copy()
    prepared = prepare_experiment(data, ResearchConfig())
    rid = prepared.training.index[0]
    data.at[rid, "Passenger Volume"] = 100000
    prepared = prepare_experiment(data, ResearchConfig())
    test_before = prepared.test.copy()
    result = run_experiment(prepared, {rid: {"action": "exclude", "reason": "Artificial fixture error"}})
    assert len(result.training) == len(prepared.training) - 1
    assert all(d["Training Rows"] == len(result.training) for d in result.models.diagnostics)
    pd.testing.assert_frame_equal(test_before, prepared.test)


def test_formula_prefix_is_text():
    result = spreadsheet_safe(pd.DataFrame({"text": ["=1+1", "@bad", "safe"], "number": [-2, 3, 4]}))
    assert result.text.tolist() == ["'=1+1", "'@bad", "safe"]
    assert result.number.tolist() == [-2, 3, 4]
