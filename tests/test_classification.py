from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
from src.config import ResearchConfig, PREDICTORS, LABELS
from src.station_classification import numerical_severity, waiting_time_severity, station_label, StationClassifier, UNDEFINED
from src.data_loader import split_dataset


def configured():
    return ResearchConfig(
        category_severity={"Traffic Condition": {"A": 0, "B": 1, "C": 3}, "Weather Condition": {"W0": 0, "W1": 3}, "Time of Day": {"T0": 0, "T1": 3}},
        numerical_directions={"Passenger Volume": "higher", "Route Distance": "higher", "Vehicle Frequency": "lower"},
        vehicle_frequency_unit="fixture vehicles/hour",
        route_distance_unit="fixture km",
    )


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
    assert result.loc[fixture_data["Traffic Condition"].eq("C"), "Traffic Condition Severity"].eq(3).all()
    assert result["Overall Station Classification"].isin(LABELS).all()


def test_pending_definitions_never_guess(fixture_data):
    result = StationClassifier(ResearchConfig()).fit(fixture_data).classify(fixture_data, np.ones(len(fixture_data)))
    assert result["Overall Station Classification"].eq("Pending configuration").all()
    assert result["Multi-Factor Station Score"].isna().all()
    changed = fixture_data.copy()
    changed["Weather Condition"] = "unknown"
    result = StationClassifier(configured()).fit(fixture_data).classify(changed, np.ones(len(changed)))
    assert result["Overall Station Classification"].eq("Pending configuration").all()


def test_training_quartiles_and_evidence_ignore_test(fixture_data):
    train, test = split_dataset(fixture_data, ResearchConfig())
    classifier = StationClassifier(configured()).fit(train)
    before = classifier.thresholds.copy(deep=True)
    evidence = classifier.evidence.copy(deep=True)
    test["Passenger Volume"] = 1e12
    test["Actual Waiting Time"] = 1e12
    test["Traffic Condition"] = "TEST ONLY"
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


def test_distance_direction_is_configurable(fixture_data):
    a = configured()
    b = replace(a, numerical_directions={**a.numerical_directions, "Route Distance": "lower"})
    s1 = StationClassifier(a).fit(fixture_data).classify(fixture_data, np.ones(len(fixture_data)))
    s2 = StationClassifier(b).fit(fixture_data).classify(fixture_data, np.ones(len(fixture_data)))
    assert (s1["Route Distance Severity"] + s2["Route Distance Severity"]).eq(3).all()


def test_training_category_means_generate_and_store_all_four_scores(fixture_data):
    training = fixture_data.copy()
    training['Actual Waiting Time'] = np.arange(1., 81.)
    training['Traffic Condition'] = np.repeat(['a', 'b', 'c', 'd'], 20)
    config = ResearchConfig(vehicle_frequency_unit='fixture vehicles/hour', route_distance_unit='fixture km')
    before = config.to_dict()
    classifier = StationClassifier(config).fit(training)
    assert classifier.category_mappings['Traffic Condition'] == {'a': 0, 'b': 1, 'c': 2, 'd': 3}
    assert config.to_dict() == before  # Learned state is not written into researcher overrides.
    for row in classifier.evidence.to_dict(orient='records'):
        mean = training.loc[training[row['Factor']].eq(row['Category']), 'Actual Waiting Time'].mean()
        assert row['Mean Actual Wait'] == pytest.approx(mean)
        assert [row['Q1'], row['Q2'], row['Q3']] == pytest.approx(training['Actual Waiting Time'].quantile([.25, .5, .75]))
        assert row['Severity Score'] == numerical_severity([mean], classifier.target_quartiles)[0]
        assert row['Mapping Source'] == 'Training category mean'
    predicted = classifier.classify(training, np.full(80, 22.))
    assert predicted['Multi-Factor Station Score'].notna().all()


@pytest.mark.parametrize('factor', ['Passenger Volume', 'Route Distance', 'Vehicle Frequency'])
@pytest.mark.parametrize('mode', ['constant', 'collapsed', 'effectively_constant'])
def test_insufficient_variation_cannot_be_overridden(fixture_data, factor, mode):
    training = fixture_data.copy()
    training[factor] = 100.
    if mode == 'collapsed': training.loc[training.index[-1], factor] = 10000.
    if mode == 'effectively_constant': training[factor] += np.arange(80) * 1e-11
    classifier = StationClassifier(configured()).fit(training)
    from src.station_classification import INSUFFICIENT
    assert classifier.thresholds.loc[factor, 'Status'] == INSUFFICIENT
    assert classifier.directions[factor] is None
    # A varying held-out observation cannot supply missing training variation.
    test = training.iloc[:2].copy()
    test[factor] = [1., 1e9]
    result = classifier.classify(test, [10., 30.])
    assert result[factor + ' Severity'].isna().all()
    assert result['Multi-Factor Station Score'].isna().all()
    assert result['Overall Station Classification'].eq('Pending configuration').all()
    assert result['Missing Classification Definitions'].str.contains(factor + ': ' + INSUFFICIENT, regex=False).all()


