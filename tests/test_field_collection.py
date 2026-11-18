"""Artificial fixture entries only; they are not transportation observations."""
from datetime import date, time

import pytest
from openpyxl import load_workbook

from src.data_loader import load_dataset
from src.dataset_units import documented_units
from src.field_collection import build_dataset, create_workbook, write_dataset
from src.research_protocol import source_declarations


def put(ws, rows):
    for r, values in enumerate(rows, start=2):
        for c, value in enumerate(values, start=1):
            ws.cell(r, c, value)


def filled_workbook(path):
    create_workbook(path)
    wb = load_workbook(path)
    put(wb["Stations"], [["S1", "Fixture stop", "Bus", "Fixture route", "Northbound", 12.5, "Fixture map"],
                         ["S2", "Fixture station", "Train", "Fixture line", "Southbound", 16.9, "Fixture map"]])
    put(wb["Counts"], [[sid, date(2026, 12, 1), time((6 * 60 + 15 * k) // 60, (6 * 60 + 15 * k) % 60), 10 + k, 2 + k % 2,
                        "Rain" if k == 4 else "Clear", "Heavy", "obs", ""]
                       for sid in ("S1", "S2") for k in range(9)])  # 06:00 ... 08:00
    put(wb["Passengers"], [["S1", date(2026, 12, 1), time(7, 5, 30), time(7, 17, 0), 1],
                           ["S1", date(2026, 12, 1), time(6, 20, 0), time(6, 30, 0), 0],
                           ["S2", date(2026, 12, 1), time(7, 50, 0), time(7, 40, 0), 0],
                           ["S2", date(2026, 12, 1), "07:59", "08:04:00", None]])
    wb.save(path)
    return path


def test_workbook_build_computes_table_3_1_definitions(tmp_path):
    dataset, exclusions, readiness, _ = build_dataset(filled_workbook(tmp_path / "field.xlsx"))
    assert len(dataset) == 2
    first = dataset.iloc[0]
    # Arrival 07:05:30 sits in the 07:00 block; the window is the four completed blocks 06:00-06:45.
    assert first["Passenger Volume"] == 10 + 11 + 12 + 13
    assert first["Vehicle Frequency"] == 2 + 3 + 2 + 3
    assert first["Weather Condition"] == "Rain" and first["Traffic Condition"] == "Heavy"
    assert first["Actual Waiting Time"] == pytest.approx(11.5)
    assert first["Time of Day"] == "Peak Morning" and first["Route Distance"] == 12.5
    assert first["Full Vehicles Missed"] == 1 and first["Frequency Window Start"].endswith("06:00:00")
    assert dataset.iloc[1]["Actual Waiting Time"] == pytest.approx(5.0)
    reasons = " ".join(exclusions.Reason)
    assert "Fewer than four completed" in reasons and "not after Arrival" in reasons
    assert readiness.set_index("Check").loc["Valid passenger rows", "Status"] == "Collect more"


def test_built_dataset_imports_with_declared_units_and_overwrite_is_refused(tmp_path):
    source = filled_workbook(tmp_path / "field.xlsx")
    output = tmp_path / "recorded.xlsx"
    write_dataset(source, output)
    assert len(load_dataset(output)) == 2
    assert documented_units(output) == {"vehicle_frequency_unit": "vehicles/hour", "route_distance_unit": "km"}
    assert source_declarations(output, {})["workbook_declares_prototype"] is False
    with pytest.raises(FileExistsError):
        create_workbook(source)


def test_invalid_entries_are_reported_with_their_row(tmp_path):
    path = filled_workbook(tmp_path / "field.xlsx")
    wb = load_workbook(path)
    wb["Counts"]["C2"] = time(6, 7)
    wb.save(path)
    with pytest.raises(ValueError, match="Counts row 2: Block Start must be on"):
        build_dataset(path)
