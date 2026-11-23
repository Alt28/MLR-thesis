"""Bundled synthetic demos stay labeled and use the existing analysis workflow."""
from pathlib import Path
import time
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app


@pytest.mark.parametrize('name', [
    'transit_bus_SYNTHETIC_DEMO.xlsx', 'transit_train_SYNTHETIC_DEMO.xlsx',
    'transportation_dataset_200_demo_fixed.xlsx', 'transportation_dataset_40_ph_internet_rows.xlsx',
    'transportation_dataset_500_bus_train.xlsx',
])
def test_superseded_workbooks_rejected_without_mutation(tmp_path, name):
    path = Path(__file__).resolve().parents[1] / 'frontend/public/assets/datasets' / name
    before = path.read_bytes()
    with TestClient(create_app(tmp_path)) as client:
        response = client.post('/api/experiments', files={'file': (name, before)})
        assert response.status_code == 400 and 'Missing required' in response.text
        assert client.get('/api/experiments').json() == []
    assert path.read_bytes() == before


@pytest.mark.parametrize('name', [
    'mrt3_daily_ridership_jan_apr_2024.csv',
    'metro_manila_historical_scheduled_frequency.csv',
])
def test_archived_reference_files_are_not_complete_model_inputs(tmp_path, name):
    root = Path(__file__).resolve().parents[1]
    content = (root / 'data/philippine_sources/prepared' / name).read_bytes()
    assert not (root / 'frontend/public/assets/datasets' / name).exists()
    with TestClient(create_app(tmp_path)) as client:
        response = client.post('/api/experiments', files={'file': (name, content)})
        assert response.status_code == 400
        assert 'Missing required' in response.text
        assert client.get('/api/experiments').json() == []
