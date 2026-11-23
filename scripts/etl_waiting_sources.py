"""Collect published passenger-wait records for review, without inventing predictors.

These are deliberately NOT system training exports or library registrations.
Austin measures passenger arrival to bus departure (not boarding); the Australian
survey measures self-reported waiting. Neither supplies the current six predictors.
"""
from __future__ import annotations

from collections import Counter
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import urllib.error
import urllib.request

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill


BUS_URL = 'https://static.tti.tamu.edu/swutc.tamu.edu/publications/technicalreports/167211-1.pdf'
TRAIN_PAGE = 'https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0199449'
TRAIN_URL = 'https://journals.plos.org/plosone/article/file?id=10.1371%2Fjournal.pone.0199449.s001&type=supplementary'
BUS_SHA = '686c7b116589a426e78b4bc6a1776d706584f7d03aa5823b48b23379b9b3b60e'
TRAIN_SHA = '14b857cf030804ace3154b877bfd6b9274419f7f795fbd8cc6638871e24d7af3'
STATIONS = {
    1: 'Capitol Center', 2: 'South Transfer Center',
    3: 'Northcross Transfer Center', 4: 'Highland Mall Transfer Center',
    5: 'Pavilion Park & Ride', 6: 'Saint Jacinto bus station',
}
BUS_DEFINITION = ('Observed passenger arrival to bus departure, in whole minutes. '
                  'Includes time after boarding; NOT the system\'s arrival-to-boarding target.')
TRAIN_DEFINITION = ('Self-reported waiting minutes for the respondent\'s most recent train trip; '
                    'NOT measured arrival/boarding timestamps.')
BUS_CHECK = [
    ['Passenger Volume', 'MISSING', 'Passenger observations in a partly extracted sample are not a complete past-window count.'],
    ['Vehicle Frequency', 'MISSING', 'BLH is scheduled headway. It is not an observed serving-vehicle count.'],
    ['Station / Stop', 'AVAILABLE', 'Report location code mapped using methods and Table 4.2.'],
    ['Time of Day', 'AVAILABLE', 'Derived from recorded passenger arrival, using the collector time bands.'],
    ['Day of Week', 'AVAILABLE', 'Derived from the recorded calendar date.'],
    ['Month of Year', 'AVAILABLE', 'Derived from the recorded calendar date.'],
    ['Actual Waiting Time', 'DEFINITION DIFFERENT', BUS_DEFINITION],
]
TRAIN_CHECK = [
    ['Passenger Volume', 'MISSING', 'Crowding indicators are passenger opinions, not counts.'],
    ['Vehicle Frequency', 'MISSING', 'No observed vehicle count or headway column.'],
    ['Station / Stop', 'MISSING', 'City indicators do not identify a station.'],
    ['Time of Day', 'PARTIAL', 'AM/PM peak flags do not identify the system\'s five time bands.'],
    ['Day of Week', 'MISSING', 'No individual trip date.'],
    ['Month of Year', 'MISSING', 'Survey collection dates cannot be assigned as individual trip dates.'],
    ['Actual Waiting Time', 'SELF-REPORTED', TRAIN_DEFINITION],
]


