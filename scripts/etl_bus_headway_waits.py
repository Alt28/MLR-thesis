"""NYC Bus training package: six predictors + observed-headway waiting time (same target as the train package).

SOURCES (TransitLab mirror of public MTA data, CC BY 4.0 / NY open data terms)
 - bus_vehicle_positions: every MTA bus GTFS-realtime position report (archive: about one per 2 minutes),
   with trip_id, route_id and stop_id ("stop the bus is at or heading to").
 - bus_hourly_ridership: MTA estimated boardings per bus route per local hour (fare payments).

BUS PASSAGE TIMES (the bus analogue of the subway "departed" events)
A 2-minute feed often skips stops, so stop_id alone misses about a third of the buses at a stop. Instead,
standard AVL interpolation is used:
 1. Direction of travel at a stop = mean direction of movement of buses heading to that stop.
 2. Stop position = far end (97th percentile along the direction of travel) of the reports heading to it;
    buses keep reporting a stop while dwelling at it. Derived from the 2024 feed itself, so it matches the
    2024 stop IDs (current GTFS differs after the 2025 Queens/Bronx network redesigns).
 3. A trip passes the stop when two consecutive reports straddle it along the direction of travel, within
    60 m laterally and 6 minutes apart; the passage time is linearly interpolated. The last passage per trip
    is kept (departure after dwelling). Only routes that report the stop are considered.
 4. Quality gate: a stop is used only if, in every sampled month, at least 90% of the trips that reported it
    are detected as passing it (recall), and it has service in every month.

TARGET: identical to the train package. For each stop and route, the exact hourly mean of the time to the
next recorded passage of that route (E[H^2] / 2E[H]), averaged over the routes serving the stop. Hours with a
gap over 60 minutes, not fully covered, or with no passage are excluded, never imputed. Random passenger
arrival, no denied boarding; not an individually measured passenger wait.

Passenger Volume = MTA boardings, in that local hour, on the routes serving the stop (route-wide, all stops);
Vehicle Frequency = distinct bus trips passing the stop in that hour.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from collections import Counter
from zoneinfo import ZoneInfo

from collect_real_bus_train_six_predictors_v2 import TRANSIT, download, source_sha256
from etl_system_export import SystemExport, local_hour_status, observation
from etl_headway_waits import MAX_GAP_MIN, service_hour_waits, training_sample, sample_note

PREFIX = "BUS_NYC_HEADWAY_WAITS"
TRAINING_FILE = "BUS_NYC_HEADWAY_WAITS_TRAINING.csv"
PREDICTION_FILE = "NYC_BUS_PREDICTION_TEST_200.csv"
TRAINING_COLUMNS = ["Record ID", "Passenger Volume", "Vehicle Frequency", "Station / Stop",
                    "Time of Day", "Day of Week", "Month of Year", "Actual Waiting Time",
                    "Transport Mode", "Observation Hour Local", "MTA Stop ID", "Routes Averaged"]
LAT0 = 40.7
KX, KY = 111320 * 0.7581, 110540  # metres per degree at 40.7 N (cos 40.7 = 0.7581)
LATERAL_M, MAX_STEP_S, MIN_RECALL = 60, 360, 0.90
WAIT_DEFINITION = (
    "Headway-derived expected stop wait (minutes): exact mean, over the local hour, of time until the next "
    "recorded passage of the passenger's route at the same stop; averaged over routes serving the stop. "
    "Passages interpolated from MTA bus GTFS-realtime positions (TransitLab archive); random passenger "
    "arrival assumed; capacity/denied boarding not represented. Not an individually measured passenger wait.")


def default_bus_days():
    """Three Monday-Sunday weeks in 2024 (bus position archive ends 4 Nov 2024)."""
    anchors = ("2024-03-04", "2024-07-08", "2024-10-07")
    return [dt.date.fromisoformat(a) + dt.timedelta(days=n) for a in anchors for n in range(7)]


def load_positions(db, files):
    db.execute(f"""
      CREATE OR REPLACE TABLE pos AS
      SELECT DISTINCT CAST(vehicle_id AS VARCHAR) || '|' || CAST(trip_id AS VARCHAR) AS trip,
             CAST(route_id AS VARCHAR) route, CAST(stop_id AS VARCHAR) stop, vehicle_ts AS ts,
             (lon + 74.0) * {KX} AS x, (lat - {LAT0}) * {KY} AS y
      FROM read_parquet(?)
      WHERE trip_id IS NOT NULL AND route_id IS NOT NULL AND stop_id IS NOT NULL
        AND lat IS NOT NULL AND lon IS NOT NULL AND vehicle_ts IS NOT NULL AND event <> 'removed'
    """, [[str(f) for f in files]])
    db.execute("""
      CREATE OR REPLACE TABLE seg AS
      SELECT trip, route, stop, ts, x, y,
             lag(ts) OVER w pts, lag(x) OVER w px, lag(y) OVER w py, lag(stop) OVER w pstop
      FROM pos WINDOW w AS (PARTITION BY trip ORDER BY ts)
    """)


def stop_geometry(db):
    """Direction of travel and position of each stop, from the 2024 reports themselves."""
    db.execute("""
      CREATE OR REPLACE TABLE sdir AS
      SELECT pstop AS stop, atan2(avg((x - px) / sqrt((x-px)^2 + (y-py)^2)),
                                  avg((y - py) / sqrt((x-px)^2 + (y-py)^2))) AS th, count(*) n
      FROM seg WHERE pstop IS NOT NULL AND sqrt((x-px)^2 + (y-py)^2) BETWEEN 20 AND 1500
      GROUP BY 1 HAVING count(*) >= 30
    """)
    db.execute("""
      CREATE OR REPLACE TABLE sgeo AS
      WITH c AS (SELECT p.stop, avg(x) cx, avg(y) cy FROM pos p JOIN sdir USING (stop) GROUP BY 1),
      a AS (SELECT p.stop, (p.x - c.cx) * sin(d.th) + (p.y - c.cy) * cos(d.th) AS s,
                   -(p.x - c.cx) * cos(d.th) + (p.y - c.cy) * sin(d.th) AS l, c.cx, c.cy, d.th
            FROM pos p JOIN c USING (stop) JOIN sdir d USING (stop)),
      q AS (SELECT stop, quantile_cont(s, 0.97) s97 FROM a GROUP BY 1)
      SELECT a.stop, any_value(th) th,
             any_value(cx) + any_value(s97) * sin(any_value(th))
               - median(l) FILTER (WHERE s > s97 - 250) * cos(any_value(th)) AS sx,
             any_value(cy) + any_value(s97) * cos(any_value(th))
               + median(l) FILTER (WHERE s > s97 - 250) * sin(any_value(th)) AS sy
      FROM a JOIN q USING (stop) GROUP BY 1
    """)
    db.execute("CREATE OR REPLACE TABLE stop_routes AS SELECT DISTINCT stop, route FROM pos")


def passages(db, candidate_table):
    """Interpolated passage time of every trip past every candidate stop."""
    db.execute(f"""
      CREATE OR REPLACE TABLE passage AS
      WITH j AS (
        SELECT g.stop, s.trip, s.route, s.pts, s.ts,
               (s.px - g.sx) * sin(g.th) + (s.py - g.sy) * cos(g.th) AS s1,
               (s.x - g.sx) * sin(g.th) + (s.y - g.sy) * cos(g.th) AS s2,
               -(s.px - g.sx) * cos(g.th) + (s.py - g.sy) * sin(g.th) AS l1,
               -(s.x - g.sx) * cos(g.th) + (s.y - g.sy) * sin(g.th) AS l2
        FROM seg s
        JOIN stop_routes r ON r.route = s.route
        JOIN {candidate_table} k ON k.stop = r.stop
        JOIN sgeo g ON g.stop = r.stop
        WHERE s.pts IS NOT NULL AND epoch(s.ts) - epoch(s.pts) <= {MAX_STEP_S}
          AND abs(s.x - g.sx) < 1500 AND abs(s.y - g.sy) < 1500)
      SELECT stop, route, trip,
             max(pts + to_microseconds(CAST((epoch(ts) - epoch(pts)) * 1e6 * (-s1) / (s2 - s1) AS BIGINT))) AS passed
      FROM j WHERE s1 <= 0 AND s2 > 0 AND abs(l1 + (l2 - l1) * (-s1) / (s2 - s1)) <= {LATERAL_M}
      GROUP BY 1, 2, 3
    """)


def bus_db(cache):
    """On-disk DuckDB: about 40 million position reports exceed the collector's 1 GB in-memory database."""
    import duckdb
    path = cache / "nyc_bus_waits_work.duckdb"
    path.unlink(missing_ok=True)
    db = duckdb.connect(str(path))
    db.execute("SET memory_limit = '3GB'")
    db.execute("SET threads = 4")
    db.execute(f"SET temp_directory = '{(cache / 'duckdb_tmp').as_posix()}'")
    db.execute("SET preserve_insertion_order = false")
    return db, path


