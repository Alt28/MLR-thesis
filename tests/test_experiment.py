import json
import numpy as np
import pandas as pd
import pytest
from src.config import ResearchConfig, TARGET
from src.experiment import prepare_experiment, run_experiment
from src.export import export_experiment, spreadsheet_safe


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
