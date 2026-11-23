from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
from src.config import ResearchConfig, PREDICTORS, LABELS
from src.station_classification import numerical_severity, waiting_time_severity, station_label, StationClassifier, UNDEFINED
from src.data_loader import split_dataset


from conftest import classification_config as configured


@pytest.mark.parametrize("value,score", [(0, 0), (10, 0), (11, 1), (20, 1), (21, 2), (30, 2), (31, 3)])
def test_numeric_boundary_and_reverse(value, score):
    assert numerical_severity([value], [10, 20, 30])[0] == score
    assert numerical_severity([value], [10, 20, 30], "lower")[0] == 3 - score


@pytest.mark.parametrize("value,score", [(-10, 0), (0, 0), (15, 0), (15.01, 1), (20, 1), (20.01, 2), (25, 2), (25.01, 3)])
def test_waiting_boundaries(value, score):
    assert waiting_time_severity([value])[0] == score


@pytest.mark.parametrize("score,label", [(0, LABELS[0]), (.749, LABELS[0]), (.75, LABELS[1]), (1.5, LABELS[2]), (2.25, LABELS[3]), (3, LABELS[3])])
def test_station_boundaries(score, label):
    assert station_label(score) == label


def test_all_seven_factors_and_mapping(fixture_data):
    classifier = StationClassifier(configured()).fit(fixture_data)
    result = classifier.classify(fixture_data, np.full(len(fixture_data), 27))
    columns = [f"{c} Severity" for c in PREDICTORS] + ["Predicted Waiting Time Severity"]
    np.testing.assert_allclose(result["Multi-Factor Station Score"], result[columns].sum(axis=1) / 7)
    assert result.loc[fixture_data["Station / Stop"].eq("C"), "Station / Stop Severity"].eq(3).all()
    assert result["Overall Station Classification"].isin(LABELS).all()


def test_pending_definitions_never_guess(fixture_data):
    result = StationClassifier(ResearchConfig(category_scoring="manual")).fit(fixture_data).classify(fixture_data, np.ones(len(fixture_data)))
    assert result["Overall Station Classification"].eq("Pending configuration").all()
    assert result["Multi-Factor Station Score"].isna().all()
    changed = fixture_data.copy()
    changed["Station / Stop"] = "unknown"
    result = StationClassifier(configured()).fit(fixture_data).classify(changed, np.ones(len(changed)))
    assert result["Overall Station Classification"].eq("Pending configuration").all()


def test_training_quartiles_and_evidence_ignore_test(fixture_data):
    train, test = split_dataset(fixture_data, ResearchConfig())
    classifier = StationClassifier(configured()).fit(train)
    before = classifier.thresholds.copy(deep=True)
    evidence = classifier.evidence.copy(deep=True)
    test["Passenger Volume"] = 1e12
    test["Actual Waiting Time"] = 1e12
    test["Station / Stop"] = "TEST ONLY"
    classifier.classify(test, np.ones(len(test)))
    pd.testing.assert_frame_equal(before, classifier.thresholds)
    pd.testing.assert_frame_equal(evidence, classifier.evidence)
    assert "TEST ONLY" not in classifier.evidence.Category.tolist()
    assert before.loc["Passenger Volume", "Q3"] == train["Passenger Volume"].quantile(.75)


def test_negative_rule_preserves_input(fixture_data):
    predictions = np.full(len(fixture_data), -2.)
    result = StationClassifier(configured()).fit(fixture_data).classify(fixture_data, predictions)
    assert result["Waiting Time Used for Classification"].eq(0).all()
    assert (predictions == -2).all()


def test_automatic_scoring_uses_training_category_means(fixture_data):
    config = ResearchConfig()
    assert config.category_scoring == "automatic"
    classifier = StationClassifier(config).fit(fixture_data)
    q = classifier.target_quartiles
    for col in ("Station / Stop", "Time of Day", "Day of Week", "Month of Year"):
        means = fixture_data.groupby(col)["Actual Waiting Time"].mean()
        expected = {k: int(np.searchsorted(q, v, side="left")) for k, v in means.items()}
        assert classifier.category_mappings[col] == expected
    result = classifier.classify(fixture_data, np.ones(len(fixture_data)))
    assert result["Multi-Factor Station Score"].notna().all()
    assert result["Overall Station Classification"].isin(LABELS).all()
    # Categories never seen in training cannot be scored and stay unresolved.
    unseen = fixture_data.copy()
    unseen["Station / Stop"] = "never-seen"
    assert classifier.classify(unseen, np.ones(len(unseen)))["Multi-Factor Station Score"].isna().all()


def test_approved_manual_mapping_overrides_automatic(fixture_data):
    base = configured()
    station = fixture_data["Station / Stop"].iloc[0]
    config = replace(base, category_scoring="automatic")
    classifier = StationClassifier(config).fit(fixture_data)
    assert classifier.category_mappings["Station / Stop"][station] == base.category_severity["Station / Stop"][station]