def collect_bus_waits(args, _db, manifest):
    db, work = bus_db(args.cache)
    try:
        _collect(args, db, manifest)
    finally:
        db.close()
        work.unlink(missing_ok=True)


def _collect(args, db, manifest):
    days = sorted({dt.date.fromisoformat(d) for d in args.days} if args.days else set(default_bus_days()))
    files, volume_files = [], []
    for day in sorted({d + dt.timedelta(days=o) for d in days for o in (-1, 0, 1)}):
        url = f"https://data.transitlab.nyc/v1/bus_vehicle_positions/year={day:%Y}/month={day:%m}/{day.isoformat()}.parquet"
        p = download(url, args.cache / f"NYC_bus_positions_{day.isoformat()}.parquet")
        files.append(p)
        manifest["downloaded_sources"].append({"url": url, "file": str(p), "sha256": source_sha256(p)})
    for ym in sorted({d.strftime("%Y-%m") for d in days}):
        y, m = ym.split("-")
        url = f"https://data.transitlab.nyc/v1/bus_hourly_ridership/year={y}/month={m}/{ym}.parquet"
        p = download(url, args.cache / f"NYC_bus_hourly_ridership_{ym}.parquet")
        volume_files.append(p)
        manifest["downloaded_sources"].append({"url": url, "file": str(p), "sha256": source_sha256(p)})
    tz, requested = ZoneInfo("America/New_York"), set(days)

    def local_hour(hour_utc):
        local = hour_utc.replace(tzinfo=dt.timezone.utc).astimezone(tz).replace(tzinfo=None)
        ok = local.date() in requested and local_hour_status(local, "America/New_York") == "unambiguous"
        return local if ok else None

    print("Loading bus positions ...")
    load_positions(db, files)
    stop_geometry(db)
    months = sorted({d.strftime("%Y-%m") for d in days})
    # Candidates: stops reported in every sampled month on most days, in a stable hash order.
    db.execute(f"""
      CREATE OR REPLACE TABLE cand AS
      SELECT stop FROM (
        SELECT stop, count(DISTINCT strftime(ts, '%Y-%m')) n_months, count(DISTINCT trip) n_trips
        FROM pos WHERE stop IN (SELECT stop FROM sgeo) GROUP BY 1)
      WHERE n_months = {len(months)} AND n_trips >= {20 * len(days)}
      ORDER BY md5(stop) LIMIT {args.bus_candidate_stops}
    """)
    print("Interpolating passages for", db.execute("SELECT count(*) FROM cand").fetchone()[0], "candidate stops ...")
    passages(db, "cand")
    # Recall per stop and month: share of trips that reported the stop and were detected passing it.
    recall = db.execute("""
      WITH rep AS (SELECT DISTINCT p.stop, p.trip, strftime(min(p.ts) OVER (PARTITION BY p.stop, p.trip), '%Y-%m') ym
                   FROM pos p JOIN cand USING (stop)),
      hit AS (SELECT rep.stop, rep.ym, avg(CASE WHEN q.trip IS NULL THEN 0 ELSE 1 END) r
              FROM rep LEFT JOIN passage q ON q.stop = rep.stop AND q.trip = rep.trip GROUP BY 1, 2)
      SELECT stop, min(r), count(*) FROM hit GROUP BY 1
    """).fetchall()
    good = sorted((s for s, r, n in recall if n == len(months) and r >= MIN_RECALL),
                  key=lambda s: hashlib.md5(s.encode()).hexdigest())[:args.bus_stops]
    db.execute("CREATE OR REPLACE TABLE keep AS SELECT unnest(?) AS stop", [good])
    print(f"Stops passing the {MIN_RECALL:.0%} recall gate: {sum(r >= MIN_RECALL and n == len(months) for _, r, n in recall)} "
          f"of {len(recall)}; using {len(good)}")
    passage_file = args.cache / "NYC_bus_passages.parquet"
    db.execute(f"""COPY (SELECT 'departed' AS event, trip AS trip_uid, stop AS stop_id, route AS route_id,
                               passed AS departed_at FROM passage WHERE stop IN (SELECT stop FROM keep))
                   TO '{passage_file.as_posix()}' (FORMAT PARQUET)""")

    freq = {}
    for stop, trip, passed in db.execute("SELECT stop, trip, passed FROM passage WHERE stop IN (SELECT stop FROM keep)").fetchall():
        local = local_hour(passed.replace(minute=0, second=0, microsecond=0))
        if local: freq.setdefault((stop, local), set()).add(trip)
    excluded, waits = Counter(), {}
    for stop, route, hour_utc, wait, covered, max_gap, inside in service_hour_waits(db, [passage_file]):
        local = local_hour(hour_utc)
        if local is None: continue
        if inside < 1: excluded["no_passage_in_hour"] += 1; continue
        if covered < 3599.5: excluded["hour_not_fully_covered"] += 1; continue
        if max_gap > MAX_GAP_MIN: excluded[f"headway_over_{MAX_GAP_MIN}_min"] += 1; continue
        waits.setdefault((stop, local), []).append((route, wait))

    ridership = db.execute("""
      SELECT CAST(bus_route AS VARCHAR), CAST(transit_timestamp AS TIMESTAMP), SUM(ridership)
      FROM read_parquet(?) GROUP BY 1, 2""", [[str(p) for p in volume_files]]).fetchall()
    volume = {(r, h): float(v) for r, h, v in ridership if v is not None}
    served = {}
    for stop, route in db.execute("SELECT DISTINCT stop, route FROM passage WHERE stop IN (SELECT stop FROM keep)").fetchall():
        served.setdefault(stop, set()).add(route)

    writer = SystemExport(args.out, PREFIX, "bus", title="NYC Bus + headway waits", target_note=WAIT_DEFINITION)
    rows, missing = [], Counter()
    for key in sorted(freq):
        stop, hour = key
        if key not in waits: missing["no_valid_route_wait"] += 1; continue
        routes = sorted(served[stop])
        if any((r, hour) not in volume for r in routes): missing["route_ridership_missing"] += 1; continue
        services = waits[key]
        wait = round(sum(w for _, w in services) / len(services), 3)
        row = observation("bus", "MTA bus ridership + TransitLab bus positions", f"MTA Bus Stop {stop}",
                          hour, round(sum(volume[(r, hour)] for r in routes), 3), len(freq[key]), {
            "MTA Stop ID": stop, "Routes Averaged": len(services),
            "Routes Serving Stop": " ".join(routes),
            "Route Wait Min (minutes)": round(min(w for _, w in services), 3),
            "Route Wait Max (minutes)": round(max(w for _, w in services), 3),
            "Waiting Time Definition": WAIT_DEFINITION,
            "Passenger Volume Definition": "MTA estimated boardings in this hour on all routes serving the stop (route-wide, every stop of those routes); not stop boardings.",
            "Vehicle Frequency Definition": "Distinct bus trips passing this stop in this hour (interpolated from recorded positions).",
            "Timing Note": "Retrospective hourly values; ridership is published later.",
            "Observation Time Zone": "America/New_York",
            "Source Reference": TRANSIT + "/bus-vehicle-positions/ ; " + TRANSIT + "/bus-hourly-ridership/",
        })
        row["Actual Waiting Time"] = wait
        writer.add(row)
        rows.append(row)

    sample = training_sample(rows, args.train_rows)
    path = args.out / TRAINING_FILE
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=TRAINING_COLUMNS, extrasaction="ignore")
        w.writeheader(); w.writerows(sample)
    # 200 further stop-hours (next smallest hashes, stops seen in training) for Test & Predict, waits blank.
    chosen = {r["Record ID"] for r in sample}
    trained_stops = {r["Station / Stop"] for r in sample}
    rest = sorted((r for r in rows if r["Record ID"] not in chosen and r["Station / Stop"] in trained_stops),
                  key=lambda r: hashlib.sha256(r["Record ID"].encode()).hexdigest())[:200]
    test_cols = TRAINING_COLUMNS[:10]
    for name, blank in [(PREDICTION_FILE, True), (PREDICTION_FILE.replace(".csv", "_answers.csv"), False)]:
        with (args.out / name).open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=test_cols, extrasaction="ignore")
            w.writeheader()
            w.writerows([{**r, "Actual Waiting Time": ""} if blank else r for r in rest])
    values = sorted(r["Actual Waiting Time"] for r in rows)
    manifest["results"] = {
        "mode": "bus-waits", "exported_rows": len(rows), "training_file": TRAINING_FILE,
        "training_file_rows": len(sample), "training_selection": sample_note(args.train_rows),
        "stops_used": len(good), "candidate_stops": len(recall), "recall_gate": MIN_RECALL,
        "stop_recall": {s: round(r, 4) for s, r, n in recall if s in set(good)},
        "waiting_time_definition": WAIT_DEFINITION, "max_headway_minutes": MAX_GAP_MIN,
        "passage_method": {"lateral_tolerance_m": LATERAL_M, "max_report_gap_s": MAX_STEP_S,
                           "stop_position": "97th percentile along direction of travel of reports heading to the stop"},
        "excluded_route_hours": dict(excluded), "excluded_stop_hours": dict(missing),
        "wait_minutes_quantiles": {q: values[int(q * (len(values) - 1))] for q in (0, .05, .25, .5, .75, .95, 1)} if values else {},
        "requested_local_dates": [d.isoformat() for d in days],
        "prediction_test_file": PREDICTION_FILE, "prediction_test_rows": len(rest),
    }
    writer.close(manifest, None, "Six stop-level predictors with a headway-derived waiting-time target (see Waiting Time Definition). "
                                 "Use the separate TRAINING file to train; parts contain every matched row.")
    print(f"Training file: {path} ({len(sample):,} rows); prediction test: {len(rest)} rows")
    if args.library_dir:
        register(args, path, len(sample), len(rest))


