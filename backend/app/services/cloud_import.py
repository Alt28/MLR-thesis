"""Read public dataset links; never send local credentials to cloud providers."""
import asyncio
import re
from email.message import Message
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

import httpx

from ..config import MAX_UPLOAD_BYTES

ACCESS_MESSAGE = ("This link did not provide a downloadable dataset. Check that it is a shared CSV or XLSX file "
                  "accessible without signing in and that downloading is allowed. For private files, download "
                  "the file from your account and use Upload Dataset.")


def checked_url(url, provider, redirect=False):
    try:
        parts = urlsplit(url)
        host = (parts.hostname or '').lower()
        valid = parts.scheme == 'https' and parts.port in (None, 443) and not parts.username and not parts.password
    except ValueError:
        raise ValueError('Enter a valid HTTPS sharing link.') from None
    if provider == 'google':
        allowed = host in ('drive.google.com', 'drive.usercontent.google.com')
        if redirect:
            allowed |= host.endswith('.googleusercontent.com')
    elif provider == 'onedrive':
        allowed = host in ('1drv.ms', 'onedrive.live.com')
        if redirect:
            allowed |= host.endswith('.files.1drv.com') or host.endswith('.files.1drvusercontent.com')
    else:
        allowed = False
    if not valid or not allowed:
        raise ValueError('Use a Google Drive or personal OneDrive file sharing link. This address or redirect is not supported.')
    return parts


def download_url(url, provider):
    parts = checked_url(url, provider)
    query = parse_qs(parts.query)
    if provider == 'google':
        match = re.fullmatch(r'/file/d/([\w-]+)(?:/[^/]*)?/?', parts.path)
        file_id = match.group(1) if match else query.get('id', [''])[0]
        if not re.fullmatch(r'[\w-]+', file_id):
            raise ValueError('Paste the sharing link for one CSV or XLSX file, not a Drive folder or Google Sheet.')
        parameters = {'id': file_id, 'export': 'download'}
        if query.get('resourcekey'):
            parameters['resourcekey'] = query['resourcekey'][0]
        return 'https://drive.google.com/uc?' + urlencode(parameters)
    return onedrive_download(url)


def onedrive_download(url):
    parts = urlsplit(url)
    if parts.hostname != 'onedrive.live.com':
        return url
    query = parse_qs(parts.query)
    if query.get('resid') or query.get('id'):
        if 'resid' not in query:
            query['resid'] = query.pop('id')
        return urlunsplit(('https', 'onedrive.live.com', '/download', urlencode(query, doseq=True), ''))
    query['download'] = ['1']
    return urlunsplit(('https', 'onedrive.live.com', parts.path, urlencode(query, doseq=True), ''))


async def fetch_dataset(url, provider, *, transport=None):
    current = download_url(url.strip(), provider)
    try:
        async with asyncio.timeout(60):
            async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False, transport=transport) as client:
                for _ in range(7):
                    checked_url(current, provider, redirect=True)
                    async with client.stream('GET', current) as response:
                        if response.is_redirect:
                            location = response.headers.get('location')
                            if not location:
                                raise ValueError(ACCESS_MESSAGE)
                            current = urljoin(current, location)
                            checked_url(current, provider, redirect=True)
                            if provider == 'onedrive':
                                current = onedrive_download(current)
                            continue
                        if response.status_code != 200:
                            raise ValueError(ACCESS_MESSAGE)
                        media_type = response.headers.get('content-type', '').split(';')[0].lower()
                        if media_type in ('text/html', 'application/xhtml+xml', 'application/json'):
                            raise ValueError(ACCESS_MESSAGE)
                        size = response.headers.get('content-length', '')
                        if size.isdigit() and int(size) > MAX_UPLOAD_BYTES:
                            raise ValueError('The cloud dataset exceeds the 25 MB upload limit.')
                        content = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            content.extend(chunk)
                            if len(content) > MAX_UPLOAD_BYTES:
                                raise ValueError('The cloud dataset exceeds the 25 MB upload limit.')
                        if not content:
                            raise ValueError('The cloud file is empty.')
                        if bytes(content[:256]).lstrip().lower().startswith((b'<!doctype html', b'<html')):
                            raise ValueError(ACCESS_MESSAGE)
                        disposition = Message()
                        disposition['content-disposition'] = response.headers.get('content-disposition', '')
                        name = (disposition.get_filename() or '').replace('\\', '/').rsplit('/', 1)[-1]
                        if not name:
                            name = 'cloud-dataset.xlsx' if content.startswith(b'PK\x03\x04') else 'cloud-dataset.csv'
                        if not name.lower().endswith(('.csv', '.xlsx')):
                            raise ValueError('Choose a CSV or XLSX dataset from your cloud storage.')
                        return name, bytes(content)
                raise ValueError(ACCESS_MESSAGE)
    except (httpx.HTTPError, TimeoutError):
        raise ValueError('Could not download the cloud file. Check your connection and sharing link, then try again.') from None
