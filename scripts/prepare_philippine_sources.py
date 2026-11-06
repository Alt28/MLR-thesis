"""Prepare auditable supporting datasets; do not invent missing MLR observations.

Run from the project root. PDF extraction additionally requires pypdf (already
available in the development environment). This script performs no downloads.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.measurements import scheduled_frequency
from src.config import PREDICTORS, TARGET

BASE = ROOT / 'data' / 'philippine_sources'
GTFS = BASE / 'raw' / 'sakay_gtfs'
PDF_URL = 'https://mediaworldadvertising.b-cdn.net/wp-content/uploads/2024/06/RIDERSHIP-REPORT-2024.pdf'


def prepare():
    from pypdf import PdfReader
    derived = BASE / 'prepared'
    derived.mkdir(parents=True, exist_ok=True)
    frequencies = pd.read_csv(GTFS / 'frequencies.txt')
    trips = pd.read_csv(GTFS / 'trips.txt')
    routes = pd.read_csv(GTFS / 'routes.txt')
    calendar = pd.read_csv(GTFS / 'calendar.txt')
    joined = frequencies.merge(trips, on='trip_id', validate='many_to_one').merge(routes, on='route_id', validate='many_to_one').merge(calendar, on='service_id', validate='many_to_one')
    if len(joined) != len(frequencies):
        raise ValueError('A source join lost frequency records; inspect keys before using the output.')
    joined['Scheduled Frequency (vehicles/hour)'] = joined.headway_secs.map(scheduled_frequency)
    joined['Frequency Basis'] = 'Historical scheduled service; not observed vehicle arrivals'
    joined['Mode Interpretation'] = joined.route_type.map({2: 'Rail', 3: 'Road transit (bus/jeepney; confirm mode)'})
    joined['Source URL'] = 'https://github.com/sakayph/gtfs'
    columns = ['trip_id','route_id','agency_id','route_short_name','route_long_name','route_type','Mode Interpretation','direction_id','service_id','start_time','end_time','headway_secs','exact_times','Scheduled Frequency (vehicles/hour)','Frequency Basis','start_date','end_date','Source URL']
    schedule = joined[columns]
    schedule.to_csv(derived / 'metro_manila_historical_scheduled_frequency.csv', index=False)

    records = []
    pdf = BASE / 'raw' / 'mrt3_ridership_april_2024_mirror.pdf'
    for number, page in enumerate(PdfReader(pdf).pages, start=1):
        text = page.extract_text(extraction_mode='layout')
        page_records = []
        for line in text.splitlines():
            match = re.match(r'^\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),(\d{2} [A-Za-z]{3} \d{2})\s+(.*)$', line)
            if not match:
                continue
            counts = re.match(r'(\d[\d,]*)\s+(\d[\d,]*)(?:\s|$)', match[2])
            page_records.append({'Date': pd.to_datetime(match[1], format='%d %b %y').date().isoformat(),
                'MRT3 System Entries': int(counts[1].replace(',','')) if counts else None,
                'MRT3 System Exits': int(counts[2].replace(',','')) if counts else None,
                'Coverage': 'Whole MRT-3 line; daily aggregate',
                'Source Status': 'Reported' if counts else 'Blank in source; not imputed',
                'Source Page': number, 'Source URL': PDF_URL})
        totals = re.search(r'^\s*Total\s+([\d,]+)\s+([\d,]+)\s*$', text, re.M)
        if not totals or not page_records:
            raise ValueError('PDF layout changed; manual source verification is required.')
        for key, total in zip(['MRT3 System Entries','MRT3 System Exits'], totals.groups()):
            assert sum(row[key] or 0 for row in page_records) == int(total.replace(',','')), 'Extracted rows disagree with published monthly total.'
        records.extend(page_records)
    ridership = pd.DataFrame(records).sort_values('Date')
    assert len(ridership) == 121 and ridership.Date.is_unique
    ridership.to_csv(derived / 'mrt3_daily_ridership_jan_apr_2024.csv', index=False)

    gaps = pd.DataFrame([
        ['MRT3 daily ridership','Real published aggregate, third-party copy','Daily system entries/exits','All six aligned predictors and measured passenger wait','Not ready for MLR'],
        ['Sakay GTFS','Historical schedule, calendar ends 2020-06-30','Routes, operating windows, scheduled headway/rate','Observed frequency, passenger demand, traffic, weather, measured wait','Not ready for MLR'],
    ], columns=['Dataset','Evidence Type','Available','Missing / Limitation','Import Readiness'])
    with pd.ExcelWriter(derived / 'philippine_supporting_datasets.xlsx') as writer:
        gaps.to_excel(writer, sheet_name='READ_ME_FIRST', index=False)
        ridership.to_excel(writer, sheet_name='MRT3_Daily_Ridership', index=False)
        schedule.to_excel(writer, sheet_name='Historical_GTFS_Frequency', index=False)

    headers = ['Record ID', *PREDICTORS, TARGET, 'Transport Mode','Station','Route','Direction',
               'Passenger Arrival Timestamp','Boarding Timestamp','Frequency Window Start','Frequency Window End',
               'Serving Vehicle Count','Frequency Basis','Passenger Count Window Start','Passenger Count Window End',
               'Source Record Reference','Weather Source','Traffic Source']
    empty = pd.DataFrame(columns=headers)
    empty.to_csv(ROOT / 'data' / 'recorded_observation_template.csv', index=False)
    with pd.ExcelWriter(ROOT / 'data' / 'recorded_observation_template.xlsx') as writer:
        empty.to_excel(writer, sheet_name='Observations', index=False)
        pd.DataFrame([
            ['Vehicle Frequency','vehicles/hour','Revised study measure: serving events in the preceding 60 minutes at the same stop/route/direction; count buses or train sets, not rail cars.'],
            ['Route Distance','km','Total route length in the relevant direction.'],
            ['Actual Waiting Time','minutes','Observed boarding timestamp minus passenger arrival timestamp. Never use half a headway or an arrival prediction.'],
            ['Passenger Volume','passengers','Observed arrivals for the same service/stop/direction during the preceding 60 minutes.'],
            ['Time of Day','category','From passenger arrival timestamp; document fixed period definitions before analysis.'],
            ['Traffic Condition','category','Independent observed condition at prediction time; do not infer it from target waiting time.'],
            ['Weather Condition','category','Observed weather aligned to station and prediction time.'],
        ], columns=['Variable','Unit','Definition']).to_excel(writer, sheet_name='Sources_Methodology', index=False)
        pd.DataFrame({'Instructions': [
            'EMPTY COLLECTION TEMPLATE: no observations are supplied or fabricated.',
            'See docs/MEASUREMENT_AMENDMENT.md for the proposed observation protocol.',
            'Use Asia/Manila timestamps with +08:00 offset. All predictor windows end at or before passenger arrival.',
            'Vehicle Frequency = 60 * Serving Vehicle Count / window length in minutes; keep 60-minute windows for this protocol.',
            'Do not mix scheduled and observed rates in one final experiment. Preserve basis and source records.',
            'Raw vehicle counts and timestamps are metadata; compute the seven required columns before uploading.',
        ]}).to_excel(writer, sheet_name='Instructions', index=False)
    manifest = {'retrieved_date': '2026-11-06', 'scope': 'Philippines only; supporting records, not complete MLR data',
                'ridership_rows': len(ridership), 'ridership_blank_days': int(ridership['MRT3 System Entries'].isna().sum()),
                'schedule_rows': len(schedule), 'calendar_end': str(calendar.end_date.max()),
                'files': {str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.rglob('*') if p.is_file() and p.name != 'manifest.json'}}
    (BASE / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k != 'files'}, indent=2))


if __name__ == '__main__':
    prepare()
