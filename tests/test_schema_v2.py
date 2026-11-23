"""Artificial software checks only. No test output is thesis evidence."""
from dataclasses import replace
from io import BytesIO
import json
import uuid

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from src.config import ResearchConfig, SCHEMA_VERSION, PREDICTORS, NUMERICAL, CATEGORICAL, TARGET
from src.data_loader import inspect_dataset_bytes, load_prediction_dataset_bytes, validate_data
from src.experiment import prepare_experiment, run_experiment
from src.interaction_terms import FeatureBuilder
from src.irregularity_detection import fit_iqr
from src.mlr_model import MLRModels
from src.station_classification import StationClassifier, UNDEFINED, INSUFFICIENT
from conftest import classification_config, declared_config


def content(frame, extension):
    if extension == 'csv':
        return frame.to_csv(index=False).encode()
    stream = BytesIO()
    frame.to_excel(stream, index=False)
    return stream.getvalue()


@pytest.mark.parametrize('extension', ['csv', 'xlsx'])
@pytest.mark.parametrize('alias', [True, False])
@pytest.mark.parametrize('target', ['omitted', 'blank', 'recorded'])
def test_current_schema_imports(fixture_data, extension, alias, target):
    data = fixture_data.reset_index(drop=True).copy()
    if target == 'omitted': data = data.drop(columns=TARGET)
    if target == 'blank': data[TARGET] = ''
    if alias: data = data.rename(columns={'Vehicle Frequency': 'Observed Vehicle Frequency'})
    data['Observation ID'] = [f'SOURCE-{i}' for i in range(len(data))]
    data = data.drop(columns='Record ID')
    result = inspect_dataset_bytes('input.' + extension, content(data, extension))
    assert result['schema_version'] == SCHEMA_VERSION
    assert result['purpose'] == ('training' if target == 'recorded' else 'prediction')
    assert set(PREDICTORS) <= set(result['columns'])
    assert 'Observed Vehicle Frequency' not in result['columns']
    assert result['preview'][0]['Record ID'] == 'SOURCE-0'
    assert not {'metrics', 'predictions', 'trained'} & set(result)


def test_duplicates_and_station_strings_preserved(fixture_data):
    row = fixture_data.iloc[:1].drop(columns=['Record ID', TARGET]).copy()
    row['Station / Stop'] = '001'
    repeated = pd.concat([row] * 3, ignore_index=True)
    loaded = load_prediction_dataset_bytes('input.csv', content(repeated, 'csv'))
    assert len(loaded) == 3 and loaded['Station / Stop'].eq('001').all()
    assert TARGET not in loaded
    assert loaded['Record ID'].is_unique


@pytest.mark.parametrize('column,value', [
    ('Passenger Volume', -1), ('Vehicle Frequency', float('inf')),
    ('Vehicle Frequency', ''), ('Station / Stop', ''), ('Day of Week', 'Funday'),
    ('Month of Year', 12), ('Time of Day', 'Peak'), ('Passenger Volume', None), ('Vehicle Frequency', True),
])
def test_invalid_values_are_explained(fixture_data, column, value):
    data = fixture_data.astype(object)
    data.loc[data.index[0], column] = value
    with pytest.raises(ValueError, match=column): validate_data(data)


def test_alias_conflict_and_old_schema_rejected(fixture_data):
    data = fixture_data.copy()
    data['Observed Vehicle Frequency'] = data['Vehicle Frequency']
    with pytest.raises(ValueError, match='not both'): validate_data(data)
    old = fixture_data.rename(columns={'Station / Stop': 'Traffic Condition', 'Day of Week': 'Weather Condition', 'Month of Year': 'Route Distance'})
    with pytest.raises(ValueError, match='Missing required'): validate_data(old)


def test_four_categorical_predictors_reference_coded_and_train_only(fixture_data):
    train = fixture_data.head(60)
    builder = FeatureBuilder(ResearchConfig()).fit(train)
    assert set(builder.categories) == set(CATEGORICAL)
    assert set(builder.centers) == set(NUMERICAL)
    for col in CATEGORICAL:
        assert len(builder.blocks[col]) == train[col].nunique() - 1
    assert 'Month of Year' not in builder.transform(train).columns
    changed = fixture_data.tail(20).copy()
    changed['Station / Stop'] = 'UNSEEN STATION'
    before = builder.encoding_table().copy()
    builder.transform(changed)
    pd.testing.assert_frame_equal(before, builder.encoding_table())
    models = MLRModels(ResearchConfig()).fit(train)
    with pytest.raises(ValueError, match='Unseen station'):
        models.predict(changed, strict_categories=True)
    models.schema_version = 'legacy'
    with pytest.raises(ValueError, match='Incompatible'): models.predict(train)


