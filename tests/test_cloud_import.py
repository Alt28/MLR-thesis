"""Cloud downloads use isolated responses, never private or live research files."""
import asyncio
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.services import cloud_import as cloud


def fetch(handler, url='https://drive.google.com/file/d/fixture/view', provider='google'):
    return asyncio.run(cloud.fetch_dataset(url, provider, transport=httpx.MockTransport(handler)))


@pytest.mark.parametrize('url', [
    'http://drive.google.com/file/d/a/view', 'https://localhost/file/d/a/view',
    'https://drive.google.com.evil.example/file/d/a/view',
    'https://user:pass@drive.google.com/file/d/a/view',
    'https://drive.google.com:8443/file/d/a/view',
    'https://drive.google.com/drive/folders/a', 'https://docs.google.com/spreadsheets/d/a',
])
def test_rejects_unsupported_links(url):
    with pytest.raises(ValueError):
        cloud.download_url(url, 'google')


def test_google_file_redirect_and_resource_key():
    seen = []
    def handler(request):
        seen.append(request.url)
        if len(seen) == 1:
            return httpx.Response(302, headers={'location': 'https://drive.usercontent.google.com/download?id=fixture'})
        return httpx.Response(200, headers={'content-disposition': 'attachment; filename="bus.csv"'}, content=b'column\nvalue')
    name, content = fetch(handler, 'https://drive.google.com/file/d/fixture/view?resourcekey=key')
    assert name == 'bus.csv' and content == b'column\nvalue'
    assert seen[0].params['resourcekey'] == 'key'


def test_onedrive_short_link():
    seen = []
    def handler(request):
        seen.append(request.url)
        if len(seen) == 1:
            return httpx.Response(302, headers={'location': 'https://onedrive.live.com/?resid=ABC!123&authkey=fixture'})
        if len(seen) == 2:
            return httpx.Response(302, headers={'location': 'https://public.files.1drv.com/file'})
        return httpx.Response(200, content=b'PK\x03\x04fixture')
    name, _ = fetch(handler, 'https://1drv.ms/x/fixture', 'onedrive')
    assert seen[1].path == '/download' and seen[1].params['authkey'] == 'fixture'
    assert name.endswith('.xlsx')


@pytest.mark.parametrize('response', [
    httpx.Response(302, headers={'location': 'http://127.0.0.1/private'}),
    httpx.Response(302, headers={'location': 'https://accounts.google.com/login'}),
    httpx.Response(200, headers={'content-type': 'text/html'}, content=b'login'),
    httpx.Response(200, content=b'<!DOCTYPE html><html>login'),
    httpx.Response(403), httpx.Response(200, content=b''),
    httpx.Response(200, headers={'content-disposition': 'attachment; filename="file.exe"'}, content=b'exe'),
])
def test_rejects_blocked_redirects_login_and_wrong_files(response):
    with pytest.raises(ValueError):
        fetch(lambda _: response)


def test_caps_download_and_redirects(monkeypatch):
    monkeypatch.setattr(cloud, 'MAX_UPLOAD_BYTES', 10)
    with pytest.raises(ValueError, match='25 MB'):
        fetch(lambda _: httpx.Response(200, content=b'12345678901'))
    with pytest.raises(ValueError, match='25 MB'):
        fetch(lambda _: httpx.Response(200, headers={'content-length': '11'}, content=b'a'))
    with pytest.raises(ValueError, match='downloadable'):
        fetch(lambda _: httpx.Response(302, headers={'location': 'https://drive.google.com/uc?id=fixture'}))


def test_import_uses_existing_validation_and_preserves_old_data(tmp_path, fixture_data, monkeypatch):
    content = fixture_data.to_csv(index=False).encode()
    async def download(url, provider):
        return 'cloud-fixture.csv', content
    monkeypatch.setattr(cloud, 'fetch_dataset', download)
    with TestClient(create_app(tmp_path / 'cloud')) as client:
        payload = {'provider': 'google', 'url': 'https://drive.google.com/file/d/fixture/view'}
        result = client.post('/api/cloud-import', json=payload)
        assert result.status_code == 201, result.text
        saved = result.json()
        assert saved['records'] == 80 and not saved['approved'] and not saved['metrics']
        content = b'wrong\n123'
        assert client.post('/api/cloud-import', json=payload).status_code == 400
        assert len(client.get('/api/experiments').json()) == 1
        assert client.get('/api/experiments/' + saved['id']).json()['records'] == 80