@pytest.mark.parametrize('direction', ['higher', 'lower'])
def test_auto_directions_follow_training_relationship_only(fixture_data, direction):
    training = fixture_data.copy()
    x = np.arange(1., 81.)
    training['Actual Waiting Time'] = x
    for factor in ['Route Distance', 'Vehicle Frequency']:
        training[factor] = x if direction == 'higher' else x[::-1]
    classifier = StationClassifier(ResearchConfig(vehicle_frequency_unit='fixture units')).fit(training)
    for factor in ['Route Distance', 'Vehicle Frequency']:
        assert classifier.directions[factor] == direction
        assert classifier.thresholds.loc[factor, 'Direction Source'] == 'Training Pearson correlation'
        assert abs(classifier.thresholds.loc[factor, 'Training Pearson Correlation']) == pytest.approx(1)
    test = training.iloc[:4].copy()
    test['Actual Waiting Time'] = 1e10
    test['Route Distance'] = 1e10
    classifier.classify(test, [5.] * 4)
    assert classifier.directions['Route Distance'] == direction


def test_zero_relationship_requires_direction_and_explicit_override_wins(fixture_data):
    training = fixture_data.copy()
    training['Route Distance'] = np.arange(1., 81.)
    training['Actual Waiting Time'] = (np.arange(1., 81.) - 40.5) ** 2
    auto = StationClassifier(ResearchConfig()).fit(training)
    assert auto.directions['Route Distance'] is None
    assert auto.thresholds.loc['Route Distance', 'Status'] == 'Requires Researcher Decision'
    fixed = StationClassifier(configured()).fit(training)
    assert fixed.directions['Route Distance'] == 'higher'
    assert fixed.thresholds.loc['Route Distance', 'Direction Source'] == 'Researcher configuration'
    training['Actual Waiting Time'] = np.arange(80., 0., -1.)
    fixed = StationClassifier(configured()).fit(training)
    assert fixed.directions['Route Distance'] == 'higher'  # Explicit override, not a silent replacement.
    assert fixed.distance_correlation == pytest.approx(-1)


def test_every_required_measurement_unit_blocks_classification(fixture_data):
    complete = configured()
    for field in ('vehicle_frequency_unit', 'route_distance_unit'):
        config = replace(complete, **{field: '   '})
        result = StationClassifier(config).fit(fixture_data).classify(fixture_data, np.full(len(fixture_data), 22.))
        assert result['Overall Station Classification'].eq('Pending configuration').all()
        assert result['Multi-Factor Station Score'].isna().all()
        factor = 'Vehicle Frequency' if field == 'vehicle_frequency_unit' else 'Route Distance'
        assert result['Missing Classification Definitions'].str.contains(f'{factor} unit: {UNDEFINED}', regex=False).all()
    classifier = StationClassifier(complete).fit(fixture_data)
    assert classifier.undeclared_units() == []
    assert classifier.rule_metadata['measurement_units'] == {
        'Vehicle Frequency': 'fixture vehicles/hour', 'Route Distance': 'fixture km'}
    assert classifier.classify(fixture_data, np.full(len(fixture_data), 22.))['Multi-Factor Station Score'].notna().all()


def test_category_overrides_and_unseen_categories(fixture_data):
    config = ResearchConfig(vehicle_frequency_unit='fixture units')
    config.category_severity['Traffic Condition'] = {'A': 3, 'explicit unseen': 2}
    classifier = StationClassifier(config).fit(fixture_data)
    assert classifier.category_mappings['Traffic Condition']['A'] == 3
    ev = classifier.evidence.query("Factor == 'Traffic Condition' and Category == 'explicit unseen'").iloc[0]
    assert ev['Training Count'] == 0 and pd.isna(ev['Mean Actual Wait'])
    test = fixture_data.iloc[:2].copy()
    test['Traffic Condition'] = ['unknown', 'explicit unseen']
    result = classifier.classify(test, [22., 22.])
    assert pd.isna(result.iloc[0]['Traffic Condition Severity'])
    assert result.iloc[0]['Overall Station Classification'] == 'Pending configuration'
    assert result.iloc[1]['Traffic Condition Severity'] == 2
    assert 'unknown' not in classifier.category_mappings['Traffic Condition']


def test_degenerate_target_and_single_category_do_not_generate_mappings(fixture_data):
    training = fixture_data.copy()
    training['Actual Waiting Time'] = 20.
    classifier = StationClassifier(ResearchConfig()).fit(training)
    assert all(not m for m in classifier.category_mappings.values())
    assert classifier.evidence.Status.eq('Insufficient Variation for Classification').all()
    training = fixture_data.copy()
    training['Weather Condition'] = 'only category'
    classifier = StationClassifier(ResearchConfig()).fit(training)
    assert classifier.category_mappings['Weather Condition'] == {}
    # A documented configured rule is distinct from a learned quartile rule.
    config = ResearchConfig(category_severity={'Weather Condition': {'only category': 1}})
    assert StationClassifier(config).fit(training).category_mappings['Weather Condition'] == {'only category': 1}


def test_reviewed_rows_determine_category_mapping_and_target_quartiles(fixture_data):
    from src.experiment import prepare_experiment, run_experiment
    original = fixture_data.copy()
    prepared = prepare_experiment(original, ResearchConfig(vehicle_frequency_unit='fixture units'))
    rid = prepared.training.index[0]
    original.loc[rid, 'Actual Waiting Time'] = 10000.
    prepared = prepare_experiment(original, prepared.config)
    result = run_experiment(prepared, {rid: {'action': 'exclude', 'reason': 'Artificial review fixture'}})
    assert rid not in result.training.index
    np.testing.assert_allclose(result.classifier.target_quartiles, result.training['Actual Waiting Time'].quantile([.25, .5, .75]))
    expected = result.training.groupby('Traffic Condition')['Actual Waiting Time'].mean()
    actual = result.classifier.evidence.query("Factor == 'Traffic Condition'").set_index('Category')['Mean Actual Wait']
    pd.testing.assert_series_equal(actual, expected, check_names=False)
