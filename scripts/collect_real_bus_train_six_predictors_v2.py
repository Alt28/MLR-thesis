#!/usr/bin/env python3
"""Source-audited ETL with v3 system import exports (updated from user V2).

DATA SOURCES
- Bus: AC Transit automatic passenger counter (APC) parquet, public Hugging Face.
       One record per APC-observed door event; NOT all bus services. Outputs a
       source-review file with vehicle frequency missing and door counts kept
       only as audit metadata. Default bus export is a documented daily subset.
- Bus alternative: SUNT node temporal feature parquet (5-minute vehicle-presence
       counts and ESTIMATED boardings; hourly sum is not guaranteed unique buses).
- Train: TransitLab archived MTA subway stop departure events and MTA hourly
         station-COMPLEX ridership estimates, joined using the official MTA GTFS
         stop -> station complex IDs. De-duplicates by LAST departure per trip-stop,
         per TransitLab's method. Defaults to three Mon-Sun weeks across 3 months.

IMPORTANT: Does NOT contain passenger actual waiting times. The six fields
alone cannot train or evaluate a wait-time MLR model.

Runs on a machine with Python, internet and DuckDB installed.
Run: python -m pip install duckdb openpyxl tzdata
     python collect_real_bus_train_six_predictors_v2.py --mode train
     python collect_real_bus_train_six_predictors_v2.py --mode bus
     python collect_real_bus_train_six_predictors_v2.py --mode sunt
     python collect_real_bus_train_six_predictors_v2.py --mode bus-waits   (NYC bus + headway waits)

No synthetic data or unsupported imputation. Fail with a clear message if the
upstream schema changes. Creates CSV datasets suitable for opening in Excel,
plus bounded CSV parts, overview XLSX with joined audit, and a structured JSON manifest.
Pass --library-dir <system-repo>/data/collected to register the files in Dataset Library.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo
from etl_system_export import SystemExport, observation, local_hour_status

ROOT = pathlib.Path(__file__).resolve().parent
HEADERS = ["Passenger Volume", "Vehicle Frequency", "Station / Stop",
           "Time of Day", "Day of Week", "Month of Year"]
UA = {"User-Agent": "Academic-Transportation-Data-Integration/1.0"}
BUSA = "https://huggingface.co/datasets/somemone/ac-transit-apc"
SUNT = "https://github.com/LabIA-UFBA/SUNT"
TRANSIT = "https://docs.transitlab.nyc/datasets"
NYAPI = "https://data.ny.gov/resource/39hk-dx4f.json"


def download(url: str, path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 1000:
        print(f"Cached: {path}")
        return path
    print(f"Downloading {url}")
    req = urllib.request.Request(url, headers=UA)
    tmp = path.with_suffix(path.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=180) as response, tmp.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        if tmp.stat().st_size < 1000:
            raise RuntimeError(f"Unusually small download ({tmp.stat().st_size} bytes): {url}")
        tmp.replace(path)
    finally:
        if tmp.exists(): tmp.unlink()
    return path


def source_sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: pathlib.Path, header: list[str], rows: list[list]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"Wrote {path.name}: {len(rows):,} rows")


def time_band(hour: int) -> str:
    if 5 <= hour < 10: return "Morning"
    if 10 <= hour < 14: return "Midday"
    if 14 <= hour < 17: return "Afternoon"
    if 17 <= hour < 21: return "Evening"
    return "Night"


def six(passengers, vehicles, stop, hour: dt.datetime):
    return [passengers, vehicles, stop, time_band(hour.hour),
            hour.strftime("%A"), hour.strftime("%B")]


def duck():
    try:
        import duckdb
    except ImportError as e:
        raise SystemExit("Missing DuckDB. Run: python -m pip install duckdb openpyxl tzdata") from e
    db = duckdb.connect(database=":memory:")
    db.execute("SET memory_limit = '1GB'")
    db.execute("SET threads = 2")
    return db


def schema(db, path):
    return [x[0] for x in db.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(path)]).fetchall()]


def demand_and_events_ac(args, db, manifest):
    """Export recorded APC boardings; never promote door events to fleet frequency.

    Default: a documented 64 stop-route-hour groups per date, chosen by stable
    key hash. --bus-rows-per-day 0 streams every group into bounded CSV parts.
    """
    months = args.months or ["2024-03", "2024-07", "2024-11"]
    files = []
    required = {"route_id", "stop_id", "event_timestamp", "boardings"}
    for ym in sorted(set(months)):
        dt.datetime.strptime(ym, "%Y-%m")
        y, m = map(int, ym.split("-"))
        url = f"{BUSA}/resolve/main/year={y}/month={m}/data_0.parquet"
        path = download(url, args.cache / f"AC_Transit_APC_{ym}.parquet")
        missing = required - set(schema(db, path))
        if missing: raise RuntimeError(f"APC source fields missing in {path.name}: {sorted(missing)}")
        files.append(str(path))
        manifest["downloaded_sources"].append({"url": url, "file": str(path), "sha256": source_sha256(path)})
    counts = db.execute("""
      SELECT COUNT(*), COUNT(*) FILTER (WHERE stop_id IS NOT NULL AND TRIM(CAST(stop_id AS VARCHAR))<>''
        AND route_id IS NOT NULL AND TRIM(CAST(route_id AS VARCHAR))<>''
        AND TRY_CAST(event_timestamp AS TIMESTAMP) IS NOT NULL AND TRY_CAST(boardings AS BIGINT)>=0)
      FROM read_parquet(?)
    """, [files]).fetchone()
    db.execute("""
      CREATE TEMP TABLE bus_hourly AS
      SELECT TRIM(CAST(route_id AS VARCHAR)) route, TRIM(CAST(stop_id AS VARCHAR)) stop,
        date_trunc('hour', TRY_CAST(event_timestamp AS TIMESTAMP)) AS observation_hour,
        SUM(TRY_CAST(boardings AS BIGINT)) boardings, COUNT(*) apc_events,
        COUNT(DISTINCT event_timestamp) unique_timestamps
      FROM read_parquet(?)
      WHERE stop_id IS NOT NULL AND TRIM(CAST(stop_id AS VARCHAR))<>''
        AND route_id IS NOT NULL AND TRIM(CAST(route_id AS VARCHAR))<>''
        AND TRY_CAST(event_timestamp AS TIMESTAMP) IS NOT NULL AND TRY_CAST(boardings AS BIGINT)>=0
      GROUP BY 1,2,3
    """, [files])
    available = db.execute('SELECT COUNT(*) FROM bus_hourly').fetchone()[0]
    selection = "All eligible stop-route-hour groups" if args.bus_rows_per_day == 0 else f"Up to {args.bus_rows_per_day} groups per date, ordered by MD5 of stop, trimmed route_id and local hour; descriptive subset, not representative sampling."
    sql = "SELECT * FROM bus_hourly"
    params = []
    if args.bus_rows_per_day:
        sql += " QUALIFY ROW_NUMBER() OVER (PARTITION BY CAST(observation_hour AS DATE) ORDER BY md5(to_json(struct_pack(stop := stop, route := route, obs_hour := observation_hour)))) <= ?"
        params.append(args.bus_rows_per_day)
    sql += ' ORDER BY observation_hour, route, stop'
    cursor = db.execute(sql, params)
    writer = SystemExport(args.out, "BUS_AC_TRANSIT_SOURCE_REVIEW", "bus")
    ambiguous = 0
    try:
        while batch := cursor.fetchmany(4096):
            for route, stop, hour, pax, events, unique in batch:
                status = local_hour_status(hour, "America/Los_Angeles")
                ambiguous += status != 'unambiguous'
                writer.add(observation("bus", "AC Transit APC community archive", f"Stop {stop} | route {route}", hour, int(pax), "", {
                    "Source Stop ID": stop, "Source Route ID": route,
                    "APC Door Events": events, "Unique APC Event Timestamps": unique,
                    "Passenger Volume Definition": "Recorded boardings on APC-equipped buses only, not total stop demand; no capture-rate scaling.",
                    "Vehicle Frequency Definition": "Missing: door events lack vehicle IDs and complete fleet coverage; no verified vehicles/hour.",
                    "Definition Note": selection + " IDs are source route_id, not inferred public route numbers. Whitespace trimmed.",
                    "Timing Note": "Naive source event_timestamp retained; America/Los_Angeles assumed, not independently verified. No prediction-time availability claimed.",
                    "Local Hour Status": status, "Source Reference": BUSA,
                }))
        manifest['results'] = {'mode': 'bus', 'raw_rows': counts[0], 'eligible_raw_rows': counts[1],
          'excluded_raw_rows': counts[0]-counts[1], 'eligible_hourly_groups': available,
          'exported_rows': writer.rows, 'unselected_hourly_groups': available-writer.rows,
          'selection': selection, 'exported_ambiguous_or_nonexistent_hours': ambiguous,
          'vehicle_frequency': 'Unverified; kept blank. APC Door Events is audit metadata only.',
          'waiting_time': 'Not observed; kept blank.',
          'timezone': 'Source naive timestamps; America/Los_Angeles is an unverified assumption.'}
        writer.close(manifest, args.library_dir,
          'Recorded APC subset; Vehicle Frequency and waiting times are missing. Opens for source review; cannot train or predict.')
    finally:
        writer.finish_part()


def sunt_temporal(args, db, manifest):
    """Audited SUNT 5-min rows; never relabel vehicle PRESENCE as hourly vehicle arrivals."""
    dates = args.days or ["2024-03-01","2024-03-02","2024-03-03"]
    files = []
    for date in dates:
        d=dt.date.fromisoformat(date)
        dd=d.strftime("%d-%m-%Y")
        url=f"https://raw.githubusercontent.com/LabIA-UFBA/SUNT/main/data/graph_designer/node_temporal_features_{dd}.parquet"
        p=download(url, args.cache / f"SUNT_temporal_{date}.parquet")
        if p.open("rb").read(4)!=b"PAR1":raise RuntimeError(f"Not a Parquet file: {p}")
        files.append(p)
        manifest["downloaded_sources"].append({"url":url,"file":str(p),"sha256":source_sha256(p)})
    names=schema(db, files[0])
    required={"node","interval","n-boarding","n-vehicles"}
    if required-set(names):raise RuntimeError(f"SUNT temporal schema mismatch: {sorted(required-set(names))}; got {names}")
    result=db.execute('''
       SELECT CAST(node AS VARCHAR) stop,
        date_trunc('hour',TRY_CAST(interval AS TIMESTAMP)) AS "hour",
        SUM(TRY_CAST("n-boarding" AS DOUBLE)) boardings_est,
        SUM(TRY_CAST("n-vehicles" AS DOUBLE)) five_min_vehicle_counts,
        COUNT(DISTINCT TRY_CAST(interval AS TIMESTAMP)) bins
       FROM read_parquet(?)
       WHERE node IS NOT NULL AND interval IS NOT NULL
          AND TRY_CAST("n-boarding" AS DOUBLE)>=0 AND TRY_CAST("n-vehicles" AS DOUBLE)>=0
       GROUP BY 1,2 ORDER BY 2,1
    ''',[[str(x) for x in files]]).fetchall()
    # 5min distinct vehicle per bin may repeat across bins. This is NOT proven to
    # equal distinct vehicle arrivals per hour; do not fill Vehicle Frequency.
    audit=[]; strict=[]
    for stop,hour,pax,veh,bins in result:
        if hour is None:continue
        loc=f"SUNT Stop {stop}"
        strict.append(six(round(pax,3),"",loc,hour))
        audit.append([hour.isoformat(sep=" "),stop,round(pax,3),round(veh,3),bins,
                      "Sum of five-minute vehicle counts; may repeat a vehicle across bins. NOT verified hourly arrivals.", SUNT])
    write_csv(args.out/"BUS_SUNT_INTEGRATED_STRICT_frequency_not_verified.csv",HEADERS,strict)
    write_csv(args.out/"BUS_SUNT_5MIN_VEHICLE_OBSERVATIONS_AUDIT.csv",
              ["Hour", "Stop ID", "Estimated boardings", "Sum five-minute vehicle counts (NOT validated service frequency)",
               "Intervals in hour", "Status", "Source"],audit)
    manifest["results"]={"mode":"sunt","records":len(strict),"assessment":
         "Passenger boardings and 5-minute n-vehicles are jointly integrated in SUNT. Hourly distinct-vehicle frequency NOT VERIFIED; intentionally blank.",
         "source":SUNT,"warning":"SUNT available daily temporal files cover 2024-03-01 through 2024-03-08; Month of Year is constant in this extract."}


def load_crosswalk(args,manifest):
    # Do not rely on station names or assume row index equality.
    url=NYAPI+"?"+urllib.parse.urlencode({"$limit":"5000"})
    p=download(url,args.cache/"mta_stations_crosswalk.json")
    data=json.loads(p.read_text(encoding="utf8"))
    if not isinstance(data,list) or not data:raise RuntimeError("No MTA station crosswalk records")
    print("MTA station crosswalk columns:",sorted(data[0]))
    mapper={}
    conflicts=[]
    for row in data:
        stop=str(row.get("gtfs_stop_id") or "").strip()
        complex_id=row.get("complex_id") or row.get("complex_mrn")
        if not stop or complex_id is None:continue
        complex_id=str(complex_id).strip()
        # MTA directions N/S use base stop ID from the official crosswalk.
        if stop in mapper and mapper[stop]!=complex_id:conflicts.append(stop)
        else:mapper[stop]=complex_id
    if conflicts:raise RuntimeError(f"Conflicting stop→complex mapping: {sorted(set(conflicts))[:12]}")
    if len(mapper)<100:raise RuntimeError(f"Unexpectedly small station mapping: {len(mapper)}. Validate upstream schema.")
    manifest["downloaded_sources"].append({"url":url,"file":str(p),"sha256":source_sha256(p),"mapped_stops":len(mapper)})
    return mapper


def default_train_days():
    """Balanced default: three seven-day weeks in March, July and November 2025."""
    anchors = ("2025-03-03", "2025-07-07", "2025-11-03")
    return [dt.date.fromisoformat(ymd) + dt.timedelta(days=n)
            for ymd in anchors for n in range(7)]


def train_nyc(args, db, manifest):
    days = [dt.date.fromisoformat(d) for d in args.days] if args.days else default_train_days()
    days = sorted(set(days))
    months = sorted({d.strftime("%Y-%m") for d in days})
    stop_files = []
    # Source files are split by UTC day, but the requested sample is in NYC local time.
    # Neighbouring UTC dates are required for midnight edge cases.
    for day in sorted({d + dt.timedelta(days=offset) for d in days for offset in (-1, 0, 1)}):
        y, m = day.strftime("%Y"), day.strftime("%m")
        url = f"https://data.transitlab.nyc/v1/subway_stop_events/year={y}/month={m}/{day.isoformat()}.parquet"
        p = download(url, args.cache / f"NYC_stop_events_{day.isoformat()}.parquet")
        if p.open("rb").read(4) != b"PAR1":
            raise RuntimeError(f"Not a Parquet file: {p}")
        stop_files.append(p)
        manifest["downloaded_sources"].append({"url": url, "file": str(p),
                                                "sha256": source_sha256(p)})
    volume_files = []
    for ym in months:
        year, month = ym.split("-")
        url = f"https://data.transitlab.nyc/v1/subway_hourly_ridership/year={year}/month={month}/{ym}.parquet"
        p = download(url, args.cache / f"NYC_hourly_ridership_{ym}.parquet")
        if p.open("rb").read(4) != b"PAR1":
            raise RuntimeError(f"Not a Parquet file: {p}")
        volume_files.append(p)
        manifest["downloaded_sources"].append({"url": url, "file": str(p),
                                                "sha256": source_sha256(p)})
    stop_names = schema(db, stop_files[0])
    vol_names = schema(db, volume_files[0])
    for name, have, need in [
        ("NYC departure events", stop_names, {"event", "trip_uid", "stop_id", "departed_at"}),
        ("MTA hourly ridership", vol_names, {"transit_timestamp", "station_complex_id", "ridership", "transit_mode"}),
    ]:
        if need - set(have):
            raise RuntimeError(f"{name} missing fields {sorted(need-set(have))}; found {have}")
    for files, needed in [(stop_files, {"event", "trip_uid", "stop_id", "departed_at"}),
                          (volume_files, {"transit_timestamp", "station_complex_id", "ridership", "transit_mode"})]:
        for file in files:
            missing = needed - set(schema(db, file))
            if missing: raise RuntimeError(f"Source schema mismatch in {file.name}: {sorted(missing)}")
    crosswalk = load_crosswalk(args, manifest)
    timezone = ZoneInfo("America/New_York")
    requested_days = set(days)

    # The source documentation says that a trip-stop can have repeated 'departed'
    # rows when a stop disappears and later reappears in the realtime feed.
    # LAST (MAX) departure per trip-stop is the source's recommended observation.
    events = db.execute('''
        SELECT CAST(trip_uid AS VARCHAR) AS trip,
               CAST(stop_id AS VARCHAR) AS stop,
               MAX(TRY_CAST(departed_at AS TIMESTAMP)) AS actual_departure_utc,
               COUNT(*) AS original_departure_rows
        FROM read_parquet(?)
        WHERE event='departed' AND trip_uid IS NOT NULL
          AND stop_id IS NOT NULL AND departed_at IS NOT NULL
        GROUP BY 1, 2
    ''', [[str(x) for x in stop_files]]).fetchall()
    per_complex = defaultdict(set)
    raw_by_complex = Counter()
    deduplicated_stop_events = Counter()
    unmapped = Counter()
    ambiguous_events = 0
    for trip, stop, departure_utc, count in events:
        if departure_utc is None:
            continue
        # Prefer direct official mapping; GTFS departure codes usually add N/S.
        cid = crosswalk.get(stop)
        if cid is None and stop.endswith(("N", "S")):
            cid = crosswalk.get(stop[:-1])
        if cid is None:
            unmapped[stop] += 1
            continue
        local = departure_utc.replace(tzinfo=dt.timezone.utc).astimezone(timezone)
        if local.date() not in requested_days:
            continue
        hour = local.replace(minute=0, second=0, microsecond=0, tzinfo=None)
        if local_hour_status(hour, "America/New_York") != "unambiguous":
            ambiguous_events += 1
            continue
        key = (cid, hour)
        per_complex[key].add(trip)
        raw_by_complex[key] += count
        deduplicated_stop_events[key] += 1

    # MTA transit_timestamp is ALREADY a local NYC hour. Do not convert from UTC.
    ridership = db.execute('''
        SELECT CAST(station_complex_id AS VARCHAR) AS complex_id,
               TRY_CAST(transit_timestamp AS TIMESTAMP) AS local_hour,
               SUM(TRY_CAST(ridership AS DOUBLE)) AS entries
        FROM read_parquet(?)
        WHERE transit_mode='subway' AND station_complex_id IS NOT NULL
          AND TRY_CAST(transit_timestamp AS TIMESTAMP) IS NOT NULL
        GROUP BY 1, 2
    ''', [[str(x) for x in volume_files]]).fetchall()
    volumes = {(cid, hour): round(pax, 3) for cid, hour, pax in ridership
               if hour is not None and hour.date() in requested_days
               and pax is not None and pax >= 0}
    result, audit = [], []
    writer = SystemExport(args.out, "TRAIN_NYC_COMPLEX", "train")
    unmatched_departure_hours = 0
    for (cid, hour), trips in sorted(per_complex.items()):
        passenger = volumes.get((cid, hour))
        if passenger is None:
            unmatched_departure_hours += 1
            continue
        n = len(trips)
        result.append(six(passenger, n, f"MTA Subway Complex {cid}", hour))
        writer.add(observation("train", "MTA hourly entries + TransitLab departures", f"MTA Subway Complex {cid}", hour, passenger, n, {
            "MTA Complex ID": cid,
            "Last Trip Stop Departures": deduplicated_stop_events[(cid, hour)],
            "Original Departure Rows": raw_by_complex[(cid, hour)],
            "Passenger Volume Definition": "MTA estimated paid entries to entire station complex in this hour; not platform queue size.",
            "Vehicle Frequency Definition": "Distinct recorded train trips departing from this complex in this hour; all constituent platforms, not one passenger's service.",
            "Definition Note": "Exact complex and New York local hour join; unmatched hours excluded, missing service never filled with zero. Current crosswalk may differ from historic configuration.",
            "Timing Note": "Retrospective hourly estimates, published later. No availability at the observation-hour start or at passenger arrival is established.",
            "Observation Time Zone": "America/New_York",
            "Source Reference": TRANSIT + "/subway-hourly-ridership/ ; " + TRANSIT + "/subway-stop-events/ ; " + NYAPI,
        }))
        audit.append([len(audit)+2, hour.isoformat(sep=" "), cid, passenger, n,
                      deduplicated_stop_events[(cid, hour)], raw_by_complex[(cid, hour)],
                      "MTA station-complex estimated fare entries; distinct train trips departing from constituent platforms. Not platform-specific.",
                      TRANSIT+"/subway-hourly-ridership/",
                      TRANSIT+"/subway-stop-events/", NYAPI])

    days_count = Counter(hour.strftime("%A") for _, hour in per_complex)
    month_count = Counter(hour.strftime("%B") for _, hour in per_complex)
    audit_days = Counter(row[1][:10] for row in audit)
    output = args.out / "TRAIN_NYC_6_PREDICTORS_COMPLEX_LEVEL_candidate_V2.csv"
    write_csv(output, HEADERS, result)
    write_csv(args.out / "TRAIN_NYC_AUDIT_V2.csv", [
        "Six-column CSV row number", "New York local hour", "MTA complex ID",
        "MTA estimated station-complex entries", "Distinct departed train trips in complex",
        "Last-per-trip-stop events in group", "All original departure rows in group",
        "Definition warning", "Ridership source", "Departure source", "Station crosswalk source"
    ], audit)
    print(f"Train source days requested: {len(days)}; days matched: {len(audit_days)}")
    print("Matched date counts:", dict(sorted(audit_days.items())))
    print("Observed weekday coverage:", dict(days_count))
    if len(set(hour.strftime('%A') for _, hour in per_complex)) < 2:
        print("WARNING: There is no weekday variation in this extract. Use seven days per sampled week.")
    if len(set(hour.strftime('%B') for _, hour in per_complex)) < 2:
        print("WARNING: There is no month variation in this extract. Add dates in other months.")
    if not result:
        print("WARNING: No join matched; inspect station crosswalk and timestamp assumptions.")
    manifest["results"] = {
        "mode": "train", "matched_rows": len(result),
        "requested_local_dates": [d.isoformat() for d in days],
        "matched_local_dates": len(audit_days),
        "matched_date_counts": dict(sorted(audit_days.items())),
        "matched_weekdays": dict(Counter(dt.date.fromisoformat(x).strftime('%A') for x in audit_days)),
        "matched_months": dict(Counter(dt.date.fromisoformat(x).strftime('%B') for x in audit_days)),
        "unmatched_train_complex_hours": unmatched_departure_hours,
        "ambiguous_or_nonexistent_local_hour_events_excluded": ambiguous_events,
        "unmapped_departure_stop_codes": dict(unmapped.most_common(25)),
        "source_event_deduplication": "For each trip_uid and stop_id, kept MAX departed_at per TransitLab source guidance.",
        "assessment": "Complex-level distinct train departures aligned by local New York hour to estimated station-complex fare entries. Not platform-specific.",
        "passenger_volume": "MTA estimated fare entries at station complex, not arriving platform queue",
        "vehicle_frequency": "Distinct recorded train trip IDs at the complex over the local hour",
        "waiting_time": "Not observed; these six features alone cannot fit/validate waiting-time MLR",
    }
    writer.close(manifest, args.library_dir,
      "Six historical complex-level predictors; blank waiting times. Overview is a subset; CSV parts together contain all matched rows. No trained model or accuracy results included.")


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode",choices=["bus","sunt","train","train-waits","bus-waits","bus-arrivals","waiting-sources","linked-waits"],required=True)
    p.add_argument("--days",nargs="+",help="YYYY-MM-DD (sunt/train)")
    p.add_argument("--months",nargs="+",help="YYYY-MM (bus)")
    p.add_argument("--cache",type=pathlib.Path,default=ROOT/"raw_data_downloads")
    p.add_argument("--out",type=pathlib.Path,default=ROOT/"system_imports")
    p.add_argument("--library-dir", type=pathlib.Path, help="System data/collected directory; register import files there")
    p.add_argument("--bus-rows-per-day", type=int, default=64, help="Deterministic bus subset per local date (default 64); 0 exports all groups in CSV parts")
    p.add_argument("--train-rows", type=int, default=10000, help="train-waits/bus-waits: rows in the single TRAINING file (0 = all; default 10000 trains in about 1-2 minutes)")
    p.add_argument("--bus-stops", type=int, default=400, help="bus-waits: stops kept after the recall gate (stable hash order)")
    p.add_argument("--bus-candidate-stops", type=int, default=1000, help="bus-waits: candidate stops checked by the recall gate")
    p.add_argument("--token-file", type=pathlib.Path, help="Local 511 token file for bus-arrivals; never printed")
    p.add_argument("--max-archive-mb", type=int, default=1024, help="Maximum download size per 511 archive")
    args=p.parse_args()
    if args.max_archive_mb < 1: p.error("--max-archive-mb must be positive")
    if args.bus_rows_per_day < 0: p.error("--bus-rows-per-day must be nonnegative")
    args.out.mkdir(parents=True,exist_ok=True)
    manifest={"version":"v3-system-compatible","mode":args.mode,"created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
              "fixed_predictors":HEADERS,"downloaded_sources":[],"results":{},
              "warning":"No actual observed passenger wait-time target in these sources."}
    db = None if args.mode in ("bus-arrivals", "waiting-sources", "linked-waits", "bus-waits") else duck()
    try:
        if args.mode == "bus-waits":
            from etl_bus_headway_waits import collect_bus_waits
            collect_bus_waits(args, db, manifest)
        elif args.mode == "train-waits":
            from etl_headway_waits import collect_train_waits
            collect_train_waits(args, db, manifest)
        elif args.mode == "linked-waits":
            from etl_linked_waits import collect_linked_waits
            collect_linked_waits(args, manifest)
        elif args.mode == "waiting-sources":
            from etl_waiting_sources import collect_waiting_sources
            collect_waiting_sources(args, manifest)
        elif args.mode == "bus-arrivals":
            from etl_511_archive import collect_archives
            collect_archives(args, manifest)
        elif args.mode=="bus":demand_and_events_ac(args,db,manifest)
        elif args.mode=="sunt":sunt_temporal(args,db,manifest)
        else:train_nyc(args,db,manifest)
    finally:
        if db is not None: db.close()
    path=args.out/f"{args.mode.upper()}_SOURCE_MANIFEST_V3.json"
    path.write_text(json.dumps(manifest,indent=2,default=str),encoding="utf8")
    print(f"Source provenance: {path}")
    if args.mode not in ("waiting-sources", "linked-waits", "train-waits", "bus-waits"):
        print("RESEARCH CAUTION: These datasets do not include observed passenger waiting times.")

if __name__=="__main__":
    try: main()
    except (ValueError, RuntimeError) as error:
        raise SystemExit(str(error)) from None