def test_iqr_categories_forbidden_and_bounds_training_only(fixture_data):
    for col in CATEGORICAL:
        with pytest.raises(ValueError, match='numeric'):
            fit_iqr(fixture_data, [col])
    train, test = fixture_data.head(60), fixture_data.tail(20).copy()
    expected = fit_iqr(train, NUMERICAL)
    test['Passenger Volume'] = 1e20
    pd.testing.assert_frame_equal(expected, fit_iqr(train, NUMERICAL))


def test_new_interaction_candidates_and_hierarchy(fixture_data):
    config = ResearchConfig(pairwise_interactions=[
        ('Passenger Volume', 'Vehicle Frequency'), ('Passenger Volume', 'Time of Day'),
        ('Vehicle Frequency', 'Time of Day'), ('Passenger Volume', 'Day of Week')], higher_order_interactions=[])
    builder = FeatureBuilder(config).fit(fixture_data)
    encoded = builder.transform(fixture_data, True)
    assert set(builder.main_columns) <= set(encoded.columns)
    assert all(len(factors) == 2 for factors in builder.interaction_columns.values())
    assert ResearchConfig().higher_order_interactions == [('Vehicle Frequency', 'Time of Day', 'Day of Week')]
    assert ResearchConfig().wait_thresholds == (5.0, 8.0, 12.0)
    with pytest.raises(ValueError, match='hierarchy'):
        ResearchConfig(hierarchical_interactions=False).validate()


