"""Join published Chilean passenger-wait survey tables using their original keys.

These are source-review exports, not six-predictor system training packages.
Survey waits, whole-trip times and household dates retain their actual meanings.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
from pathlib import Path

from etl_waiting_sources import fetch_verified, write_review


SOURCE_PAGE = 'https://www.sectra.gob.cl/info-territorial/region-de-valparaiso/'
SOURCE_URL = 'https://drive.google.com/file/d/1SGLzQYpFRLATRjTTpSbkWrCpUplCDtnt/view'
DOWNLOAD_URL = 'https://drive.google.com/uc?export=download&id=1SGLzQYpFRLATRjTTpSbkWrCpUplCDtnt'
SOURCE_SHA = '4cbb68a27c3908144a984aa0eafe5bd28e63a083145503aa8cd0edceff885a2a'
DATABASE_NAME = 'BD_EOD_GV_2014_(27_4_2016).accdb'
TABLE_COUNTS = {'Etapa': 64670, 'Viaje': 61609, 'Hogar': 8776,
                'ModoEtapa': 17, 'EstacionMetro Ori': 20, 'RecorridoBus': 107}
TRIP_KEY = ('Hogar', 'Persona', 'Viaje')
STAGE_KEY = (*TRIP_KEY, 'Etapa')
DAYS = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday',
        5: 'Friday', 6: 'Saturday', 7: 'Sunday'}
DEFINITION = ('Reported waiting minutes for a journey stage (Etapa.TiempoEspera) '
              'in the SECTRA Greater Valparaiso origin-destination survey. '
              'Not sensor-measured arrival-to-boarding timestamps.')


def records(columns):
    """Fail on inconsistent parser output instead of truncating with zip()."""
    if not columns or len({len(v) for v in columns.values()}) != 1:
        raise ValueError('Missing table or unequal parsed column lengths.')
    return [dict(zip(columns, row)) for row in zip(*columns.values())]


def integer(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('A join identifier is missing or is not numeric.')
    if not math.isfinite(value) or value < 1 or int(value) != value:
        raise ValueError('A join identifier is invalid.')
    return int(value)


def key(row, names):
    return tuple(integer(row.get(name)) for name in names)


def unique_index(rows, names):
    result = {}
    for row in rows:
        value = key(row, names)
        if value in result:
            raise ValueError(f'Duplicate source key for {names}; join would multiply rows.')
        result[value] = row
    return result


def clock_text(value):
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.time().isoformat()
    # Access time-only fields have an 1899 base date; do not treat it as a trip date.
    return dt.datetime.fromisoformat(str(value)).time().isoformat()


def merge_survey(tables):
    stages, trips, households = (tables[n] for n in ('Etapa', 'Viaje', 'Hogar'))
    unique_index(stages, STAGE_KEY)
    trip_index = unique_index(trips, TRIP_KEY)
    household_index = unique_index(households, ('Hogar',))
    stations = unique_index(tables['EstacionMetro Ori'], ('Id',))
    routes = unique_index(tables['RecorridoBus'], ('ID',))
    modes = unique_index(tables['ModoEtapa'], ('id modo',))
    result = {'Bus': [], 'Train': []}
    audit = {'all_source_stages': len(stages), 'selected_stages': 0,
             'matched_trip_rows': 0, 'matched_household_rows': 0,
             'missing_station_codes': 0, 'missing_bus_route_codes': 0,
             'other_transport_stage_rows_excluded': 0}
    for stage in stages:
        mode = integer(stage['ModoEtapa'])
        # Keep a clearly defined population: urban bus and Metro Valparaiso only.
        if mode not in (3, 4):
            audit['other_transport_stage_rows_excluded'] += 1
            continue
        audit['selected_stages'] += 1
        trip = trip_index.get(key(stage, TRIP_KEY))
        household = household_index.get(key(stage, ('Hogar',)))
        if trip is None or household is None:
            raise ValueError('Unmatched survey key. No silently dropped or cross-matched waits allowed.')
        audit['matched_trip_rows'] += 1
        audit['matched_household_rows'] += 1
        wait = stage.get('TiempoEspera')
        if isinstance(wait, bool) or not isinstance(wait, (float, int)) or not math.isfinite(wait) or not 0 <= wait <= 1440:
            raise ValueError('Missing or invalid reported waiting minutes; source review required.')
        transport = 'Bus' if mode == 3 else 'Train'
        station_code = stage.get('EstacionMetroIni') if mode == 4 else None
        route_code = stage.get('RecorridoBus') if mode == 3 else None
        station = stations.get((integer(station_code),)) if station_code is not None else None
        route = routes.get((integer(route_code),)) if route_code is not None else None
        if station_code is not None and station is None:
            raise ValueError('Unknown station code; source lookup cannot be guessed.')
        if route_code is not None and route is None:
            raise ValueError('Unknown bus route code; source lookup cannot be guessed.')
        audit['missing_station_codes'] += int(mode == 4 and station is None)
        audit['missing_bus_route_codes'] += int(mode == 3 and route is None)
        ids = key(stage, STAGE_KEY)
        result[transport].append({
            'Record ID': 'CL-' + '-'.join(map(str, ids)),
            'Transport Mode': transport,
            'Reported Waiting Time (minutes)': wait,
            'Source Mode': modes[(mode,)]['Modo ext'].strip(),
            'City': 'Greater Valparaiso, Chile',
            'Source Household ID': ids[0], 'Source Person ID': ids[1],
            'Source Trip ID': ids[2], 'Source Stage Number': ids[3],
            'Whole-trip Start Time': clock_text(trip.get('HoraIni')),
            'Whole-trip End Time': clock_text(trip.get('Horafin')),
            'Assigned Survey Day': DAYS.get(household.get('DiaAsig')),
            'Household Date (source Fecha)': str(household.get('Fecha')) if household.get('Fecha') is not None else None,
            'Boarding Station (train only)': station['EstacionMetro'].strip() if station else None,
            'Source Boarding Station Code': station_code,
            'Bus Route': route['RecorridoBus'].strip() if route else None,
            'Source Bus Route Code': route_code,
            'Stage Origin Zone': stage.get('ZonaOrigen'),
            'Stage Destination Zone': stage.get('ZonaDestino'),
            'Source Trip Time Valid Flag': stage.get('ViajeTiempoValido'),
            'Source Laboral Expansion Factor': stage.get('Factor_Laboral'),
            'Source Saturday Expansion Factor': stage.get('Factor_Sabado'),
            'Source Sunday Expansion Factor': stage.get('Factor_Domingo'),
            'Measurement Definition': DEFINITION,
            'Source Reference': SOURCE_URL,
        })
    audit['bus_rows'] = len(result['Bus'])
    audit['train_rows'] = len(result['Train'])
    audit['unique_output_records'] = len({r['Record ID'] for rows in result.values() for r in rows})
    if audit['unique_output_records'] != audit['selected_stages']:
        raise ValueError('Join multiplied or duplicated passenger stages.')
    return result, audit


def collect_linked_waits(args, manifest):
    from access_parser import AccessParser
    import zipfile_deflate64 as zipfile

    cache = Path(args.cache) / 'waiting_time_sources' / 'chile'
    archive = cache / 'EOD_2014_GranValparaiso.zip'
    source = fetch_verified(DOWNLOAD_URL, archive, SOURCE_SHA)
    source.update({'official_landing_page': SOURCE_PAGE, 'public_file': SOURCE_URL,
                   'measurement_definition': DEFINITION})
    with zipfile.ZipFile(archive) as z:
        member = z.getinfo(DATABASE_NAME)
        if member.file_size != 68685824:
            raise ValueError('Unexpected database size in pinned source archive.')
        # Read just the known database; never extract arbitrary archive paths.
        (cache / DATABASE_NAME).write_bytes(z.read(member))
    database = AccessParser(str(cache / DATABASE_NAME))
    tables = {}
    for name, expected in TABLE_COUNTS.items():
        tables[name] = records(database.parse_table(name))
        if len(tables[name]) != expected:
            raise ValueError(f'Incomplete extraction of {name}: expected {expected} rows.')
    merged, audit = merge_survey(tables)
    output = Path(args.out) / 'waiting_time_source_review' / 'chile_linked'
    output.mkdir(parents=True, exist_ok=True)
    notes = [
        'Official SECTRA Greater Valparaiso origin-destination survey; published Access database dated 27 April 2016.',
        DEFINITION,
        'Exact joins: Etapa to Viaje on Hogar + Persona + Viaje; Etapa to Hogar on Hogar. Station and route names come from source lookup tables.',
        'Urban bus (source mode 3) and Metro Valparaiso (mode 4) only; other modes remain excluded. One output row is one reported journey stage, not one unique passenger.',
        'Zero reported waits are preserved. No wait or missing predictor was fabricated or imputed. Original source flags and survey expansion weights are preserved.',
        'Whole-trip departure time is not passenger arrival at a stop. Household Fecha is retained as source metadata, not asserted to be the travel date. Assigned day is retained separately.',
        'Passenger Volume and observed Vehicle Frequency are unavailable. Survey sample counts and expansion factors do not become station-hour counts.',
        'Bus route and zone are not bus stop IDs. Train station names are available. This file cannot be merged with NYC or AC Transit records: different cities, periods and identifiers.',
        'These are genuine reported survey records, not a complete current-schema training dataset. Not registered in the system library and no models trained.',
        'For future statistical analysis, account for survey weights and correlated stages/trips within the same respondent or household; a random row split can leak information.',
    ]
    checks = [
        ['Passenger Volume', 'MISSING', 'No observed station-window passenger count.'],
        ['Vehicle Frequency', 'MISSING', 'No observed station-window serving-vehicle count.'],
        ['Station / Stop', 'TRAIN ONLY', 'Metro boarding lookup available; bus route/zone is not a stop.'],
        ['Time of Day', 'DIFFERENT REFERENCE', 'Whole-trip start available; station-arrival or stage-start time absent.'],
        ['Day of Week', 'ASSIGNED SURVEY DAY', 'Original household DiaAsig retained; no guessed observation timestamp.'],
        ['Month of Year', 'NOT VERIFIED FOR TRIP', 'Household Fecha is retained; travel-date interpretation not assumed.'],
        ['Actual Waiting Time', 'SURVEY REPORTED', DEFINITION],
    ]
    for mode, rows in merged.items():
        name = f'{mode.upper()}_CHILE_REPORTED_WAITS_MERGED'
        write_review(output / (name + '.xlsx'), rows, checks, notes, {**source, 'join_audit': audit})
        with (output / (name + '.csv')).open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    manifest.update({
        'downloaded_sources': [source],
        'warning': 'Real survey waits merged by exact source IDs; current six predictors are incomplete.',
        'results': {**audit, 'output_dir': str(output), 'source_table_rows': TABLE_COUNTS,
                    'within_source_merge_performed': True, 'cross_city_merge_performed': False,
                    'registered_in_system_library': False, 'model_trained': False},
    })
    (output / 'MERGE_AUDIT.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (output / 'READ_FIRST.txt').write_text('\n\n'.join(notes) + '\n\n' + json.dumps(audit, indent=2), encoding='utf-8')
    print(f'Exact survey joins complete: {audit["bus_rows"]} bus stages; {audit["train_rows"]} train stages.')
    print(f'Files: {output}')
    print(manifest['warning'])
