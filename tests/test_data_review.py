import numpy as np
import pandas as pd
import pytest
from src.config import ResearchConfig, ROW_ID
from src.data_loader import validate_data, split_dataset, load_dataset, write_templates
from src.irregularity_detection import fit_iqr, flag_irregularities, apply_reviews
from src.irregularity_detection import review_bundle, read_review_bundle
from src.experiment import prepare_experiment


def test_iqr_and_detection():
    frame = pd.DataFrame({"x": [1, 2, 3, 4, 100]}, index=list("abcde"))
    bounds = fit_iqr(frame, ["x"])
    assert bounds.loc["x", ["Q1", "Q3", "IQR", "Lower Bound", "Upper Bound"]].tolist() == [2, 4, 2, -1, 7]
    assert flag_irregularities(frame, bounds)[ROW_ID].tolist() == ["e"]


def test_zero_iqr_and_boundary():
    frame = pd.DataFrame({"x": [5, 5, 5, 5, 6]})
    assert len(flag_irregularities(frame, fit_iqr(frame, ["x"]))) == 1


def test_validation_and_split(fixture_data):
    a, b = split_dataset(fixture_data, ResearchConfig())
    c, d = split_dataset(fixture_data, ResearchConfig())
    assert a.equals(c) and b.equals(d) and set(a.index).isdisjoint(b.index)
    for col, value in [("Passenger Volume", -1), ("Route Distance", np.inf), ("Time of Day", "")]:
        bad = fixture_data.copy()
        bad.at[bad.index[0], col] = value
        with pytest.raises(ValueError):
            validate_data(bad)
    with pytest.raises(ValueError, match="Missing required"):
        validate_data(fixture_data.drop(columns="Vehicle Frequency"))


def test_review_preserves_then_audits(fixture_data):
    data = fixture_data.copy()
    rid = data.index[0]
    data.at[rid, "Passenger Volume"] = 10000
    flags = flag_irregularities(data, fit_iqr(data, ["Passenger Volume"]))
    kept, audit = apply_reviews(data, flags)
    assert len(kept) == len(data) and audit.iloc[0]["Action"] == "retain_unreviewed"
    corrected, audit = apply_reviews(data, flags, {rid: {"action": "correct", "reason": "fixture source check", "corrections": {"Passenger Volume": 100}}})
    assert corrected.at[rid, "Passenger Volume"] == 100
    assert data.at[rid, "Passenger Volume"] == 10000
    excluded, _ = apply_reviews(data, flags, {rid: {"action": "exclude", "reason": "fixture error"}})
    assert rid not in excluded.index
    with pytest.raises(ValueError):
        apply_reviews(data, flags, {"test-row": {"action": "exclude"}})
    with pytest.raises(ValueError):
        apply_reviews(data, flags, {rid: {"action": "exclude"}})


def test_csv_excel_roundtrip_and_empty_template(tmp_path, fixture_data):
    write_templates(tmp_path)
    with pytest.raises(ValueError, match="no observations"):
        load_dataset(tmp_path / "transportation_template.csv")
    for suffix in ["csv", "xlsx"]:
        path = tmp_path / ("fixture." + suffix)
        if suffix == "csv": fixture_data.to_csv(path, index=False)
        else: fixture_data.to_excel(path, index=False)
        loaded = load_dataset(path)
        assert len(loaded) == len(fixture_data)
        assert loaded.index.tolist() == fixture_data.index.tolist()


def test_iqr_training_only(fixture_data):
    train, test = split_dataset(fixture_data, ResearchConfig())
    bounds = fit_iqr(train, ["Passenger Volume"])
    test["Passenger Volume"] = 1e12
    pd.testing.assert_frame_equal(bounds, fit_iqr(train, ["Passenger Volume"]))


def test_saved_reviews_bound_to_source_and_split(fixture_data):
    prepared = prepare_experiment(fixture_data, ResearchConfig())
    bundle = review_bundle(prepared, {})
    assert read_review_bundle(prepared, bundle) == {}
    another_split = prepare_experiment(fixture_data, ResearchConfig(random_state=7))
    with pytest.raises(ValueError, match="does not match"):
        read_review_bundle(another_split, bundle)
    changed = fixture_data.copy()
    changed.iloc[0, changed.columns.get_loc("Actual Waiting Time")] += 1
    with pytest.raises(ValueError, match="does not match"):
        read_review_bundle(prepare_experiment(changed, ResearchConfig()), bundle)
    with pytest.raises(ValueError, match="review bundle"):
        read_review_bundle(prepared, {})
