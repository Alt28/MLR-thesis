"""Artificial ZIP fixtures; no API credential or live download required."""
import io
import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import etl_511_archive as archive


def options(tmp_path):
    return SimpleNamespace(token_file=None, months=['2024-03'], cache=tmp_path, max_archive_mb=1)


def zip_bytes(observed=True):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as out:
        out.writestr('stops.txt', 'stop_id,stop_name\nA,Artificial\n')
        out.writestr('stop_observations.txt' if observed else 'stop_times.txt', 'trip_id,stop_id\nT,A\n')
    return stream.getvalue()


def test_missing_token_makes_no_network_request(tmp_path, monkeypatch):
    monkeypatch.delenv('TRANSIT_511_API_KEY', raising=False)
    monkeypatch.setattr(archive.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('No request should be made'))
    with pytest.raises(ValueError, match='free access token'):
        archive.collect_archives(options(tmp_path), {'downloaded_sources': []})
    assert list(tmp_path.iterdir()) == []


def test_schedule_is_not_substituted_for_observed_arrivals(tmp_path):
    file = tmp_path / 'schedule.zip'; file.write_bytes(zip_bytes(False))
    with pytest.raises(ValueError, match='Scheduled stop_times.txt cannot replace'):
        archive.archive_headers(file)


def test_download_and_manifest_never_disclose_token(tmp_path, monkeypatch, capsys):
    secret = 'ARTIFICIAL-TEST-CREDENTIAL'
    monkeypatch.setenv('TRANSIT_511_API_KEY', secret)
    def fetch(request, timeout):
        assert 'historic=2024-03-so' in request.full_url
        assert secret in request.full_url
        return io.BytesIO(zip_bytes())
    monkeypatch.setattr(archive.urllib.request, 'urlopen', fetch)
    manifest = {'downloaded_sources': []}
    archive.collect_archives(options(tmp_path), manifest)
    assert secret not in json.dumps(manifest) + capsys.readouterr().out
    assert len(manifest['downloaded_sources']) == 1
    assert 'NOT merged' in manifest['results']['status']
    monkeypatch.delenv('TRANSIT_511_API_KEY')
    monkeypatch.setattr(archive.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('Use cached archive'))
    archive.collect_archives(options(tmp_path), {'downloaded_sources': []})


def test_failed_download_leaves_no_partial_archive_and_redacts_error(tmp_path, monkeypatch):
    monkeypatch.setenv('TRANSIT_511_API_KEY', 'ARTIFICIAL-TEST-CREDENTIAL')
    def failed(request, timeout):
        raise archive.urllib.error.HTTPError(request.full_url, 401, request.full_url, {}, None)
    monkeypatch.setattr(archive.urllib.request, 'urlopen', failed)
    with pytest.raises(ValueError) as error:
        archive.collect_archives(options(tmp_path), {'downloaded_sources': []})
    assert '401' in str(error.value)
    assert 'ARTIFICIAL-TEST-CREDENTIAL' not in str(error.value)
    assert not list(tmp_path.iterdir())
