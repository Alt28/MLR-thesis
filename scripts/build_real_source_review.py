"""Package source records and a conservative context join; never invent model inputs."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(r'C:\Users\clarence\Downloads\real_philippine_transport_sources_2026-11-20')
MRT = ROOT / 'data/mrt3_ridership_2023_2025'
BUS = ROOT / 'data/edsa_busway_field_study_2023'
WEATHER = OUT / 'raw/rpll_observed_weather_july_2023.csv'
MRT_URL = 'https://github.com/ongods/mrt3-ridership-data/tree/f4f1b40413efef0e7381892f67e43876ea3a99f5'
BUS_URL = 'https://ncts.upd.edu.ph/tssp/wp-content/uploads/2025/01/TSSP2024-Vol7-No2_01-Ollero-Vergel-and-Tiglao.pdf'
WEATHER_URL = 'https://mesonet.agron.iastate.edu/request/download.phtml?network=PH__ASOS'


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(line for line in stream if not line.startswith('#')))


def sheet(book, name, rows):
    ws = book.create_sheet(name)
    keys = list(rows[0])
    ws.append(keys)
    for row in rows:
        ws.append([row.get(k) for k in keys])
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='173F43')
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    for column in ws.columns:
        letter = column[0].column_letter
        ws.column_dimensions[letter].width = min(72, max(18, len(str(column[0].value)) + 3))
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical='top', wrap_text=True)
    return ws


def workbook(path, notes, tables):
    book = Workbook()
    book.remove(book.active)
    sheet(book, 'READ_FIRST', [{'Item': k, 'Explanation': v} for k, v in notes])
    for name, rows in tables:
        sheet(book, name, rows)
    book.save(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    weather = read_csv(WEATHER)
    weather_index = defaultdict(list)
    for line, row in enumerate(weather, start=2):
        weather_index[row['valid']].append((line, row))
    hourly = read_csv(MRT / 'prepared/mrt3_hourly_2023_2025.csv')
    selected = [r for r in hourly if r['report_date'].startswith('2023-07-')
                and r['date_in_sheet_month'] == 'true'
                and r['hour_label_matches_sequence'] == 'true'
                and 1 <= int(r['hour_sequence']) <= 21]
    assert len(selected) == 651
    joined = []
    for row in selected:
        key = row['report_date'] + ' ' + row['hour_start']
        candidates = weather_index.get(key, [])
        match = candidates[0][1] if len(candidates) == 1 else {}
        joined.append({
            'Record ID': 'TAFT-' + row['report_date'] + '-' + row['hour_sequence'],
            'Transport Mode': 'Train', 'Station': 'MRT-3 Taft Avenue',
            'Report Date': row['report_date'], 'Reported Hour': row['time_label'],
            'Join Timestamp (Asia/Manila)': key,
            'Reported Station Entries': row['taft_entry'],
            'Reported Station Exits': row['taft_exit'],
            'Actual Waiting Time': None,
            'Weather Join Status': 'Exact timestamp; airport context only' if match else 'No unique exact timestamp match',
            'Airport Weather Station': match.get('station'),
            'Airport Weather Timestamp': match.get('valid'),
            'Airport Weather Codes (raw)': match.get('wxcodes'),
            'Airport Sky Cover 1 (raw)': match.get('skyc1'),
            'Airport METAR (raw)': match.get('metar'),
            'Weather CSV Record': candidates[0][0] if match else None,
            'Ridership Source Workbook': row['source_workbook'],
            'Ridership Source Sheet': row['source_sheet'],
            'Ridership Source Row': row['source_row'],
            'Ridership Source': MRT_URL, 'Weather Source': WEATHER_URL,
        })
    assert len({r['Record ID'] for r in joined}) == len(selected)
    assert all(r['Actual Waiting Time'] is None for r in joined)
    assert [(r['Reported Station Entries'], r['Reported Station Exits']) for r in joined] == [(r['taft_entry'], r['taft_exit']) for r in selected]
    assert all(not r['Airport Weather Timestamp'] or r['Airport Weather Timestamp'] == r['Join Timestamp (Asia/Manila)'] for r in joined)
    matches = sum(bool(r['Airport Weather Timestamp']) for r in joined)
    fields = [
        {'System Field': 'Traffic Condition', 'Train Status': 'Missing', 'Bus Status': 'Missing'},
        {'System Field': 'Weather Condition', 'Train Status': 'Airport context only; not a station observation or approved model category', 'Bus Status': 'Cannot join: bus count dates absent'},
        {'System Field': 'Passenger Volume', 'Train Status': 'Station entries available, but no direction-specific preceding-hour passenger arrivals', 'Bus Status': 'No matching passenger-arrival counts in the extracted tables'},
        {'System Field': 'Route Distance', 'Train Status': 'Not supplied in this source', 'Bus Status': 'Route endpoints supplied; route length not in these extracted tables'},
        {'System Field': 'Vehicle Frequency', 'Train Status': 'No observed train service event log', 'Bus Status': '12 published hourly direction counts, without observation dates; not matched stop-hour logs'},
        {'System Field': 'Time of Day', 'Train Status': 'Reported hourly intervals retained', 'Bus Status': 'Published hourly / AM-PM intervals retained'},
        {'System Field': 'Actual Waiting Time', 'Train Status': 'Blank; optional for predictions, required for training/evaluation', 'Bus Status': 'Absent; bus dwell duration is not passenger waiting time'},
    ]
    train_notes = [
        ('Status', 'Recorded-source reference data with an airport-weather context join. NOT a complete six-predictor model input. No simulated values or waiting times were added.'),
        ('Coverage', f'MRT-3 Taft Avenue, July 2023; 651 reported hourly slots (03:00 through 23:59), {matches} unique exact weather timestamp matches.'),
        ('Ridership origin', 'Publisher attributes the original workbooks to DOTr FOI. The public package has no release letter or request number. Existing conversion checks match source cells; annual-total consistency does not authenticate every record.'),
        ('Counting definition', 'Entries/exits are station aggregates without train direction. They are not individual passenger waiting episodes and are not silently renamed Passenger Volume.'),
        ('Join rule', 'One weather observation at exactly the rail interval start, using Asia/Manila time. No nearest-time fill, no averaging, no future report, no duplication of rail rows. Multiple exact weather records leave the weather blank.'),
        ('Location limitation', 'RPLL is Manila airport. Airport conditions are retained as contextual observations, not represented as weather measured at Taft Avenue. No Weather Condition model category was fabricated.'),
        ('Date limitation', 'After-midnight slots (00:00-02:59) and mislabeled slots are excluded because source reporting-date conventions are unresolved. Reporting labels for 03:00-23:59 are interpreted as local Manila time.'),
        ('Missing values', 'Source blanks and recorded zeros are distinct and unchanged. Blank weather codes do not establish clear weather; precipitation amounts are not supplied for non-US sites.'),
        ('Actual Waiting Time', 'Left blank. Predicting these rows still requires all six valid predictors and previously trained models. This workbook cannot establish waiting-time accuracy.'),
        ('Full original package', str(MRT / 'prepared/MRT3_RIDERSHIP_2023_2025.xlsx')),
        ('Ridership source', MRT_URL), ('Weather source', WEATHER_URL),
        ('Retrieved/check date', '2026-11-20'),
    ]
    train_path = OUT / 'train_recorded_sources_and_weather_REFERENCE.xlsx'
    workbook(train_path, train_notes, [('Taft July Context Join', joined), ('Six Predictor Check', fields), ('Airport Weather Source', weather)])
    counts = read_csv(BUS / 'prepared/edsa_busway_reported_bus_counts.csv')
    dwell = read_csv(BUS / 'prepared/edsa_busway_dwell_means_2023.csv')
    coverage = read_csv(BUS / 'prepared/edsa_busway_survey_coverage_2023.csv')
    assert len(counts) == 12 and len(dwell) == 80 and len(coverage) == 9
    assert all(not r['observation_date'] for r in counts)
    bus_notes = [
        ('Status', 'Published measured-survey summaries, not simulated scenario outputs. REFERENCE ONLY; not a complete six-predictor input dataset.'),
        ('Source', 'Ollero, Vergel and Tiglao (2024), A Microsimulation Model of An Exclusive Bus Lane: The Case of EDSA Busway, Philippine Transportation Journal 7(2), pp. 1-40.'),
        ('Bus counts', '12 direction/hour summaries from Table 3, checked against Table 5 Actual counts. The source gives no exact observation date for each count.'),
        ('Dwell means', '80 station/direction/peak-period means in seconds from Table 4. Dwell is the time a bus stops; it is not a passenger waiting duration.'),
        ('Survey coverage', '9 operator/date rows covering 8 dates, 29 surveyed bus deployments and 105 roundtrips. These are survey coverage, not passenger volume.'),
        ('Merge decision', 'No weather or train-ridership merge. Matching hourly counts to any one coverage date would invent an unsupported relationship; train entries do not measure bus passenger arrivals.'),
        ('Needed to predict', 'All six predictors matched to bus stop/route/direction and observation period. Waiting time can be absent for prediction, but other missing predictors remain required.'),
        ('Publisher PDF', BUS_URL), ('Checked', '2026-11-20'),
    ]
    bus_path = OUT / 'bus_recorded_survey_sources_REFERENCE.xlsx'
    workbook(bus_path, bus_notes, [('Reported Bus Counts', counts), ('Bus Dwell Means - NOT Wait', dwell), ('Survey Coverage', coverage), ('Six Predictor Check', fields)])
    # Verify saved artifacts, including the deliberately blank target and source counts.
    book = load_workbook(train_path, read_only=True)
    saved = list(book['Taft July Context Join'].values)
    target = saved[0].index('Actual Waiting Time')
    assert len(saved) - 1 == 651 and all(r[target] is None for r in saved[1:])
    book.close()
    check = load_workbook(bus_path, read_only=True)
    assert check['Reported Bus Counts'].max_row - 1 == 12
    check.close()
    manifest = {'checked': '2026-11-20', 'train_rows': 651, 'unique_exact_weather_matches': matches,
                'bus_count_summaries': 12, 'bus_dwell_means': 80, 'model_ready_rows': 0,
                'verification': ['No invented waits', 'Rail source counts preserved', 'Join does not multiply rail rows', 'Exact same timestamp for matched weather', 'Undated bus counts not joined'],
                'files': []}
    for path in (train_path, bus_path, WEATHER, MRT / 'prepared/mrt3_hourly_2023_2025.csv', BUS / 'prepared/edsa_busway_reported_bus_counts.csv'):
        manifest['files'].append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    (OUT / 'verification.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (OUT / 'START_HERE.txt').write_text(
        'REAL SOURCE REVIEW - 20 NOVEMBER 2026\n\n'
        'There is no verified complete six-predictor prediction file in this package. Model-ready rows: 0.\n'
        'The two REFERENCE workbooks contain published source records and explain their limitations.\n'
        f'Train: 651 Taft Avenue hourly slots, July 2023; {matches} exact matches to observed Manila airport weather. Airport context is not a station weather measurement.\n'
        'Bus: 12 published hourly direction counts, 80 dwell means and 9 survey-coverage rows. Exact dates for count summaries are absent, so no weather merge is made.\n'
        'Actual waiting time may be blank for forecasting, but all six predictors must still be valid and aligned. Training and accuracy evaluation still require recorded waiting times.\n'
        'Nothing was imported into the application or added to its ready-to-use dataset library. No predictions or accuracy figures were generated from these incomplete records.\n'
        'Read READ_FIRST and Six Predictor Check in each workbook. Source URLs and original source-row references are included.\n'
        'The rejected_candidates folder contains an inspected STPH sample with TEST identifiers, mixed regions and unresolved mode/timezone. It is NOT verified recorded bus data.\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k != 'files'}, indent=2))
    print(train_path)
    print(bus_path)


if __name__ == '__main__':
    main()
