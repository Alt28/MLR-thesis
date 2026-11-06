"""Bundled synthetic demos stay labeled and use the existing analysis workflow."""
from pathlib import Path
import time
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app


@pytest.mark.parametrize('mode', ['bus', 'train'])
def test_library_demo_uses_normal_validation_and_classification(tmp_path, mode):
    path = Path(__file__).resolve().parents[1] / f'frontend/public/assets/datasets/transit_{mode}_SYNTHETIC_DEMO.xlsx'
    with TestClient(create_app(tmp_path)) as client:
        response = client.post('/api/experiments', files={'file': (path.name, path.read_bytes())})
        assert response.status_code == 201, response.text
        state = response.json()
        assert state['records'] == 180
        assert state['provenance']['status'] == 'prototype'
        assert state['config']['vehicle_frequency_unit'] == 'vehicles/hour'
        assert state['config']['route_distance_unit'] == 'km'
        assert state['transport']['dataset_counts'][mode] == 180
        assert state['approved'] is False and state['trained'] == []
        endpoint = f"/api/experiments/{state['id']}"
        response = client.post(endpoint + '/analyze', json={
            'revision': state['revision'], 'approve_interactions': True,
            'retain_remaining': True, 'retain_reason': 'Synthetic software demo validation only'})
        assert response.status_code == 202, response.text
        for _ in range(300):
            state = client.get(endpoint).json()
            if state['status'] != 'running':
                break
            time.sleep(.05)
        assert state['status'] == 'complete', state.get('error')
        assert state['export_ready']
        assert sum(state['distribution'].values()) == 36
        assert 'Requires Researcher Decision' not in state['distribution']
        assert state['provenance']['status'] == 'prototype'



@pytest.mark.parametrize('name,rows', [
    ('transportation_dataset_500_demo_validated.xlsx', 500),
    ('transportation_dataset_200_demo_fixed.xlsx', 200),
    ('transportation_dataset_40_ph_internet_rows.xlsx', 40),
])
def test_earlier_library_workbooks_preserve_declarations(tmp_path, name, rows):
    folder = Path(__file__).resolve().parents[1] / 'frontend/public/assets/datasets'
    content = (folder / name).read_bytes()
    manifest = json.loads((folder / 'source-manifest.json').read_text())
    assert hashlib.sha256(content).hexdigest() == manifest[name]['sha256']
    with TestClient(create_app(tmp_path)) as client:
        response = client.post('/api/experiments', files={'file': (name, content)})
        assert response.status_code == 201, response.text
        state = response.json()
        assert state['records'] == rows
        assert state['provenance']['status'] == 'prototype'
        assert state['transport']['dataset_counts']['unspecified'] == rows
        assert not state['approved'] and state['trained'] == []
        assert state['config']['vehicle_frequency_unit'] == ('' if rows == 40 else 'vehicles/hour')


@pytest.mark.parametrize('name', [
    'mrt3_daily_ridership_jan_apr_2024.csv',
    'metro_manila_historical_scheduled_frequency.csv',
])
def test_reference_files_are_unchanged_and_not_complete_model_inputs(tmp_path, name):
    root = Path(__file__).resolve().parents[1]
    content = (root / 'frontend/public/assets/datasets' / name).read_bytes()
    assert content == (root / 'data/philippine_sources/prepared' / name).read_bytes()
    with TestClient(create_app(tmp_path)) as client:
        response = client.post('/api/experiments', files={'file': (name, content)})
        assert response.status_code == 400
        assert 'Missing required' in response.text
        assert client.get('/api/experiments').json() == []
