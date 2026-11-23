"""Retrieve the official observed-arrival archive for a later, verified APC join.

This stage does not assume an arrival-column schema or claim that GTFS schedule
times are actual observations. Credentials never enter console output/manifests.
"""
import csv
import datetime as dt
import hashlib
import io
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ENDPOINT = 'https://api.511.org/transit/datafeeds'
DOCUMENTATION = 'https://511.org/about/faq'
TOKEN_PAGE = 'https://511.org/open-data/token'


def archive_headers(path):
    with zipfile.ZipFile(path) as archive:
        members = {Path(name).name: name for name in archive.namelist()}
        if 'stop_observations.txt' not in members:
            raise ValueError('The archive lacks stop_observations.txt. Scheduled stop_times.txt cannot replace observed arrivals.')
        result = {}
        for name in ('stop_observations.txt', 'stops.txt', 'trips.txt', 'routes.txt', 'agency.txt'):
            if name in members:
                with archive.open(members[name]) as stream:
                    result[name] = next(csv.reader(io.TextIOWrapper(stream, encoding='utf-8-sig')), [])
        return result


def collect_archives(args, manifest):
    # Use a specific named variable or user-specified file; never inspect other secrets.
    token = (Path(args.token_file).read_text(encoding='utf-8-sig').strip() if args.token_file
             else os.environ.get('TRANSIT_511_API_KEY', '').strip())
    months = sorted(set(args.months or ['2024-03', '2024-07', '2024-11']))
    for month in months:
        dt.datetime.strptime(month, '%Y-%m')
    args.cache.mkdir(parents=True, exist_ok=True)
    inventories = []
    for month in months:
        path = args.cache / f'511_REGIONAL_OBSERVED_{month}.zip'
        public_query = {'operator_id': 'RG', 'historic': month + '-so'}
        public_url = ENDPOINT + '?' + urllib.parse.urlencode(public_query)
        if not path.exists():
            if not token:
                raise ValueError(f'511 requires a free access token: {TOKEN_PAGE}. Save it in a local text file and pass --token-file PATH, or set TRANSIT_511_API_KEY. Existing Train and Bus files remain usable without it.')
            request_url = ENDPOINT + '?' + urllib.parse.urlencode({**public_query, 'api_key': token})
            temporary = path.with_suffix('.zip.part')
            print(f'Downloading 511 observed-arrival archive for {month} (credential hidden).')
            try:
                request = urllib.request.Request(request_url, headers={'User-Agent': 'Academic-Transportation-ETL/1.0'})
                with urllib.request.urlopen(request, timeout=180) as response, temporary.open('wb') as output:
                    total = 0
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > args.max_archive_mb * 1024 * 1024:
                            raise ValueError('511 archive exceeds --max-archive-mb. Increase that limit only if the download fits your available disk space.')
                        output.write(chunk)
                archive_headers(temporary)
                temporary.replace(path)
            except urllib.error.HTTPError as exc:
                raise ValueError(f'511 archive request failed (HTTP {exc.code}); check token access and month availability. No new bus frequency was created.') from None
            except urllib.error.URLError:
                raise ValueError('Could not reach the 511 archive service. No new bus frequency was created.') from None
            finally:
                if temporary.exists(): temporary.unlink()
        columns = archive_headers(path)
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''): digest.update(chunk)
        manifest['downloaded_sources'].append({'url': public_url, 'authentication': 'API token omitted',
                                               'file': str(path), 'sha256': digest.hexdigest()})
        inventories.append({'month': month, 'file': str(path), 'columns': columns})
    manifest['results'] = {'mode': 'bus-arrivals', 'archives': inventories,
                           'status': 'Downloaded for schema and matching review; NOT merged into model inputs.',
                           'next_checks': ['Identify AC Transit agency and historic stop/route identifiers.',
                                           'Verify observed arrival fields, service dates, timezone and duplicate event keys.',
                                           'Match only compatible AC Transit place/date/hour groups; retain unmatched counts.',
                                           'Keep scheduled or predicted arrival times out of measured frequency.'],
                           'documentation': DOCUMENTATION}
