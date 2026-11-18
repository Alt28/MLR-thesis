"""Package extracted Philippine bus survey summaries without inventing observations."""
from pathlib import Path
from datetime import datetime
import csv
import hashlib
import json
from zipfile import ZipFile, ZIP_DEFLATED

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'prepared'
OUT.mkdir(exist_ok=True)
SOURCE_URL = 'https://ncts.upd.edu.ph/tssp/wp-content/uploads/2025/01/TSSP2024-Vol7-No2_01-Ollero-Vergel-and-Tiglao.pdf'
source = json.loads((ROOT / 'source/extracted_tables.json').read_text(encoding='utf-8'))
pdf = ROOT / 'source/TSSP2024-Vol7-No2_01-Ollero-Vergel-and-Tiglao.pdf'
if pdf.exists():
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == source['source_sha256']

dwell = []
for row in source['dwell']:
    for label, key in [('AM Peak', 'am_peak_seconds'), ('PM Peak', 'pm_peak_seconds')]:
        dwell.append(dict(station=row['station'], direction=row['direction'], peak_period=label,
                          mean_dwell_seconds=row[key], aggregation='published_survey_mean',
                          source_table=4, source_page=row['source_page'], source_url=SOURCE_URL))
counts = []
for row in source['bus_counts']:
    start, end = [datetime.strptime(t, '%I:%M %p').strftime('%H:%M') for t in row['time'].split(' - ')]
    for direction, key, origin, destination in [('Southbound', 'southbound', 'Monumento', 'PITX'),
                                               ('Northbound', 'northbound', 'PITX', 'Monumento')]:
        counts.append(dict(direction=direction, origin=origin, destination=destination,
                           interval_start=start, interval_end=end, reported_bus_count=row[key],
                           observation_date='', aggregation='published_hour_direction_summary',
                           source_table=3, source_page=10, source_url=SOURCE_URL))
coverage = [dict(operator=r['operator'], survey_date=datetime.strptime(r['date'], '%B %d, %Y').date().isoformat(),
                 buses_deployed=r['buses'], total_roundtrips=r['roundtrips'], source_table=2,
                 source_page=9, source_url=SOURCE_URL) for r in source['survey_coverage']]
tables = [('Dwell means', 'edsa_busway_dwell_means_2023.csv', dwell),
          ('Reported bus counts', 'edsa_busway_reported_bus_counts.csv', counts),
          ('Survey coverage', 'edsa_busway_survey_coverage_2023.csv', coverage)]
assert [len(rows) for _, _, rows in tables] == [80, 12, 9]
assert len({(r['station'], r['direction'], r['peak_period']) for r in dwell}) == 80
assert all(isinstance(r['mean_dwell_seconds'], int) and r['mean_dwell_seconds'] > 0 for r in dwell)

workbook = Workbook()
notes = workbook.active
notes.title = 'Read me first'
for line in (ROOT / 'README.md').read_text(encoding='utf-8').splitlines():
    notes.append([line])
notes.column_dimensions['A'].width = 115
for row in notes:
    row[0].alignment = Alignment(wrap_text=True, vertical='top')
    if row[0].value:
        notes.row_dimensions[row[0].row].height = max(18, 15 * ((len(row[0].value) // 110) + 1))

for title, filename, rows in tables:
    headers = list(rows[0])
    with (OUT / filename).open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    sheet = workbook.create_sheet(title)
    sheet.append(headers)
    for row in rows:
        sheet.append([row[h] for h in headers])
    sheet.freeze_panes = 'A2'
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='164E63')
    for col, header in enumerate(headers, 1):
        sheet.column_dimensions[get_column_letter(col)].width = min(48, max(20, len(header) + 3))

excel = OUT / 'EDSA_BUSWAY_SURVEY_REFERENCE_2023.xlsx'
workbook.save(excel)
check = load_workbook(excel, read_only=True, data_only=True)
for title, filename, rows in tables:
    headers = list(rows[0])
    assert list(check[title].values)[1:] == [tuple(r[h] if r[h] != '' else None for h in headers) for r in rows]
check.close()
manifest = dict(source_url=SOURCE_URL, retrieved_date='2026-11-18',
                source_filename=pdf.name, source_sha256=source['source_sha256'],
                prepared_files={p.name: dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size)
                                for p in sorted(OUT.iterdir()) if p.is_file()})
(ROOT / 'download_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
verification = dict(source['verification'], prepared_row_counts={filename: len(rows) for _, filename, rows in tables},
                    unique_station_direction_pairs=40, workbook_matches_extracted_values=True,
                    passenger_waiting_time_available=False, complete_six_predictors_available=False)
(ROOT / 'verification.json').write_text(json.dumps(verification, indent=2), encoding='utf-8')
members = [*sorted(OUT.iterdir()), ROOT / 'README.md', ROOT / 'download_manifest.json',
           ROOT / 'verification.json', ROOT / 'source/extracted_tables.json',
           ROOT / 'extract_source.py', ROOT / 'prepare.py']
with ZipFile(ROOT / 'EDSA_BUSWAY_SURVEY_REFERENCE_PACKAGE.zip', 'w', ZIP_DEFLATED) as archive:
    for path in members:
        archive.write(path, path.relative_to(ROOT).as_posix())
print(json.dumps(verification, indent=2))