def test_training_requires_mode_observations_and_input_availability(fixture_data):
    for config, message in [
        (ResearchConfig(), 'transport mode'),
        (ResearchConfig(research_notes={'transport_mode': 'bus'}), 'recorded passenger'),
        (ResearchConfig(research_notes={'transport_mode': 'bus'}, observed_targets_confirmed=True), 'prediction time'),
    ]:
        with pytest.raises(ValueError, match=message):
            run_experiment(prepare_experiment(fixture_data, config))
    mixed = fixture_data.copy()
    mixed['Transport Mode'] = ['Bus', 'Train'] * (len(mixed) // 2)
    with pytest.raises(ValueError, match='separate'):
        prepare_experiment(mixed, declared_config())


def test_category_scores_require_explicit_approval(fixture_data):
    approved = classification_config()
    proposed = replace(approved, classification_approved=False)
    pending = StationClassifier(proposed).fit(fixture_data)
    assert all(not mapping for mapping in pending.category_mappings.values())
    assert pending.evidence.Status.eq(UNDEFINED).all()
    assert pending.evidence['Derived Severity Score'].isna().all()
    assert pending.classify(fixture_data, np.ones(len(fixture_data)))['Multi-Factor Station Score'].isna().all()
    result = StationClassifier(approved).fit(fixture_data).classify(fixture_data, np.ones(len(fixture_data)))
    assert result['Multi-Factor Station Score'].notna().all()
    with pytest.raises(ValueError, match='rationale'):
        replace(approved, research_notes={}).validate()
    incomplete = replace(approved, category_severity={**approved.category_severity, 'Month of Year': {}})
    assert StationClassifier(incomplete).fit(fixture_data).classify(fixture_data, np.ones(len(fixture_data)))['Multi-Factor Station Score'].isna().all()


@pytest.mark.parametrize('factor', NUMERICAL)
@pytest.mark.parametrize('kind', ['constant', 'collapsed', 'effectively_constant'])
def test_constant_numeric_scores_remain_unresolved(fixture_data, factor, kind):
    data = fixture_data.copy()
    data[factor] = 100.
    if kind == 'collapsed': data.loc[data.index[-1], factor] = 10000.
    if kind == 'effectively_constant': data[factor] += np.arange(len(data)) * 1e-11
    classifier = StationClassifier(classification_config()).fit(data)
    assert classifier.factor_status[factor] == INSUFFICIENT
    result = classifier.classify(data, np.full(len(data), 22.))
    assert result[factor + ' Severity'].isna().all()
    assert result['Multi-Factor Station Score'].isna().all()


def test_legacy_experiment_preserved_but_unavailable(tmp_path):
    sid = uuid.uuid4().hex
    folder = tmp_path / sid
    folder.mkdir()
    metadata = {'id': sid, 'name': 'Old dataset', 'created': '2025-01-01', 'revision': 1, 'status': 'complete', 'config': {}}
    original = json.dumps(metadata)
    (folder / 'metadata.json').write_text(original)
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/api/experiments').json()[0]['compatible'] is False
        response = client.get('/api/experiments/' + sid)
        assert response.status_code == 409 and 'previous predictor schema' in response.text
    assert (folder / 'metadata.json').read_text() == original


def test_source_audit_preserves_ids_without_similarity_join(fixture_data):
    data = fixture_data.iloc[:3].drop(columns='Record ID').copy()
    audit = pd.DataFrame({'Six-column CSV row number': [4, 2, 3],
                          'Observation ID': ['SOURCE-C', 'SOURCE-A', 'SOURCE-B'],
                          'Local hour': ['2025-03-01 02:00', '2025-03-01 00:00', '2025-03-01 01:00']})
    stream = BytesIO()
    with pd.ExcelWriter(stream) as writer:
        data.to_excel(writer, sheet_name='Dataset', index=False)
        audit.to_excel(writer, sheet_name='Source_Audit', index=False)
    loaded = inspect_dataset_bytes('audited.xlsx', stream.getvalue())
    assert [r['Record ID'] for r in loaded['preview']] == ['SOURCE-A', 'SOURCE-B', 'SOURCE-C']
    from src.data_loader import attach_source_audit
    with pytest.raises(ValueError, match='shared observation ID'):
        attach_source_audit(data, audit.drop(columns='Six-column CSV row number'))
    with pytest.raises(ValueError, match='unique'):
        attach_source_audit(data, pd.concat([audit, audit.iloc[:1]]))


def test_future_window_counts_rejected_when_timestamps_available(fixture_data):
    data = fixture_data.copy()
    data['Prediction Timestamp'] = '2026-01-01 08:00:00'
    data['Frequency Window End'] = '2026-01-01 09:00:00'
    with pytest.raises(ValueError, match='future-window'):
        validate_data(data)
    data['Frequency Window End'] = '2026-01-01 08:00:00'
    assert len(validate_data(data)) == len(data)


def test_csv_duplicate_headers_not_silently_mangled(fixture_data):
    data = fixture_data.copy()
    data['duplicate'] = 1
    csv = data.to_csv(index=False).replace('duplicate', 'Vehicle Frequency', 1).encode()
    with pytest.raises(ValueError, match='Duplicate column'):
        inspect_dataset_bytes('duplicate.csv', csv)


def test_blank_optional_template_metadata_can_be_declared_later(fixture_data):
    data = fixture_data.drop(columns='Record ID').copy()
    data['Transport Mode'] = ''
    data['Observation ID'] = ''
    inspection = inspect_dataset_bytes('template.csv', content(data, 'csv'))
    assert inspection['transport_mode'] == 'unknown'
    assert inspection['preview'][0]['Record ID'] == 'R000001'


def test_template_update_never_erases_observations(tmp_path, fixture_data):
    from src.data_loader import write_templates
    path = tmp_path / 'transportation_template.csv'
    original = content(fixture_data, 'csv')
    path.write_bytes(original)
    with pytest.raises(ValueError, match='contains observations'):
        write_templates(tmp_path)
    assert path.read_bytes() == original


@pytest.mark.parametrize('mode', ['bus', 'train'])
def test_each_mode_can_fit_its_own_three_arms(fixture_data, mode):
    data = fixture_data.copy()
    data['Transport Mode'] = mode.title()
    config = declared_config(research_notes={'transport_mode': mode}, cv_folds=2, cv_repeats=1)
    result = run_experiment(prepare_experiment(data, config))
    assert set(result.mode_metrics['Transport Mode']) == {mode.title()}
    assert result.study['metrics'].Arm.tolist() == ['A', 'B', 'C']
    assert result.study['metrics']['Test Rows'].eq(len(result.prepared.test)).all()
    assert result.prepared.config.research_notes['transport_mode'] == mode