def fetch_verified(url, path, expected_sha):
    """Reuse an exact inspected source version; never parse an HTML error as data."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        partial = path.with_suffix(path.suffix + '.part')
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'TransitResearchCollector/1.0'})
            with urllib.request.urlopen(request, timeout=45) as source, partial.open('wb') as target:
                total = 0
                while chunk := source.read(1024 * 1024):
                    total += len(chunk)
                    if total > 25 * 1024 * 1024:
                        raise ValueError('Waiting-time source exceeded the 25 MiB limit.')
                    target.write(chunk)
            digest = hashlib.sha256(partial.read_bytes()).hexdigest()
            if digest != expected_sha:
                raise ValueError('Published source version changed; inspect it before changing the expected checksum.')
            partial.replace(path)
        except (OSError, urllib.error.URLError) as exc:
            raise RuntimeError(f'Could not download {path.name}. Existing datasets were not changed.') from exc
        finally:
            partial.unlink(missing_ok=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected_sha:
        raise ValueError(f'{path.name} differs from the inspected source. No automatic conversion performed.')
    return {'url': url, 'local_path': str(path), 'sha256': digest, 'bytes': path.stat().st_size}


def time_band(hour):
    if 5 <= hour <= 9: return 'Morning'
    if 10 <= hour <= 13: return 'Midday'
    if 14 <= hour <= 16: return 'Afternoon'
    if 17 <= hour <= 20: return 'Evening'
    return 'Night'


def parse_bus_line(line, pdf_page):
    """Strictly parse a complete Appendix I row; ambiguous OCR is not corrected.

    The inspected PDF has 30 observations/page on PDF pages 84--167 (last
    page has observation 2491). The source hash is pinned before extraction.
    """
    t = line.split()
    if len(t) != 19:
        raise ValueError('Incomplete or ambiguous PDF row')
    if not re.fullmatch(r'\d{1,2}/\d{1,2}/98', t[1]):
        raise ValueError('Unambiguous 1998 date not recovered')
    try:
        number = int(t[0])
        date = dt.datetime.strptime(t[1], '%m/%d/%y').date()
        arrival = dt.datetime.strptime(t[4], '%H:%M').time()
        departure = dt.datetime.strptime(t[8], '%H:%M').time()
        wait, before, after = int(t[15]), int(t[13]), int(t[14])
        location, headway = int(t[17]), int(t[12])
        ratio = float(t[16])
    except (ValueError, IndexError) as exc:
        raise ValueError('Unambiguous numeric fields or timestamps not recovered') from exc
    if not (84 <= pdf_page <= 167 and (pdf_page - 84) * 30 < number <= min((pdf_page - 83) * 30, 2491)):
        raise ValueError('Observation number conflicts with the printed page sequence')
    if location not in STATIONS or headway <= 0 or not math.isfinite(ratio):
        raise ValueError('Invalid location, headway or ratio')
    start, end = dt.datetime.combine(date, arrival), dt.datetime.combine(date, departure)
    if wait < 0 or (end - start).total_seconds() / 60 != wait or before + after != wait:
        raise ValueError('Printed wait disagrees with recorded timestamps or components')
    if abs(wait / headway - ratio) > 0.011:
        raise ValueError('Printed wait/headway ratio disagrees with the extracted fields')
    return {
        'Source Observation ID': number, 'Transport Mode': 'Bus',
        'Station / Stop': STATIONS[location], 'Observation Date': date.isoformat(),
        'Passenger Arrival (local)': start.isoformat(sep=' '),
        'Bus Departure (local)': end.isoformat(sep=' '),
        'Recorded Wait to Bus Departure (minutes)': wait,
        'Time of Day': time_band(arrival.hour), 'Day of Week': date.strftime('%A'),
        'Month of Year': date.strftime('%B'), 'Source Bus Line': t[7],
        'Scheduled Headway (minutes)': headway,
        'Source PDF Page': pdf_page, 'Printed Report Page': pdf_page - 12,
        'Measurement Definition': BUS_DEFINITION, 'Source Reference': BUS_URL,
    }


def extract_bus(path):
    from pypdf import PdfReader
    reader = PdfReader(path)
    if len(reader.pages) != 230:
        raise ValueError('Unexpected Austin report layout; stop rather than reinterpret its columns.')
    rows, excluded = [], []
    for index in range(83, 167):
        for line in (reader.pages[index].extract_text() or '').splitlines():
            # Keep every nonempty unparsed line for inspection, including split
            # fragments and headers. Exclusion line counts are not passenger counts.
            if not line.strip(): continue
            try:
                rows.append(parse_bus_line(line, index + 1))
            except ValueError as exc:
                excluded.append([index + 1, str(exc), line])
    ids = Counter(row['Source Observation ID'] for row in rows)
    if any(count > 1 for count in ids.values()):
        raise ValueError('Duplicate Austin observation IDs; inspect source extraction before proceeding.')
    missing_ids = sorted(set(range(1, 2492)) - set(ids))
    return rows, excluded, missing_ids


def extract_train(path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook['2927respondents']
        stream = sheet.iter_rows(values_only=True)
        headers = next(stream)
        required = {'ID', 'Sydney', 'Melbourn', 'Brisbane', 'Perth', 'Ampeak', 'Pmpeak', 'wtmins'}
        if not required <= set(headers):
            raise ValueError('Australian survey columns changed; no automatic remapping performed.')
        rows, ids = [], set()
        for excel_row, values in enumerate(stream, start=2):
            source = dict(zip(headers, values))
            if all(value is None for value in values): continue
            wait = source['wtmins']
            if isinstance(wait, bool) or not isinstance(wait, (int, float)) or not math.isfinite(wait) or wait < 0:
                raise ValueError(f'Invalid self-reported wait at published Excel row {excel_row}.')
            if source['ID'] is None or source['ID'] in ids:
                raise ValueError('Missing or duplicate survey ID.')
            ids.add(source['ID'])
            flags = [source[name] for name in ('Sydney', 'Melbourn', 'Brisbane', 'Perth')]
            if any(flag not in (0, 1) for flag in flags) or sum(flags) > 1:
                raise ValueError('Ambiguous city indicators in published survey.')
            city = next((name for name, flag in zip(('Sydney', 'Melbourne', 'Brisbane', 'Perth'), flags) if flag), 'Adelaide')
            rows.append({
                'Source Survey ID': source['ID'], 'Transport Mode': 'Train', 'City': city,
                'Self-reported Waiting Time (minutes)': wait,
                'Source AM Peak Indicator': source['Ampeak'], 'Source PM Peak Indicator': source['Pmpeak'],
                'Source Excel Row': excel_row, 'Measurement Definition': TRAIN_DEFINITION,
                'Source Reference': TRAIN_PAGE,
            })
        return rows
    finally:
        workbook.close()


def write_review(path, rows, checks, notes, provenance, excluded=None, missing_ids=None):
    workbook = Workbook()
    first = workbook.active
    first.title = 'Read_First'
    first.append(['SOURCE REVIEW ONLY', 'Not ready for current six-predictor system training'])
    for note in notes: first.append(['Explanation', note])
    first.append(['Matching rule', 'Do not join Austin/Australian waits to unrelated NYC or AC Transit rows.'])
    data = workbook.create_sheet('Recorded_Rows')
    if rows:
        headers = list(rows[0])
        data.append(headers)
        for row in rows: data.append([row.get(name) for name in headers])
    check = workbook.create_sheet('Predictor_Check')
    check.append(['System field', 'Availability', 'Explanation'])
    for row in checks: check.append(row)
    source = workbook.create_sheet('Provenance')
    source.append(['Field', 'Value'])
    for key, value in provenance.items(): source.append([key, str(value)])
    if excluded is not None:
        audit = workbook.create_sheet('Unparsed_PDF_Lines')
        audit.append(['PDF Page', 'Exclusion Reason', 'Original Extracted Text'])
        for row in excluded: audit.append(row)
    if missing_ids is not None:
        missing = workbook.create_sheet('Not_Extracted_IDs')
        missing.append(['Source Observation ID', 'Status'])
        for number in missing_ids: missing.append([number, 'Not recovered by strict parsing; needs source review'])
    for sheet in workbook:
        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='175C55')
        for column in sheet.columns:
            width = min(70, max(16, max(len(str(c.value or '')) for c in list(column)[:30]) + 2))
            sheet.column_dimensions[column[0].column_letter].width = width
        for row in sheet:
            for cell in row:
                # Public raw text must remain text, never a spreadsheet formula.
                if isinstance(cell.value, str) and cell.value.startswith(('=', '+', '-', '@')):
                    cell.data_type = 's'
                cell.alignment = Alignment(vertical='top', wrap_text=True)
    workbook.save(path)


def collect_waiting_sources(args, manifest):
    cache = Path(args.cache) / 'waiting_time_sources'
    out = Path(args.out) / 'waiting_time_source_review'
    out.mkdir(parents=True, exist_ok=True)
    bus_path = cache / 'austin' / '167211-1.pdf'
    train_path = cache / 'australia_train' / 'pone.0199449.s001.xlsx'
    bus_source = fetch_verified(BUS_URL, bus_path, BUS_SHA)
    train_source = fetch_verified(TRAIN_URL, train_path, TRAIN_SHA)
    bus_rows, unparsed, missing_ids = extract_bus(bus_path)
    train_rows = extract_train(train_path)
    if not bus_rows or not train_rows:
        raise ValueError('No usable source rows extracted; no review workbook created.')
    bus_notes = [
        'Salek and Machemehl (1999), Characterizing Bus Transit Passenger Wait Times, SWUTC/99/167211-1. Field observations: Austin, Texas, June-December 1998.',
        BUS_DEFINITION,
        f'{len(bus_rows)} of 2491 Appendix I non-transfer passenger observations were recovered by strict PDF text parsing. This is NOT a random sample or the full study dataset.',
        'Arrival/departure difference, printed wait components, wait/headway ratio, date, location and page/ID sequence were checked. This is not a full visual transcription audit.',
        'Ambiguous OCR and inconsistent rows were not repaired. Missing IDs and original unparsed lines are retained for review. Appendix III transfer passengers were not extracted.',
        'Passenger Volume and observed Vehicle Frequency are unavailable. Counts of these extracted rows would be biased sample counts. BLH remains Scheduled Headway.',
        'Old observations do not validate present-day performance or another city. A measured departure endpoint cannot silently replace a boarding endpoint.',
    ]
    train_notes = [
        'Paramita et al. (2018), User satisfaction with train fares: A comparative analysis in five Australian cities, PLOS ONE 13(6): e0199449. S1 Dataset.',
        'Survey collected 9 April-16 May 2013. These are collection dates, not individual trip dates.',
        TRAIN_DEFINITION,
        f'{len(train_rows)} published respondent rows, preserving original wtmins values and survey IDs. The original published workbook is also copied unchanged.',
        'The paper describes prior cleaning of the survey. This is the published analysis sample, not an unfiltered set of timestamp measurements.',
        'Station, trip date, passenger counts and vehicle counts are absent. City and crowding categories cannot be renamed to fill these fields.',
        'Both source peak flags equal to zero means neither coded peak period. No exact hour or collector time band is assigned.',
    ]
    write_review(out / 'BUS_RECORDED_WAIT_SOURCE_REVIEW.xlsx', bus_rows, BUS_CHECK, bus_notes, bus_source, unparsed, missing_ids)
    write_review(out / 'TRAIN_REPORTED_WAIT_SOURCE_REVIEW.xlsx', train_rows, TRAIN_CHECK, train_notes, train_source)
    shutil.copy2(train_path, out / 'TRAIN_ORIGINAL_PUBLISHED_DATA.xlsx')
    manifest['downloaded_sources'] = [bus_source, train_source]
    manifest['warning'] = 'Real source waits found, but definitions and missing predictors prevent current system training. No training or cross-city merge performed.'
    manifest['results'] = {
        'bus': {'rows': len(bus_rows), 'source_observations': 2491, 'not_extracted': len(missing_ids),
                'definition': BUS_DEFINITION, 'predictor_check': BUS_CHECK},
        'train': {'rows': len(train_rows), 'definition': TRAIN_DEFINITION, 'predictor_check': TRAIN_CHECK},
        'output_dir': str(out), 'registered_in_system_library': False, 'model_trained': False,
        'cross_source_merge_performed': False,
    }
    (out / 'SOURCE_AUDIT.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (out / 'READ_FIRST.txt').write_text(
        'REAL WAITING-TIME SOURCE REVIEW\n\n' + manifest['warning'] + '\n\n'
        + 'BUS\n' + '\n'.join(bus_notes) + '\n\nTRAIN\n' + '\n'.join(train_notes)
        + '\n\nOpen each workbook: Read_First, Recorded_Rows, Predictor_Check and Provenance.\n'
        + 'No artificial waiting times or predictor values were generated. Neither review file is a current system training dataset.\n', encoding='utf-8')
    print(f'Bus source observations extracted: {len(bus_rows)} / 2491; train survey responses: {len(train_rows)}')
    print(f'Waiting-time source review: {out}')
    print(manifest['warning'])
