"""NYC Train training package: six predictors + observed-headway waiting time.

TARGET DEFINITION (Actual Waiting Time, minutes)
For every platform-direction stop (GTFS stop_id incl. N/S) and subway route,
the recorded departures (TransitLab stop events, last departure per trip-stop)
define a step function w(t) = next departure after t - t.  The service-hour
waiting time is the exact mean of w(t) over the one-hour window, i.e. the
average wait of a passenger who arrives at a uniformly random instant and
boards the next recorded train of their route.  This is the standard
random-arrival result E[W] = E[H^2] / (2 E[H]) (Osuna & Newell, 1971;
Larson & Odoni, 1981) computed from the actual observed headway sequence,
including headway irregularity, not from scheduled frequency.

The station-complex-hour target is the unweighted mean over the route-
direction services that departed from the complex in that hour.

It is NOT a measured individual passenger wait: it assumes random passenger
arrival, no denied boarding (capacity), and that every passenger boards the
next train of their route.  These assumptions are written into every row.

Exclusions (counted in the manifest, never imputed):
 - service-hours with any covering headway > MAX_GAP_MIN (feed gap / suspension),
 - service-hours without a recorded departure inside the hour,
 - hours not fully covered by recorded departures (start/end of data),
 - ambiguous / nonexistent local DST hours, unmapped stops,
 - complex-hours without a matching MTA ridership value.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from collections import Counter
from zoneinfo import ZoneInfo

from collect_real_bus_train_six_predictors_v2 import (
    NYAPI, TRANSIT, default_train_days, download, load_crosswalk, schema, source_sha256)
from etl_system_export import SystemExport, local_hour_status, observation

MAX_GAP_MIN = 60
PREFIX = "TRAIN_NYC_HEADWAY_WAITS"
TRAINING_FILE = "TRAIN_NYC_HEADWAY_WAITS_TRAINING.csv"
TRAINING_COLUMNS = ["Record ID", "Passenger Volume", "Vehicle Frequency", "Station / Stop",
                    "Time of Day", "Day of Week", "Month of Year", "Actual Waiting Time",
                    "Transport Mode", "Observation Hour Local", "MTA Complex ID",
                    "Services Averaged"]
WAIT_DEFINITION = (
    "Headway-derived expected platform wait (minutes): exact mean, over the local hour, of time until the "
    "next recorded departure of the passenger's route at the same platform direction; averaged over route-"
    "directions serving the complex. Observed departures (TransitLab/MTA GTFS-realtime), random passenger "
    "arrival assumed; capacity/denied boarding not represented. Not an individually measured passenger wait.")


def service_hour_waits(db, stop_files):
    """Exact hourly mean wait per (stop, route, UTC hour) from consecutive observed departures."""
    db.execute('''
      CREATE OR REPLACE TEMP TABLE deps AS
      SELECT CAST(stop_id AS VARCHAR) stop, CAST(route_id AS VARCHAR) route,
             MAX(TRY_CAST(departed_at AS TIMESTAMP)) dep
      FROM read_parquet(?)
      WHERE event='departed' AND trip_uid IS NOT NULL AND stop_id IS NOT NULL
        AND route_id IS NOT NULL AND departed_at IS NOT NULL
      GROUP BY CAST(trip_uid AS VARCHAR), 1, 2
    ''', [[str(x) for x in stop_files]])
    # Interval (prev, dep]: an arrival at t waits dep - t.  Split each interval at UTC hour edges.
    return db.execute(f'''
      WITH iv AS (
        SELECT stop, route, dep, LAG(dep) OVER (PARTITION BY stop, route ORDER BY dep) prev
        FROM deps WHERE dep IS NOT NULL),
      pieces AS (
        SELECT stop, route, dep, prev, h AS hour_utc,
               GREATEST(prev, h) s, LEAST(dep, h + INTERVAL 1 HOUR) e
        FROM iv, LATERAL unnest(generate_series(date_trunc('hour', prev), dep, INTERVAL 1 HOUR)) t(h)
        WHERE prev IS NOT NULL AND dep > prev),
      measured AS (
        SELECT stop, route, hour_utc,
               epoch(dep) - epoch(s) a, epoch(dep) - epoch(e) b, epoch(e) - epoch(s) len,
               epoch(dep) - epoch(prev) gap,
               dep >= hour_utc AND dep < hour_utc + INTERVAL 1 HOUR AS departs_inside
        FROM pieces)
      -- Zero-length pieces (a departure exactly on the hour) count as departures but carry no wait.
      SELECT stop, route, hour_utc,
             SUM((a*a - b*b) / 2) FILTER (WHERE len > 0) / SUM(len) FILTER (WHERE len > 0) / 60.0 AS wait_min,
             SUM(len) FILTER (WHERE len > 0) AS covered_seconds,
             MAX(gap) FILTER (WHERE len > 0) / 60.0 AS max_gap_min,
             COUNT(*) FILTER (WHERE departs_inside) AS departures_in_hour
      FROM measured GROUP BY 1, 2, 3
      HAVING SUM(len) FILTER (WHERE len > 0) > 0
    ''').fetchall()


def collect_train_waits(args, db, manifest):
    days = sorted({dt.date.fromisoformat(d) for d in args.days} if args.days else set(default_train_days()))
    stop_files, volume_files = [], []
    for day in sorted({d + dt.timedelta(days=o) for d in days for o in (-1, 0, 1)}):
        url = f"https://data.transitlab.nyc/v1/subway_stop_events/year={day:%Y}/month={day:%m}/{day.isoformat()}.parquet"
        p = download(url, args.cache / f"NYC_stop_events_{day.isoformat()}.parquet")
        stop_files.append(p)
        manifest["downloaded_sources"].append({"url": url, "file": str(p), "sha256": source_sha256(p)})
    for ym in sorted({d.strftime("%Y-%m") for d in days}):
        y, m = ym.split("-")
        url = f"https://data.transitlab.nyc/v1/subway_hourly_ridership/year={y}/month={m}/{ym}.parquet"
        p = download(url, args.cache / f"NYC_hourly_ridership_{ym}.parquet")
        volume_files.append(p)
        manifest["downloaded_sources"].append({"url": url, "file": str(p), "sha256": source_sha256(p)})
    for p in stop_files:
        missing = {"event", "trip_uid", "stop_id", "route_id", "departed_at"} - set(schema(db, p))
        if missing: raise RuntimeError(f"Stop-event schema mismatch in {p.name}: {sorted(missing)}")
    crosswalk = load_crosswalk(args, manifest)
    tz, requested = ZoneInfo("America/New_York"), set(days)

    def complex_of(stop):
        cid = crosswalk.get(stop)
        if cid is None and stop.endswith(("N", "S")): cid = crosswalk.get(stop[:-1])
        return cid

    def local_hour(hour_utc):
        local = hour_utc.replace(tzinfo=dt.timezone.utc).astimezone(tz).replace(tzinfo=None)
        ok = local.date() in requested and local_hour_status(local, "America/New_York") == "unambiguous"
        return local if ok else None

    # Vehicle Frequency: identical definition to the existing V2 train export.
    trips = db.execute('''
        SELECT CAST(trip_uid AS VARCHAR), CAST(stop_id AS VARCHAR), MAX(TRY_CAST(departed_at AS TIMESTAMP))
        FROM read_parquet(?) WHERE event='departed' AND trip_uid IS NOT NULL AND stop_id IS NOT NULL
          AND departed_at IS NOT NULL GROUP BY 1, 2''', [[str(x) for x in stop_files]]).fetchall()
    freq, unmapped = {}, Counter()
    for trip, stop, dep in trips:
        if dep is None: continue
        cid = complex_of(stop)
        if cid is None: unmapped[stop] += 1; continue
        local = local_hour(dep.replace(minute=0, second=0, microsecond=0))
        if local: freq.setdefault((cid, local), set()).add(trip)
    del trips

    excluded = Counter()
    waits = {}
    for stop, route, hour_utc, wait, covered, max_gap, inside in service_hour_waits(db, stop_files):
        cid = complex_of(stop)
        local = local_hour(hour_utc) if cid else None
        if local is None: continue
        if inside < 1: excluded["no_departure_in_hour"] += 1; continue
        if covered < 3599.5: excluded["hour_not_fully_covered"] += 1; continue
        if max_gap > MAX_GAP_MIN: excluded[f"headway_over_{MAX_GAP_MIN}_min"] += 1; continue
        waits.setdefault((cid, local), []).append((f"{route}@{stop}", wait))

    ridership = db.execute('''
        SELECT CAST(station_complex_id AS VARCHAR), TRY_CAST(transit_timestamp AS TIMESTAMP),
               SUM(TRY_CAST(ridership AS DOUBLE))
        FROM read_parquet(?) WHERE transit_mode='subway' AND station_complex_id IS NOT NULL
          AND TRY_CAST(transit_timestamp AS TIMESTAMP) IS NOT NULL GROUP BY 1, 2''',
        [[str(x) for x in volume_files]]).fetchall()
    volumes = {(c, h): round(v, 3) for c, h, v in ridership if h and h.date() in requested and v is not None and v >= 0}

    writer = SystemExport(args.out, PREFIX, "train", title="NYC Train + headway waits",
                          target_note=WAIT_DEFINITION)
    training_rows, missing = [], Counter()
    for key in sorted(freq):
        cid, hour = key
        if key not in volumes: missing["no_ridership_match"] += 1; continue
        if key not in waits: missing["no_valid_service_wait"] += 1; continue
        services = waits[key]
        wait = round(sum(w for _, w in services) / len(services), 3)
        row = observation("train", "MTA hourly entries + TransitLab departures", f"MTA Subway Complex {cid}",
                          hour, volumes[key], len(freq[key]), {
            "MTA Complex ID": cid, "Services Averaged": len(services),
            "Service Wait Min (minutes)": round(min(w for _, w in services), 3),
            "Service Wait Max (minutes)": round(max(w for _, w in services), 3),
            "Services (route@stop)": " ".join(sorted(s for s, _ in services))[:2000],
            "Waiting Time Definition": WAIT_DEFINITION,
            "Passenger Volume Definition": "MTA estimated paid entries to entire station complex in this hour; not platform queue size.",
            "Vehicle Frequency Definition": "Distinct recorded train trips departing from this complex in this hour (same as V2 export).",
            "Timing Note": "Retrospective hourly values. Ridership is published later; same-hour counts are not available at the start of the hour.",
            "Observation Time Zone": "America/New_York",
            "Source Reference": TRANSIT + "/subway-hourly-ridership/ ; " + TRANSIT + "/subway-stop-events/ ; " + NYAPI,
        })
        row["Actual Waiting Time"] = wait
        writer.add(row)
        training_rows.append(row)

    # Compact single-file training package (fits the 25 MB upload limit).
    sample = training_sample(training_rows, args.train_rows)
    path = args.out / TRAINING_FILE
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=TRAINING_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sample)
    print(f"Training file: {path} ({len(sample):,} rows)")
    values = sorted(r["Actual Waiting Time"] for r in training_rows)
    manifest["results"] = {
        "mode": "train-waits", "exported_rows": len(training_rows), "training_file": TRAINING_FILE,
        "training_file_rows": len(sample), "training_selection": sample_note(args.train_rows),
        "waiting_time_definition": WAIT_DEFINITION, "max_headway_minutes": MAX_GAP_MIN,
        "excluded_service_hours": dict(excluded), "excluded_complex_hours": dict(missing),
        "unmapped_departure_stop_codes": dict(unmapped.most_common(25)),
        "wait_minutes_quantiles": {q: values[int(q * (len(values) - 1))] for q in (0, .05, .25, .5, .75, .95, 1)} if values else {},
        "requested_local_dates": [d.isoformat() for d in days],
    }
    writer.close(manifest, args.library_dir,
                 "Six complex-level predictors with a headway-derived waiting-time target (see Waiting Time Definition). "
                 "Use the separate TRAINING file to train; parts contain every matched row.")
    if args.library_dir:
        register_training(args, path, len(sample))


def training_sample(rows, limit):
    """Deterministic, documented subset: smallest SHA-256 of Record ID. 0 = all rows."""
    if not limit or limit >= len(rows): return rows
    ranked = sorted(rows, key=lambda r: hashlib.sha256(r["Record ID"].encode()).hexdigest())
    return sorted(ranked[:limit], key=lambda r: (r["Observation Hour Local"], r["Station / Stop"]))


def sample_note(limit):
    return "All matched rows." if not limit else (
        f"Up to {limit} rows with the smallest SHA-256 Record ID hashes (reproducible, station-agnostic).")


def register_training(args, path, records):
    import shutil
    library = args.library_dir
    library.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, library / path.name)
    index = library / "library.json"
    items = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    items = [i for i in items if i["id"] != "train_nyc_headway_waits-training"]
    items.insert(0, {"id": "train_nyc_headway_waits-training", "title": "NYC Train - TRAINING (headway waits)",
                     "mode": "Train", "filename": path.name, "records": records, "recordLabel": "observations",
                     "kind": "collected", "note": sample_note(args.train_rows) + " " + WAIT_DEFINITION})
    tmp = index.with_suffix(".json.part")
    tmp.write_text(json.dumps(items, indent=2), encoding="utf-8")
    tmp.replace(index)
