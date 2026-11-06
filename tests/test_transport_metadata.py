import numpy as np
import pandas as pd
import pytest
from src.config import ResearchConfig
from src.experiment import prepare_experiment, run_experiment
from src.transport_metadata import transport_labels, transport_summary


def test_explicit_row_modes_take_precedence_and_unknowns_stay_unknown(fixture_data):
    data = fixture_data.iloc[:6].copy()
    data['Transport Mode'] = ['Bus', ' TRAIN ', 'MRT', None, 'ferry', 'buses']
    labels, column = transport_labels(data, ResearchConfig(research_notes={'transport_mode': 'bus'}))
    assert column == 'Transport Mode'
    assert labels.tolist() == ['bus', 'train', 'train', 'unspecified', 'unspecified', 'bus']


def test_dataset_declaration_and_missing_mode(fixture_data):
    assert transport_labels(fixture_data, ResearchConfig())[0].eq('unspecified').all()
    assert transport_labels(fixture_data, ResearchConfig(research_notes={'transport_mode': 'train'}))[0].eq('train').all()
    assert transport_labels(fixture_data, ResearchConfig(research_notes={'transport_mode': 'mixed'}))[0].eq('unspecified').all()
    with pytest.raises(ValueError):
        ResearchConfig(research_notes={'transport_mode': 'made-up'}).validate()


def test_transport_metadata_does_not_change_predictions_or_metrics(fixture_data):
    original = run_experiment(prepare_experiment(fixture_data, ResearchConfig()))
    data = fixture_data.copy()
    data['Transport Mode'] = ['Bus', 'Train'] * (len(data) // 2)
    prepared = prepare_experiment(data, ResearchConfig())
    labeled = run_experiment(prepared)
    pd.testing.assert_frame_equal(original.metrics, labeled.metrics)
    pd.testing.assert_frame_equal(original.models.coefficients(), labeled.models.coefficients())
    np.testing.assert_array_equal(original.predictions['Enhanced Predicted Waiting Time'], labeled.predictions['Enhanced Predicted Waiting Time'])
    counts = transport_summary(prepared)
    assert counts['dataset_counts'] == {'bus': 40, 'train': 40, 'unspecified': 0}
    assert sum(counts['test_counts'].values()) == len(prepared.test)
