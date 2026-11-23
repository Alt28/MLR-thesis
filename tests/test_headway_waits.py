"""Artificial departure fixtures for the headway-derived wait target; not research data."""
import datetime as dt
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from etl_headway_waits import service_hour_waits, training_sample


def departures(path, minutes, stop="101N", route="1"):
    base = dt.datetime(2025, 3, 4, 12)
    frame = pd.DataFrame({
        "event": "departed", "trip_uid": [f"T{i}" for i in range(len(minutes))],
        "stop_id": stop, "route_id": route,
        "departed_at": [base + dt.timedelta(minutes=m) for m in minutes]})
    db = duckdb.connect()
    db.register("frame", frame)
    db.execute(f"COPY frame TO '{path.as_posix()}' (FORMAT PARQUET)")
    return path


def waits(tmp_path, minutes):
    db = duckdb.connect()
    rows = service_hour_waits(db, [departures(tmp_path / "events.parquet", minutes)])
    return {r[2].hour: r for r in rows}


def test_regular_headway_gives_half_headway(tmp_path):
    # Every 10 minutes from 11:50 to 13:10: a random arrival in 12:00-13:00 waits 5 minutes on average.
    hour = waits(tmp_path, range(-10, 71, 10))[12]
    assert hour[3] == pytest.approx(5.0)
    assert hour[4] == pytest.approx(3600)
    assert hour[5] == pytest.approx(10)
    assert hour[6] == 6


def test_irregular_headway_matches_e_h2_over_2_e_h(tmp_path):
    # Headways of 5 and 15 minutes repeating: E[H^2]/(2E[H]) = (25+225)/(2*20) = 6.25, more than mean/2 = 5.
    minutes = [0]
    while minutes[-1] < 80:
        minutes.append(minutes[-1] + (5 if len(minutes) % 2 else 15))
    hour = waits(tmp_path, minutes)[12]
    assert hour[3] == pytest.approx(6.25)


def test_partial_coverage_is_reported_not_filled(tmp_path):
    # Data starts at 12:30, so the 12:00 hour is only half covered by recorded departures.
    hour = waits(tmp_path, [30, 40, 50, 60, 70])[12]
    assert hour[4] == pytest.approx(1800)


def test_training_sample_is_deterministic_and_bounded():
    rows = [{"Record ID": f"ID{i}", "Observation Hour Local": f"2025-03-0{1 + i % 5}", "Station / Stop": "S"}
            for i in range(50)]
    first, second = training_sample(rows, 10), training_sample(list(reversed(rows)), 10)
    assert len(first) == 10 and first == second
    assert training_sample(rows, 0) == rows