def register(args, training, records, test_rows):
    import shutil
    library = args.library_dir
    library.mkdir(parents=True, exist_ok=True)
    shutil.copy2(training, library / training.name)
    shutil.copy2(args.out / PREDICTION_FILE, library / PREDICTION_FILE)
    index = library / "library.json"
    items = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    ids = {"bus_nyc_headway_waits-training", "nyc_bus_prediction_test_200"}
    items = [i for i in items if i["id"] not in ids]
    items[0:0] = [
        {"id": "bus_nyc_headway_waits-training", "title": "NYC Bus - TRAINING (headway waits)", "mode": "Bus",
         "filename": training.name, "records": records, "recordLabel": "observations", "kind": "collected",
         "note": sample_note(args.train_rows) + " " + WAIT_DEFINITION},
        {"id": "nyc_bus_prediction_test_200", "title": f"NYC Bus - PREDICTION TEST ({test_rows} rows, blank waits)",
         "mode": "Bus", "filename": PREDICTION_FILE, "records": test_rows, "recordLabel": "observations",
         "kind": "collected",
         "note": f"{test_rows} NYC bus stop-hours not in the training file, with Actual Waiting Time left blank for "
                 "Test & Predict. The real waits are in NYC_BUS_PREDICTION_TEST_200_answers.csv."},
    ]
    tmp = index.with_suffix(".json.part")
    tmp.write_text(json.dumps(items, indent=2), encoding="utf-8")
    tmp.replace(index)
