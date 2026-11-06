"""Artificial fixtures check the protocol, never claim transportation accuracy."""
import numpy as np
import pandas as pd
import pytest
from src.config import ResearchConfig, TARGET
from src.experiment import prepare_experiment, run_experiment
from src.research_protocol import source_declarations


def test_no_review_change_does_not_claim_iqr_improvement(fixture_data):
    result = run_experiment(prepare_experiment(fixture_data, ResearchConfig()))
    study = result.study
    assert study["metrics"].Arm.tolist() == ["A", "B", "C"]
    assert study["metrics"]["Test Rows"].tolist() == [16, 16, 16]
    np.testing.assert_allclose(study["predictions"]["A Predicted Wait"], study["predictions"]["B Predicted Wait"])
    assert not study["metadata"]["review_changed_training_data"]
    assert "not demonstrated" in study["comparisons"].iloc[0]["Outcome for second arm"]


def test_review_changes_only_reviewed_arms_and_keeps_identical_test(fixture_data):
    config = ResearchConfig()
    initial = prepare_experiment(fixture_data, config)
    rid = initial.training.index[0]
    data = fixture_data.copy()
    data.at[rid, TARGET] = 10000
    prepared = prepare_experiment(data, config)
    before = run_experiment(prepared)
    after = run_experiment(prepared, {rid: {"action": "exclude", "reason": "Deliberate artificial recording error"}})
    a, b = before.study, after.study
    pd.testing.assert_frame_equal(a["original_model"].coefficients(), b["original_model"].coefficients())
    assert b["metrics"]["Training Rows"].tolist() == [64, 63, 63]
    assert b["metadata"]["test_record_ids"] == list(prepared.test.index)
    assert rid not in b["metadata"]["test_record_ids"]
    assert not np.allclose(a["predictions"]["B Predicted Wait"], b["predictions"]["B Predicted Wait"])
    for arm in "ABC":
        mse = np.mean((prepared.test[TARGET] - b["predictions"][f"{arm} Predicted Wait"]) ** 2)
        assert b["metrics"].set_index("Arm").loc[arm, "MSE"] == pytest.approx(mse)
    difference = b["comparisons"].iloc[0]
    scores = b["metrics"].set_index("Arm")
    assert difference["RMSE reduction (min)"] == pytest.approx(scores.loc["A", "RMSE"] - scores.loc["B", "RMSE"])
    prepared.test[TARGET] += 500
    perturbed = run_experiment(prepared)
    pd.testing.assert_frame_equal(a["original_model"].coefficients(), perturbed.study["original_model"].coefficients())


def test_workbook_prototype_declaration_survives_recorded_override(tmp_path, fixture_data):
    file = tmp_path / "prototype.xlsx"
    with pd.ExcelWriter(file) as writer:
        fixture_data.to_excel(writer, sheet_name="Transportation_Dataset", index=False)
        pd.DataFrame([{"Item": "Source", "Value / Rule": "This dataset is simulated. NOT final thesis evidence."}]).to_excel(writer, sheet_name="Sources_Methodology", index=False)
    prepared = prepare_experiment(file, ResearchConfig(research_notes={"source_type": "recorded"}))
    assert prepared.provenance["status"] == "prototype"
    assert prepared.provenance["workbook_declares_prototype"]
    assert any("dataset is simulated" in row["Note"] for row in prepared.provenance["workbook_notes"])
    assert source_declarations(fixture_data, {})["status"] == "undocumented"
    assert source_declarations(fixture_data, {"source_type": "recorded"})["status"] == "recorded_declared"
    assert source_declarations(fixture_data, {"source_type": "simulated"})["status"] == "prototype"


@pytest.mark.parametrize("notes", [[], {"source_type": "verified"}, {"source_reference": 123}, {"source_reference": "x" * 4001}, {"invented": "field"}])
def test_research_notes_validation(notes):
    with pytest.raises(ValueError):
        ResearchConfig(research_notes=notes).validate()


def test_prototype_banner_in_first_spreadsheet_row_is_not_lost(tmp_path, fixture_data):
    file = tmp_path / "banner.xlsx"
    with pd.ExcelWriter(file) as writer:
        fixture_data.to_excel(writer, sheet_name="Transportation_Dataset", index=False)
        pd.DataFrame([
            ["IMPORTANT", "NOT final observation-level thesis evidence. Synthetic/demo data."],
            ["Variable", "Meaning"], ["Actual Waiting Time", "Generated values"],
        ]).to_excel(writer, sheet_name="Sources_Methodology", header=False, index=False)
    evidence = source_declarations(file, {})
    assert evidence["status"] == "prototype"
    assert "NOT final" in evidence["workbook_notes"][0]["Note"]
