from io import BytesIO
import pandas as pd
from fastapi.testclient import TestClient
from backend.app.main import create_app
from src.dataset_units import documented_units


def workbook(path, data, declarations):
    with pd.ExcelWriter(path) as writer:
        data.to_excel(writer, index=False, sheet_name='Dataset')
        pd.DataFrame([['Prototype test data', '', ''], ['Variable', 'Meaning', 'Unit'], *declarations]).to_excel(
            writer, index=False, header=False, sheet_name='Sources_Methodology')


def test_exact_documented_units_and_conflicts(tmp_path, fixture_data):
    path = tmp_path / 'units.xlsx'
    workbook(path, fixture_data, [['Vehicle Frequency', 'Service frequency', 'vehicles/hour'], ['Route Distance', 'Trip length', 'km']])
    assert documented_units(path) == {'vehicle_frequency_unit': 'vehicles/hour', 'route_distance_unit': 'km'}
    workbook(path, fixture_data, [['Vehicle Frequency', '', 'vehicles/hour'], ['Vehicle Frequency', '', 'minutes'], ['Route Distance', '', '']])
    assert documented_units(path) == {}
    assert documented_units(tmp_path / 'unknown.csv') == {}
    workbook(path, fixture_data, [['Vehicle Frequency', 'vehicles/hour mentioned in prose only', '']])
    assert documented_units(path) == {}


def test_import_defaults_are_saved_and_editable(tmp_path, fixture_data):
    buffer = BytesIO()
    workbook(buffer, fixture_data, [['Vehicle Frequency', 'Service frequency', 'vehicles/hour'], ['Route Distance', 'Trip length', 'km']])
    storage = tmp_path / 'state'
    with TestClient(create_app(storage)) as client:
        response = client.post('/api/experiments', files={'file': ('units.xlsx', buffer.getvalue())})
        assert response.status_code == 201, response.text
        s = response.json()
        assert s['config']['vehicle_frequency_unit'] == 'vehicles/hour'
        assert s['config']['route_distance_unit'] == 'km'
        assert not s['approved'] and not s['metrics']
        config = s['config']
        config['vehicle_frequency_unit'] = 'researcher documented count'
        response = client.put('/api/experiments/' + s['id'] + '/config', json={'revision': s['revision'], 'config': config})
        assert response.status_code == 200
    with TestClient(create_app(storage)) as client:
        restored = client.get('/api/experiments/' + s['id']).json()
        assert restored['config']['vehicle_frequency_unit'] == 'researcher documented count'
