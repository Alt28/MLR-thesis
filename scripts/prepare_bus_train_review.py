"""Consolidate supplied fallback files without presenting assigned waits as observations.

This creates a review workbook, not an analysis-ready dataset. It never changes
the source files or adds anything to the application dataset library.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime
import csv
import hashlib
import json
import shutil

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / 'Downloads'
OUT = ROOT / 'outputs/bus_train_data_review_2026-11-19'
OUT.mkdir(parents=True, exist_ok=True)
INPUTS = {mode: DOWNLOADS / f'{mode.lower()}_complete_fallback_dataset.xlsx' for mode in ['Bus', 'Train']}
FILE_NAME = 'bus_train_combined_REVIEW_ONLY.xlsx'
DESTINATION = DOWNLOADS / FILE_NAME
if DESTINATION.exists():
    raise FileExistsError(f'{DESTINATION} already exists; retain the existing review or choose a new filename.')

BUS_URL = 'https://ncts.upd.edu.ph/tssp/wp-content/uploads/2025/01/TSSP2024-Vol7-No2_01-Ollero-Vergel-and-Tiglao.pdf'
TRAIN_URL = 'https://github.com/ongods/mrt3-ridership-data'
before_hashes = {mode: hashlib.sha256(p.read_bytes()).hexdigest() for mode, p in INPUTS.items()}

# These source copies were checked against their published workbooks/PDF earlier.
bus_reference = json.loads((ROOT / 'data/edsa_busway_field_study_2023/source/extracted_tables.json').read_text(encoding='utf-8'))
dwell_lookup = {(r['direction'], r['station'].upper(), peak): r[key]
                for r in bus_reference['dwell']
                for peak, key in [('AM', 'am_peak_seconds'), ('PM', 'pm_peak_seconds')]}
station_columns = {'North Avenue': 'north_ave', 'Quezon Avenue': 'quezon_ave',
                   'GMA Kamuning': 'gma_kamuning', 'Araneta-Cubao': 'cubao',
                   'Santolan-Annapolis': 'santolan', 'Ortigas': 'ortigas',
                   'Shaw Boulevard': 'shaw_blvd', 'Boni': 'boni_ave',
                   'Guadalupe': 'guadalupe', 'Buendia': 'buendia', 'Ayala': 'ayala_ave',
                   'Magallanes': 'magallanes', 'Taft Avenue': 'taft'}
with (ROOT / 'data/mrt3_ridership_2023_2025/prepared/mrt3_hourly_2023_2025.csv').open(encoding='utf-8', newline='') as handle:
    train_reference = {(r['report_date'], r['hour_start']): r for r in csv.DictReader(handle)
                       if r['report_date'] == '2025-01-02'}

CORE = ['Traffic Condition', 'Weather Condition', 'Passenger Volume', 'Route Distance', 'Vehicle Frequency', 'Time of Day']
HEADERS = ['Review Record ID', 'Transport Mode', 'Station', 'Direction', 'Source Date', 'Source Hour',
           'Source Peak Period', 'Actual Waiting Time (min)', 'Supplied Waiting Benchmark (min)',
           'Waiting Benchmark Evidence', 'Waiting Benchmark Source', 'Waiting Benchmark Period',
           'Waiting Benchmark Mapping', *['Supplied ' + h for h in CORE],
           'Published Dwell Mean (sec)', 'Reported Station Entries', 'Checked Value Source',
           'Observed MLR Row Ready', 'Input Workbook', 'Input Sheet', 'Input Row']
workbook = Workbook()
overview = workbook.active
overview.title = 'Read Me'
checks = {}
source_rows = []
for mode, path in INPUTS.items():
    source = load_workbook(path, read_only=True, data_only=True)
    original = list(source['MLR_Complete_Fallback'].values)
    records = [dict(zip(original[0], row)) for row in original[1:]]
    sheet = workbook.create_sheet(mode)
    sheet.append(HEADERS)
    for number, record in enumerate(records, 2):
        record_date = record.get('Date')
        date_label = record_date.date().isoformat() if isinstance(record_date, datetime) else record_date
        dwell, entries = None, None
        if mode == 'Bus':
            dwell = record['Observed Dwell Time (sec)']
            assert dwell == dwell_lookup[(record['Direction'], record['Station'].upper(), record['Peak Period'])]
        else:
            entries = record['Passenger Volume']
            published = train_reference[(date_label, record['Hour'])][station_columns[record['Station']] + '_entry']
            assert float(published) == entries
        row = [f'{mode.upper()}-REF-{number-1:04d}', mode, record['Station'], record.get('Direction'),
               date_label, record.get('Hour'), record.get('Peak Period'),
               None,  # No aligned measured passenger waiting time was supplied or found.
               record['Actual Waiting Time'], record['Waiting Time Evidence Class'],
               record['Waiting Time Source'], record.get('Waiting Time Source Period'),
               record['Waiting Time Mapping Note'], *[record[h] for h in CORE], dwell, entries,
               BUS_URL if mode == 'Bus' else TRAIN_URL, 'NO - matched measured waiting time unavailable',
               path.name, 'MLR_Complete_Fallback', number]
        sheet.append(row)
    checks[mode] = {'rows': len(records), 'matched_measured_waits': 0, 'observed_mlr_ready_rows': 0,
                    'verified_against_saved_source': 'Published dwell mean' if mode == 'Bus' else 'Reported station entries',
                    'verified_values': len(records),
                    'assigned_wait_distribution': dict(Counter(str(r['Actual Waiting Time']) for r in records))}
    for name in ['Waiting_Time_Evidence', 'Fallback_Derivation_Audit', 'Source_Provenance']:
        if name in source.sheetnames:
            for number, row in enumerate(source[name].values, 1):
                if number < 4 or not any(v is not None for v in row):
                    continue
                source_rows.append([mode, path.name, name, number, *list(row)])
    source.close()

overview_rows = [
    ['BUS AND TRAIN - COMBINED DATA REVIEW'],
    ['Status', 'INCOMPLETE FOR OBSERVED WAITING-TIME MLR VALIDATION'],
    ['Prepared', '19 November 2026 (Asia/Manila)'],
    ['Bus tab', '80 station/direction/peak summaries from the supplied bus fallback workbook.'],
    ['Train tab', '234 station-hour rows from the supplied train fallback workbook; 13 stations on 2 January 2025.'],
    ['Matched measured waiting times', 'Bus: 0. Train: 0. There are no complete verified observed model rows in this package.'],
    ['What was done', 'Consolidated both supplied workbooks; checked 80 bus dwell means and 234 train entry counts against saved source copies.'],
    ['Waiting-time correction', 'Values previously named Actual Waiting Time are retained as Supplied Waiting Benchmark. Actual Waiting Time (min) is blank because matched measurements are absent.'],
    ['Supplied predictor columns', 'These preserve the values in the input files. Their presence does not establish that they were measured for the row; see Field Review.'],
    ['What this file supports', 'Inspecting source values, estimates and missing evidence separately. It is not an import-ready research dataset.'],
    ['Model results', 'No models were trained and no MSE/RMSE, prediction-accuracy or station-classification results were produced.'],
    ['Bus provenance', 'Dwell means match Table 4, pp. 11-12, of the Ollero/Vergel/Tiglao EDSA Busway paper. These are aggregate means, not individual passenger episodes.'],
    ['Train provenance', 'Entry counts match the saved MRT-3 report conversion. The publisher attributes the originals to DOTr FOI; an agency release letter is not included. Matching a copy does not independently authenticate every count.'],
    ['How a valid merge would work', 'Start with recorded waiting episodes. Match the same service, station, direction, date and relevant observation window. Keep unmatched fields missing; check duplicate keys and units.'],
    ['Passenger volume definition', 'The current model uses arrivals for the same service/direction in the preceding 60 minutes. Station entry totals and inferred boarding activity do not automatically satisfy that definition.'],
    ['Source date limits', 'Bus data are peak-period survey summaries without individual episode dates. Train traffic, weather and frequency substitutes are not matched actual observations for each row.'],
    ['Preservation', 'The input workbooks were not edited. Cached values were copied without carrying formulas into this workbook. Original input filenames, sheet names and row numbers identify every row.'],
    ['File organization', 'Bus and Train are separate tabs in this one workbook. Field Review and Supplied Source Notes document the limitations.'],
    ['Search result', 'The checked public sources did not provide complete aligned passenger-wait records. See Access Checks; this is not a claim that no such records exist anywhere.'],
]
for row in overview_rows:
    overview.append(row)
overview.column_dimensions['A'].width = 30
overview.column_dimensions['B'].width = 110
for row in overview:
    for cell in row:
        cell.alignment = Alignment(wrap_text=True, vertical='top')
    overview.row_dimensions[row[0].row].height = 52 if row[0].row > 1 else 30
overview['A1'].font = Font(size=16, bold=True, color='17365D')
overview['B2'].font = Font(bold=True, color='9C0006')
overview.freeze_panes = 'B4'

review = workbook.create_sheet('Field Review')
review.append(['Mode', 'Field', 'Finding', 'How to interpret it'])
for row in [
    ['Bus', 'Actual Waiting Time', 'All 80 targets were assigned 4, 5, 6.5 or 20 minutes using benchmarks.', 'No matched passenger arrival-to-boarding measurements.'],
    ['Bus', 'Traffic Condition', 'Heavy was assigned to all 80 rows.', 'Not measured traffic; no within-file traffic variation.'],
    ['Bus', 'Weather Condition', 'Clear for AM; Cloudy for PM.', 'Assigned from a general weather context, not observed at each row. Weather and period cannot be separated statistically here.'],
    ['Bus', 'Passenger Volume', 'Calculated by reversing a dwell-time regression and multiplying by bus counts.', 'Estimated passenger activity, not observed arrivals in the preceding hour.'],
    ['Bus', 'Route Distance', 'Station positions distributed evenly over the direction route length.', 'Not measured station distances and not the total service route length required by the current model.'],
    ['Bus', 'Vehicle Frequency', 'One published peak hour reused across a wider peak period and stations.', 'The source count is published; its assignment to each summary is not an aligned event observation.'],
    ['Bus', 'Time of Day', 'AM/PM survey summaries.', 'No exact passenger arrival timestamps or dates supplied.'],
    ['Train', 'Actual Waiting Time', '224 rows assigned 4 minutes; 10 use historical 2014 averages on 2025 rows.', 'Different periods and definitions; none establish the actual wait for the 2025 row.'],
    ['Train', 'Traffic Condition', 'Citywide 2025 Thursday travel-time profile mapped to categories.', 'Annual profile substitute, not exact date/station traffic.'],
    ['Train', 'Weather Condition', 'Cloudy for all 234 rows.', 'Forecast-based substitute with no variation; an additional cited virtual-airline page is not an authenticated weather archive.'],
    ['Train', 'Passenger Volume', 'All 234 supplied values match the saved published hourly station-entry table.', 'Reported aggregate entries; direction and preceding-window correspondence are not established.'],
    ['Train', 'Route Distance', 'Cumulative station position from North Avenue.', 'Different from the total service route length required by the current model.'],
    ['Train', 'Vehicle Frequency', 'Derived from a schedule rather than observed 2025 dispatch.', 'The supplied schedule also differs from the current cited page; a dated archived schedule would be needed.'],
    ['Train', 'Time of Day', 'Supplied labels derived from hours.', 'Can be derived legitimately, but category boundaries must agree with the study protocol.'],
]:
    review.append(row)

notes = workbook.create_sheet('Supplied Source Notes')
notes.append(['Mode', 'Input Workbook', 'Input Sheet', 'Input Row', *[f'Supplied Column {i}' for i in range(1, 9)]])
for row in source_rows:
    notes.append(row)

access = workbook.create_sheet('Access Checks')
access.append(['Source', 'URL', 'Checked 19 November 2026', 'Consequence'])
for row in [
    ['EDSA Busway 2025 study', 'https://www.mdpi.com/2673-7590/5/4/178', 'Data Availability Statement says underlying data are available from the corresponding author on reasonable request, with possible restrictions.', 'The public article does not supply the matched rows needed here.'],
    ['MRT-3 waiting study', 'https://digitalcommons.usf.edu/jpt/vol19/iss4/9/', 'Landing page describes historical surveys. PDF request returned HTTP 403.', 'No complete aligned raw dataset obtained.'],
    ['Related MRT-3 field study', 'https://easts.info/on-line/proceedings/vol10/pdf/1361.pdf', 'Public paper describes surveys in 2013/2014 and publishes figures and summaries.', 'Historical values cannot be assigned to 2025 rows as actual waiting times.'],
    ['SafeTravelPH inventory', 'https://www.safetravelph.org/data-inventory', 'Lists bus trip, boarding/alighting and ridership data.', 'Listing alone does not establish access or passenger queue-arrival measurements.'],
    ['SafeTravelPH linked folder', 'https://drive.google.com/drive/folders/1HY1BDSVR6ppVE4SJCZFwDY-ZK1d0nzqk', 'Web redirected to sign-in; connected Drive metadata returned 404 and folder listing returned no files.', 'No underlying files obtained with available access.'],
    ['MRT-3 four-minute source', 'https://www.pna.gov.ph/articles/1171694', '2022 article describes 3.5-4-minute train headways.', 'This does not establish passenger waiting durations in 2025.'],
]:
    access.append(row)

for sheet in workbook:
    if sheet.title == 'Read Me':
        continue
    sheet.freeze_panes = 'D2' if sheet.title in INPUTS else 'A2'
    sheet.auto_filter.ref = sheet.dimensions
    sheet.sheet_view.zoomScale = 85
    sheet.row_dimensions[1].height = 42
    for cell in sheet[1]:
        cell.fill = PatternFill('solid', fgColor='17365D')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = Alignment(wrap_text=True, vertical='center')
    for col, cell in enumerate(sheet[1], 1):
        sheet.column_dimensions[get_column_letter(col)].width = 28 if sheet.title in INPUTS else 48
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical='top', wrap_text=True)
            if isinstance(cell.value, str) and cell.value.startswith('https://') and ' | ' not in cell.value:
                cell.hyperlink = cell.value
                cell.font = Font(color='0563C1', underline='single')
        sheet.row_dimensions[row[0].row].height = 60
    if sheet.title in INPUTS:
        sheet.sheet_properties.tabColor = '1F7A8C' if sheet.title == 'Bus' else '4472C4'
        for row in sheet.iter_rows(min_row=2):
            row[7].fill = PatternFill('solid', fgColor='FCE4D6')
            row[8].fill = PatternFill('solid', fgColor='FFF2CC')

path = OUT / FILE_NAME
workbook.save(path)
check = load_workbook(path, read_only=True, data_only=True)
for mode, expected in [('Bus', 80), ('Train', 234)]:
    rows = list(check[mode].values)
    assert len(rows) - 1 == expected
    assert all(row[7] is None for row in rows[1:]), 'No benchmark may be labeled an observed wait.'
    assert len({row[0] for row in rows[1:]}) == expected
    original = load_workbook(INPUTS[mode], read_only=True, data_only=True)
    source_data = list(original['MLR_Complete_Fallback'].values)[1:]
    for output_row, input_row in zip(rows[1:], source_data):
        assert output_row[8] == input_row[6]
        assert output_row[13:19] == input_row[:6]
    original.close()
check.close()
for mode, original in INPUTS.items():
    assert hashlib.sha256(original.read_bytes()).hexdigest() == before_hashes[mode]
shutil.copyfile(path, DESTINATION)
assert path.read_bytes() == DESTINATION.read_bytes()
audit = {'output': str(DESTINATION), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
         'inputs': {mode: {'file': str(INPUTS[mode]), 'sha256': before_hashes[mode]} for mode in INPUTS},
         'checks': checks, 'input_files_unchanged': True, 'assigned_values_preserved_under_explicit_labels': True,
         'complete_observed_dataset_obtained': False, 'application_library_changed': False}
(OUT / 'verification.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
print(json.dumps(audit, indent=2))
