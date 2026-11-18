"""Combine the downloaded MRT-3 reports, preserving CSV values and checking Excel cells."""
from pathlib import Path
import csv
from decimal import Decimal
import hashlib
import json
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET
import posixpath

import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.utils.cell import column_index_from_string, get_column_letter

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
OUT = ROOT / "prepared"
OUT.mkdir(exist_ok=True)
combined = {"hourly": [], "daily": []}
headers = {}
audit = {"checked_source_cells": 0, "excluded_outside_month_rows": {}, "annual_entry_totals": {}}


def read_source_cells(path):
    """Read stored numeric XML directly, avoiding source formatting incompatibilities."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel_attr = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    with ZipFile(path) as archive:
        relationships = {r.attrib["Id"]: r.attrib["Target"] for r in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        sheets = {}
        for sheet in ET.fromstring(archive.read("xl/workbook.xml")).find(ns + "sheets"):
            target = relationships[sheet.attrib[rel_attr]]
            member = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
            cells = {}
            for cell in ET.fromstring(archive.read(member)).iter(ns + "c"):
                value = cell.find(ns + "v")
                cells[cell.attrib["r"]] = (cell.attrib.get("t", "n"), None if value is None else value.text)
            sheets[sheet.attrib["name"]] = cells
        return sheets

for year in [2023, 2024, 2025]:
    workbook = SOURCE / f"Daily Hourly {year}.xlsx"
    sheets = read_source_cells(workbook)
    for kind in ["hourly", "daily"]:
        with (SOURCE / f"csv/mrt3_{kind}_{year}.csv").open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if kind in headers:
                assert headers[kind] == reader.fieldnames
            headers[kind] = reader.fieldnames
        count_columns = [c for c in headers[kind] if c.endswith("_entry") or c.endswith("_exit")]
        for record in rows:
            offset = column_index_from_string(record["source_time_column"])
            for j, column in enumerate(count_columns):
                coordinate = f"{get_column_letter(offset + j + 1)}{record['source_row']}"
                cell_type, original = sheets[record["source_sheet"]].get(coordinate, ("n", None))
                exported = record[column]
                if original is None:
                    assert exported == "", (year, kind, record["source_row"], column)
                else:
                    assert exported != ""
                    assert cell_type == "n", (year, coordinate, cell_type)
                    assert Decimal(original) == Decimal(exported), (
                        year, kind, record["source_row"], column, original, exported)
                audit["checked_source_cells"] += 1
        selected = [r for r in rows if r["date_in_sheet_month"] == "true"]
        expected = (366 if year == 2024 else 365) * (24 if kind == "hourly" else 1)
        assert len(selected) == expected
        keys = [(r["report_date"], r["hour_sequence"]) if kind == "hourly" else r["report_date"] for r in selected]
        assert len(set(keys)) == len(keys)
        audit["excluded_outside_month_rows"][f"{kind}_{year}"] = len(rows) - len(selected)
        combined[kind].extend(selected)
        if kind == "daily":
            audit["annual_entry_totals"][str(year)] = str(sum(Decimal(r["total_entry"]) for r in selected if r["total_entry"]))

assert audit["annual_entry_totals"]["2023"] == "129030158"
assert audit["annual_entry_totals"]["2024"] == "135885336"
audit["official_annual_comparison"] = {
    "url": "https://www.dotrmrt3.gov.ph/news/mrt-3-logs-135-million-riders-in-2024",
    "2023": "Match: 129030158", "2024": "Match: 135885336",
    "scope": "Checks annual totals only; does not independently authenticate every underlying record."
}
for kind, rows in combined.items():
    with (OUT / f"mrt3_{kind}_2023_2025.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers[kind], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

# Compare the separately obtained 2024 report without silently reconciling discrepancies.
old_path = ROOT.parent / "philippine_sources/prepared/mrt3_daily_ridership_jan_apr_2024.csv"
discrepancies = []
checks = 0
if old_path.exists():
    by_date = {r["report_date"]: r for r in combined["daily"]}
    with old_path.open(encoding="utf-8-sig", newline="") as f:
        for old in csv.DictReader(f):
            new = by_date[old["Date"]]
            for old_field, new_field in [("MRT3 System Entries", "total_entry"), ("MRT3 System Exits", "total_exit")]:
                if old[old_field] and new[new_field]:
                    checks += 1
                    if Decimal(old[old_field]) != Decimal(new[new_field]):
                        discrepancies.append({"date": old["Date"], "field": new_field,
                                              "earlier_pdf_value": old[old_field], "downloaded_workbook_value": new[new_field]})
with (OUT / "comparison_with_earlier_2024_report.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["date", "field", "earlier_pdf_value", "downloaded_workbook_value"])
    writer.writeheader()
    writer.writerows(discrepancies)
audit["earlier_2024_report_comparison"] = {"compared_values": checks, "different_values": len(discrepancies), "differences_corrected": False}
audit["output_rows"] = {kind: len(rows) for kind, rows in combined.items()}
audit["in_month_hour_labels_flagged_by_upstream"] = sum(r["hour_label_matches_sequence"] == "false" for r in combined["hourly"])

wb = openpyxl.Workbook()
notes = wb.active
notes.title = "READ ME FIRST"
notes_rows = [
    ["MRT-3 reported ridership, 2023-2025", ""],
    ["Data", "Station entries/exits and system totals; aggregated hourly and daily."],
    ["Source", "https://github.com/ongods/mrt3-ridership-data"],
    ["Provenance", "Publisher states DOTr FOI origin; no request ID or release letter included."],
    ["Verification", f"Checked {audit['checked_source_cells']:,} count cells against the supplied Excel workbooks."],
    ["Independent check", "2023 and 2024 entry totals agree with MRT-3's official January 9, 2025 announcement."],
    ["Hourly rows", len(combined["hourly"])], ["Daily rows", len(combined["daily"])],
    ["Preparation", "Retained only dates belonging to the worksheet month; preserved recorded counts and blanks."],
    ["Clock handling", "Report days run 03:00-02:59. No after-midnight date shift applied; hour-label flags remain."],
    ["Source issues", "Some fractional counts, blank cells, time labels and totals need review. See source/csv quality files."],
    ["Cross-source differences", f"{len(discrepancies)} of {checks} checked daily values differ from the earlier 2024 PDF; kept unchanged and listed separately."],
    ["Waiting-time study", "No measured passenger waiting time and no complete six-predictor observations. Not ready for that model."],
    ["Use", "Reported ridership analysis or a separately agreed demand-forecasting study."],
    ["Precision", "CSV preserves original numeric text; Excel displays numerical cells using ordinary spreadsheet precision."],
]
for row in notes_rows:
    notes.append(row)
notes.column_dimensions["A"].width = 27
notes.column_dimensions["B"].width = 115
notes.freeze_panes = "A2"
for kind, rows in combined.items():
    ws = wb.create_sheet(kind.title())
    ws.append(headers[kind])
    numerical = {c for c in headers[kind] if c.endswith("_entry") or c.endswith("_exit")}
    numerical.update({"source_year", "source_month", "source_row", "hour_sequence"})
    for record in rows:
        values = []
        for key in headers[kind]:
            val = record[key]
            values.append(None if val == "" else float(val) if key in numerical else val)
        ws.append(values)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for column in ws.columns:
        ws.column_dimensions[column[0].column_letter].width = 23
for ws in wb.worksheets:
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
wb.save(OUT / "MRT3_RIDERSHIP_2023_2025.xlsx")
audit["output_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name != "verification.json"}
(OUT / "verification.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
with ZipFile(ROOT / "MRT3_RIDERSHIP_PACKAGE.zip", "w", ZIP_DEFLATED) as archive:
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and p.suffix != ".zip" and "__pycache__" not in p.parts:
            archive.write(p, p.relative_to(ROOT))
print(json.dumps(audit, indent=2))
