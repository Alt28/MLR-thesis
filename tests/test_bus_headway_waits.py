"""Artificial bus position fixtures for the interpolated stop-passage method; not research data."""
import datetime as dt
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from etl_bus_headway_waits import KX, KY, LAT0, load_positions, passages, stop_geometry

SPEED = 5.0          # metres per second, northbound
REPORT_EVERY = 120   # seconds, like the 2017-2024 archive
STOPS = {"S1": 500, "S2": 1000, "S3": 1500, "S4": 2000}  # stop positions along y (metres)


def positions(tmp_path, trips=60, seed=3):
    """Buses report every 2 minutes with the stop they are heading to; 600 m between reports skips stops."""
    rng = np.random.default_rng(seed)
    base = dt.datetime(2024, 3, 5, 12)
    rows, truth = [], {}
    for k in range(trips):
        start = base + dt.timedelta(minutes=6 * k)
        phase = rng.uniform(0, REPORT_EVERY)  # first report somewhere along the route
        truth[f"V{k}|T{k}"] = start + dt.timedelta(seconds=STOPS["S2"] / SPEED)
        t = phase
        while t * SPEED <= 2400:
            y = t * SPEED
            heading = next((s for s, ys in STOPS.items() if y < ys), None)
            if heading:
                rows.append({"vehicle_id": f"V{k}", "trip_id": f"T{k}", "route_id": "R1", "stop_id": heading,
                             "event": "changed", "vehicle_ts": start + dt.timedelta(seconds=t),
                             "lat": LAT0 + y / KY, "lon": -74.0 + rng.normal(0, 3) / KX})
            t += REPORT_EVERY
    frame = pd.DataFrame(rows)
    path = tmp_path / "positions.parquet"
    db = duckdb.connect()
    db.register("frame", frame)
    db.execute(f"COPY frame TO '{path.as_posix()}' (FORMAT PARQUET)")
    return path, truth, frame


def test_passages_are_interpolated_and_include_trips_that_skipped_the_stop(tmp_path):
    path, truth, frame = positions(tmp_path)
    db = duckdb.connect()
    load_positions(db, [path])
    stop_geometry(db)
    db.execute("CREATE TABLE cand AS SELECT 'S2' AS stop")
    passages(db, "cand")
    found = dict(db.execute("SELECT trip, passed FROM passage WHERE stop = 'S2'").fetchall())
    reported = set((frame[frame.stop_id == "S2"].vehicle_id + "|" + frame[frame.stop_id == "S2"].trip_id))
    # 600 m between reports and 500 m between stops: some trips never report S2, yet every trip passes it.
    assert len(reported) < len(truth)
    assert set(found) == set(truth)
    errors = [abs((found[t] - truth[t]).total_seconds()) for t in truth]
    # The stop position is estimated from the reports themselves, so allow a few seconds of bias.
    assert max(errors) < 15


def test_opposite_direction_buses_do_not_count(tmp_path):
    path, truth, frame = positions(tmp_path, trips=40)
    south = frame.copy()
    south["trip_id"] = south.trip_id + "S"
    south["lat"] = 2 * LAT0 + 2400 / KY - south.lat   # same street, travelling south
    south["stop_id"] = "N" + south.stop_id            # the other side of the street has its own stop IDs
    both = tmp_path / "both.parquet"
    db = duckdb.connect()
    db.register("frame", pd.concat([frame, south]))
    db.execute(f"COPY frame TO '{both.as_posix()}' (FORMAT PARQUET)")
    load_positions(db, [both])
    stop_geometry(db)
    db.execute("CREATE TABLE cand AS SELECT 'S2' AS stop")
    passages(db, "cand")
    trips = {t for (t,) in db.execute("SELECT trip FROM passage WHERE stop = 'S2'").fetchall()}
    assert trips == set(truth)
