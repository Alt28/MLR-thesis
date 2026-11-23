import io
import json
import urllib.error
import pytest
from backend.app import server_discovery as discovery
from src.config import SCHEMA_VERSION


def test_health_alone_does_not_make_old_server_compatible(monkeypatch):
    def fetch(url, timeout):
        if url.endswith('/api/health'): return io.BytesIO(b'{"application":"transit-lab"}')
        if url.endswith('/api/schema'): return io.BytesIO(json.dumps({'defaults': {'schema_version': SCHEMA_VERSION}}).encode())
        raise urllib.error.HTTPError(url, 404, 'Not found', {}, None)
    monkeypatch.setattr(discovery.urllib.request, 'urlopen', fetch)
    assert discovery.server_status('http://127.0.0.1:8000') == 'outdated'


def test_launcher_uses_next_compatible_server(monkeypatch):
    monkeypatch.setattr(discovery, 'server_status', lambda url: 'outdated' if url.endswith(':8000') else 'compatible')
    assert discovery.select_server('127.0.0.1', 8000) == (8001, 'http://127.0.0.1:8001', True)


def test_unrelated_listener_not_reused_or_stopped(monkeypatch):
    monkeypatch.setattr(discovery, 'server_status', lambda url: 'unavailable')
    monkeypatch.setattr(discovery, 'port_available', lambda host, port: port == 8002)
    assert discovery.select_server('0.0.0.0', 8000) == (8002, 'http://127.0.0.1:8002', False)


def test_occupied_range_fails_clearly(monkeypatch):
    monkeypatch.setattr(discovery, 'server_status', lambda url: 'other')
    with pytest.raises(ValueError, match='No compatible'):
        discovery.select_server('127.0.0.1', 8000)
