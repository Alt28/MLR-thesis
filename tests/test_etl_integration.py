"""Artificial unit fixtures; never empirical research observations."""
import datetime as dt
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from src.data_loader import inspect_dataset_bytes, load_prediction_dataset_bytes

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from etl_system_export import SystemExport, observation, local_hour_status
import collect_real_bus_train_six_predictors_v2 as collector


def row(number=1, mode="train", frequency=3):
    return observation(mode, "ARTIFICIAL SOFTWARE TEST", "001", dt.datetime(2024, 3, number, 17), 15, frequency,
                       {"Source Reference": "ARTIFICIAL SOFTWARE TEST", "Definition Note": "Not research data."})


def test_csv_parts_keep_every_row_and_xlsx_audit_by_id(tmp_path):
    library = tmp_path / "library"
    writer = SystemExport(tmp_path / "exports", "TEST", "train", max_bytes=1500)
    expected = [row(i) for i in range(1, 10)]
    for item in expected: writer.add(item)
    result = writer.close({"results": {"artificial_fixture": True}}, library)
    assert len(writer.parts) > 1
    seen = []
    for part in writer.parts:
        file = library / part["filename"]
        assert file.stat().st_size <= 1500
        data = load_prediction_dataset_bytes(file.name, file.read_bytes())
        seen.extend(data["Record ID"])
        assert data["Station / Stop"].eq("001").all()
        assert data["Time of Day"].eq("Evening").all()
    assert seen == [r["Record ID"] for r in expected]
    assert result["rows"] == 9
    book = library / "TEST_OVERVIEW.xlsx"
    inspection = inspect_dataset_bytes(book.name, book.read_bytes())
    assert inspection["purpose"] == "prediction"
    assert inspection["missing_predictors"] == {}
    assert inspection["preview"][0]["Definition Note"] == "Not research data."
    assert any("ARTIFICIAL SOFTWARE TEST" in x for x in inspection["source_notes"])


def test_missing_frequency_is_source_review_never_imputed_or_trained(tmp_path, monkeypatch):
    library = tmp_path / "library"
    writer = SystemExport(tmp_path / "exports", "BUS_TEST", "bus")
    writer.add(row(mode="bus", frequency=""))
    writer.close({"results": {}}, library)
    monkeypatch.setenv("MLR_DATASET_LIBRARY_DIR", str(library))
    with TestClient(create_app(tmp_path / "storage")) as client:
        entries = client.get("/api/datasets/library").json()
        assert len(entries) == 2
        for entry in entries:
            response = client.get("/api/datasets/library/" + entry["id"])
            assert response.status_code == 200
            payload = {"file": (entry["filename"], response.content)}
            preview = client.post("/api/datasets/inspect", files=payload).json()
            assert preview["purpose"] == "source_review"
            assert preview["missing_predictors"] == {"Vehicle Frequency": 1}
            assert preview["recorded_waits"] == 0
            assert preview["preview"][0]["Vehicle Frequency"] is None
            assert client.post("/api/experiments", files=payload).status_code == 400
            with pytest.raises(ValueError, match="Vehicle Frequency"):
                load_prediction_dataset_bytes(entry["filename"], response.content)
        assert client.get("/api/experiments").json() == []
        assert client.get("/api/datasets/library/unknown").status_code == 404
    # A manifest cannot expose other local files or escape the library directory.
    (tmp_path / "outside.csv").write_text("private")
    (library / "library.json").write_text(json.dumps([{"id": "escape", "filename": "../outside.csv"}]))
    with TestClient(create_app(tmp_path / "storage2")) as client:
        assert client.get("/api/datasets/library").json() == []
        assert client.get("/api/datasets/library/escape").status_code == 404


def test_dst_ambiguous_hours_not_collapsed_into_one_vehicle_frequency():
    assert local_hour_status(dt.datetime(2025, 11, 2, 1), "America/New_York") == "ambiguous"
    assert local_hour_status(dt.datetime(2025, 3, 9, 2), "America/New_York") == "nonexistent"
    assert local_hour_status(dt.datetime(2025, 3, 9, 3), "America/New_York") == "unambiguous"


def test_bus_real_fields_aggregated_and_door_events_kept_out_of_frequency(tmp_path, monkeypatch):
    duckdb = pytest.importorskip("duckdb")
    db = duckdb.connect()
    fixture = pd.DataFrame({"route_id": ["10 "]*4, "stop_id": ["001"]*4,
                            "event_timestamp": pd.to_datetime(["2024-03-01 07:02", "2024-03-01 07:15", "2024-03-01 07:15", "2024-03-01 07:40"]),
                            "boardings": [2, 3, 4, -1]})
    db.register("fixture", fixture)
    source = tmp_path / "artificial.parquet"
    db.execute("COPY fixture TO ? (FORMAT PARQUET)", [str(source)])
    monkeypatch.setattr(collector, "download", lambda url, path: source)
    args = SimpleNamespace(months=["2024-03"], cache=tmp_path, out=tmp_path / "export", library_dir=None, bus_rows_per_day=64)
    manifest = {"downloaded_sources": []}
    try: collector.demand_and_events_ac(args, db, manifest)
    finally: db.close()
    assert manifest["results"]["raw_rows"] == 4
    assert manifest["results"]["excluded_raw_rows"] == 1
    assert manifest["results"]["exported_rows"] == 1
    file = args.out / "BUS_AC_TRANSIT_SOURCE_REVIEW_OVERVIEW.xlsx"
    preview = inspect_dataset_bytes(file.name, file.read_bytes())
    record = preview["preview"][0]
    assert record["Passenger Volume"] == 9
    assert record["APC Door Events"] == 3
    assert record["Unique APC Event Timestamps"] == 2
    assert record["Vehicle Frequency"] is None
    assert record["Actual Waiting Time"] == ""
    assert record["Source Stop ID"] == "001"
    assert record["Station / Stop"] == "Stop 001 | route 10"
