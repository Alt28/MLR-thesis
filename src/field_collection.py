"""Field-collection workbook: raw on-site tallies and stopwatch times -> model-ready recorded dataset.

Observers record only what they see: 15-minute passenger and vehicle tallies for completed observation windows, and the arrival and boarding time of each sampled passenger. Every model column is then computed
here with the operational definitions of Table 3.1, so no value is typed in by hand or estimated.
"""
from datetime import date, datetime, time, timedelta
from pathlib import Path
import math

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from .config import ROW_ID, TARGET, CATEGORY_VALUES
from .data_loader import validate_data

BLOCK_MINUTES = 15
WINDOW_BLOCKS = 4  # four completed 15-minute blocks = the 60-minute window W of Table 3.1
MODES = ["Bus", "Train"]
# Proposed collection convention, exported in Lists; existing source-specific boundaries must be documented.
PERIODS = [("Morning", "05:00", "10:00"), ("Midday", "10:00", "14:00"),
           ("Afternoon", "14:00", "18:00"), ("Evening", "18:00", "22:00"), ("Night", "22:00", "05:00")]
MIN_ROWS = 400
MIN_PER_CATEGORY = 20
MIN_STATIONS = 4
MAX_ROWS = 3000

STATION_COLUMNS = ["Station ID", "Station Name", "Transport Mode", "Route", "Direction"]
COUNT_COLUMNS = ["Station ID", "Date", "Block Start", "Passenger Arrivals", "Vehicles Serving", "Observer", "Notes"]
PASSENGER_COLUMNS = ["Station ID", "Date", "Arrival Time", "Boarding Time", "Full Vehicles Missed",
                     "Observer", "Notes", "Wait (min) - check only"]

SOURCE_ROWS = [
    ("Passenger Volume", "passengers per 60-minute window", "Recorded arrivals in four completed 15-minute blocks before the sampled arrival.", "Observer tally"),
    ("Vehicle Frequency", "vehicles/hour", "Actual serving vehicles in the same four completed blocks; not scheduled service or available fleet.", "Observer tally"),
    ("Station / Stop", "category", "Identifier of the observed station or stop and direction.", "Stations sheet"),
    ("Time of Day", "category", "Period containing the passenger arrival using documented Lists boundaries.", "Arrival timestamp"),
    ("Day of Week", "category", "Local weekday of the passenger arrival.", "Arrival timestamp"),
    ("Month of Year", "category", "Local calendar month of the passenger arrival.", "Arrival timestamp"),
    ("Actual Waiting Time", "minutes", "Recorded boarding timestamp minus passenger arrival timestamp.", "Observer stopwatch / clock"),
]
INSTRUCTIONS = [
    "FIELD COLLECTION WORKBOOK - six-predictor Bus or Train waiting-time study",
    "Use a separate workbook and model for Bus and Train. Never estimate waiting times from vehicle frequency.",
    "Stations: record a stop/station identifier, mode, route, and direction.",
    "Counts: record passenger arrivals and actual serving vehicles in complete 15-minute blocks.",
    "Passengers: record arrival and boarding timestamps for each sampled passenger; keep timing if full vehicles pass.",
    "Start counts at least 60 minutes before timing passengers. Only the four completed blocks before arrival are used.",
    "Review and document the Time of Day boundaries in Lists before collecting data. They are not severity thresholds.",
    "Record counts and timestamps only. No passenger names or other identifying details are needed.",
    "Calendar and station categories are not ordered severity levels. Classification mappings need documented approval.",
    "After collection run scripts/field_data.py build with this workbook. No source records are invented.",
]


def create_workbook(path, overwrite=False):
    """Write an empty collection workbook with dropdowns, formats, and the methodology sheet."""
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; it may contain collected data. Use a new file name.")
    wb = Workbook()
    header_font, header_fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F4E78")

    def sheet(title, columns, widths):
        ws = wb.create_sheet(title)
        ws.append(columns)
        for cell, width in zip(ws[1], widths):
            cell.font, cell.fill = header_font, header_fill
            cell.alignment = Alignment(wrap_text=True, vertical="center")
            ws.column_dimensions[cell.column_letter].width = width
        ws.freeze_panes = "A2"
        return ws

    instructions = wb.active
    instructions.title = "Instructions"
    instructions.column_dimensions["A"].width = 140
    for line in INSTRUCTIONS:
        instructions.append([line])
    instructions["A1"].font = Font(bold=True, size=14)
    for row in instructions.iter_rows():
        row[0].alignment = Alignment(wrap_text=True)
        first = str(row[0].value or "").split(" ")[0]
        if len(first) >= 5 and first.isupper():
            row[0].font = Font(bold=True)

    stations = sheet("Stations", STATION_COLUMNS, [12, 28, 14, 22, 18])
    counts = sheet("Counts", COUNT_COLUMNS, [12, 13, 12, 18, 16, 14, 40])
    passengers = sheet("Passengers", PASSENGER_COLUMNS, [12, 13, 13, 14, 19, 14, 40, 20])

    lists = sheet("Lists", ["Day of Week", "Month of Year", "Transport Mode", "",
                            "Time of Day", "Start (HH:MM)", "End (HH:MM)"], [18, 18, 15, 3, 16, 14, 14])
    days, months = CATEGORY_VALUES["Day of Week"], CATEGORY_VALUES["Month of Year"]
    for i in range(12):
        lists.append([days[i] if i < 7 else None, months[i], MODES[i] if i < 2 else None, None,
                      *(PERIODS[i] if i < len(PERIODS) else (None, None, None))])

    methodology = sheet("Sources_Methodology", ["Variable", "Unit", "Definition", "Source"], [22, 30, 80, 80])
    for row in SOURCE_ROWS:
        methodology.append(list(row))
    methodology.append([])
    methodology.append(["Data source", "", "Field observation by the researchers.",
                        "Write the stations, dates, and observers here before submitting."])
    for row in methodology.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    last = MAX_ROWS + 1

    def dropdown(ws, column, source):
        rule = DataValidation(type="list", formula1=source, allow_blank=True, showErrorMessage=True)
        ws.add_data_validation(rule)
        rule.add(f"{column}2:{column}{last}")

    def whole_number(ws, column):
        rule = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0", allow_blank=True, showErrorMessage=True)
        ws.add_data_validation(rule)
        rule.add(f"{column}2:{column}{last}")

    dropdown(stations, "C", "=Lists!$C$2:$C$3")
    for ws in (counts, passengers):
        dropdown(ws, "A", f"=Stations!$A$2:$A${last}")
    for column in ("D", "E"):
        whole_number(counts, column)
    whole_number(passengers, "E")
    for r in range(2, last + 1):
        counts[f"B{r}"].number_format = passengers[f"B{r}"].number_format = "yyyy-mm-dd"
        counts[f"C{r}"].number_format = "hh:mm"
        passengers[f"C{r}"].number_format = passengers[f"D{r}"].number_format = "hh:mm:ss"
        passengers[f"H{r}"] = f'=IF(AND(C{r}<>"",D{r}<>""),ROUND((D{r}-C{r})*1440,2),"")'
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def _blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _rows(wb, name, columns, inputs):
    ws = wb[name]
    header = [str(c.value).strip() if c.value is not None else "" for c in ws[1]][:len(columns)]
    if header != columns:
        raise ValueError(f"{name} sheet columns were changed; expected {columns}.")
    out = []
    for number, values in enumerate(ws.iter_rows(min_row=2, max_col=len(columns), values_only=True), start=2):
        if all(_blank(values[i]) for i in range(inputs)):
            continue
        out.append({"Excel Row": number, **dict(zip(columns, values))})
    return out


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value.strip()[:10])
    raise ValueError("date must be an Excel date or YYYY-MM-DD")


def _time(value):
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, (int, float)) and 0 <= value < 1:
        seconds = round(value * 86400)
        return time(seconds // 3600, seconds % 3600 // 60, seconds % 60)
    if isinstance(value, str):
        for pattern in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value.strip(), pattern).time()
            except ValueError:
                pass
    raise ValueError("time must be an Excel time or HH:MM[:SS]")


def _count(value, name):
    number = float(value)
    if not math.isfinite(number) or number < 0 or not number.is_integer():
        raise ValueError(f"{name} must be a whole number of 0 or more")
    return int(number)


def _in_period(minute, start, end):
    return start <= minute < end if start < end else (minute >= start or minute < end)


def _periods(wb):
    periods = []
    for row in wb["Lists"].iter_rows(min_row=2, min_col=5, max_col=7, values_only=True):
        if _blank(row[0]):
            continue
        start, end = _time(row[1]), _time(row[2])
        periods.append((str(row[0]).strip(), start.hour * 60 + start.minute, end.hour * 60 + end.minute))
    if not periods:
        raise ValueError("Lists sheet has no Time of Day periods.")
    if any(sum(_in_period(m, s, e) for _, s, e in periods) != 1 for m in range(1440)):
        raise ValueError("Time of Day periods in the Lists sheet must cover every minute of the day exactly once.")
    return periods


def _period(periods, moment):
    minute = moment.hour * 60 + moment.minute
    return next(name for name, s, e in periods if _in_period(minute, s, e))


def build_dataset(workbook_path):
    """Return (dataset, exclusions, readiness, methodology) computed from a filled collection workbook."""
    wb = load_workbook(workbook_path)
    periods = _periods(wb)
    problems, exclusions = [], []

    stations = {}
    for row in _rows(wb, "Stations", STATION_COLUMNS, 5):
        sid = "" if _blank(row["Station ID"]) else str(row["Station ID"]).strip()
        try:
            if not sid:
                raise ValueError("Station ID is empty")
            if sid in stations:
                raise ValueError("duplicate Station ID")
            if row["Transport Mode"] not in MODES:
                raise ValueError("Transport Mode must be Bus or Train")
        except (TypeError, ValueError) as exc:
            problems.append(f"Stations row {row['Excel Row']}: {exc}")
            continue
        stations[sid] = row

    blocks = {}
    for row in _rows(wb, "Counts", COUNT_COLUMNS, 7):
        try:
            sid = str(row["Station ID"]).strip()
            if sid not in stations:
                raise ValueError(f"Station ID '{sid}' is not a valid row in the Stations sheet")
            start = datetime.combine(_date(row["Date"]), _time(row["Block Start"]))
            if start.minute % BLOCK_MINUTES or start.second:
                raise ValueError("Block Start must be on :00, :15, :30, or :45")
            key = (sid, start)
            if key in blocks:
                raise ValueError("duplicate count block for this station and time")
            blocks[key] = {"passengers": _count(row["Passenger Arrivals"], "Passenger Arrivals"),
                           "vehicles": _count(row["Vehicles Serving"], "Vehicles Serving")}
        except (TypeError, ValueError) as exc:
            problems.append(f"Counts row {row['Excel Row']}: {exc}")

    records = []
    for row in _rows(wb, "Passengers", PASSENGER_COLUMNS, 7):
        try:
            sid = str(row["Station ID"]).strip()
            if sid not in stations:
                raise ValueError(f"Station ID '{sid}' is not a valid row in the Stations sheet")
            day = _date(row["Date"])
            arrival = datetime.combine(day, _time(row["Arrival Time"]))
            boarding = datetime.combine(day, _time(row["Boarding Time"]))
            missed = 0 if _blank(row["Full Vehicles Missed"]) else _count(row["Full Vehicles Missed"], "Full Vehicles Missed")
        except (TypeError, ValueError) as exc:
            problems.append(f"Passengers row {row['Excel Row']}: {exc}")
            continue
        current = arrival.replace(minute=arrival.minute - arrival.minute % BLOCK_MINUTES, second=0, microsecond=0)
        window = [current - timedelta(minutes=BLOCK_MINUTES * k) for k in range(WINDOW_BLOCKS, 0, -1)]
        reason = None
        if boarding <= arrival:
            reason = "Boarding Time is not after Arrival Time (check the times; midnight crossings are not supported)."
        elif any((sid, start) not in blocks for start in window):
            reason = (f"Fewer than four completed 15-minute count blocks before arrival "
                      f"({window[0]:%H:%M}-{current:%H:%M} needed).")
        if reason:
            exclusions.append({"Passengers Excel Row": row["Excel Row"], "Station ID": sid, "Reason": reason})
            continue
        station = stations[sid]
        vehicles = sum(blocks[(sid, start)]["vehicles"] for start in window)
        records.append({
            "Station / Stop": sid, "Day of Week": CATEGORY_VALUES["Day of Week"][arrival.weekday()],
            "Month of Year": CATEGORY_VALUES["Month of Year"][arrival.month - 1],
            "Passenger Volume": sum(blocks[(sid, start)]["passengers"] for start in window),
            "Vehicle Frequency": 60.0 * vehicles / (BLOCK_MINUTES * WINDOW_BLOCKS),
            "Time of Day": _period(periods, arrival),
            TARGET: round((boarding - arrival).total_seconds() / 60, 2),
            "Transport Mode": station["Transport Mode"], "Station ID": sid, "Station Name": station["Station Name"],
            "Route": station["Route"], "Direction": station["Direction"],
            "Passenger Arrival Timestamp": arrival.isoformat(sep=" "), "Boarding Timestamp": boarding.isoformat(sep=" "),
            "Frequency Window Start": window[0].isoformat(sep=" "), "Frequency Window End": current.isoformat(sep=" "),
            "Serving Vehicle Count": vehicles, "Frequency Basis": "observed",
            "Full Vehicles Missed": missed, "Source Workbook Row": row["Excel Row"],
        })
    if problems:
        raise ValueError("Fix these entries in the workbook, then build again:\n- " + "\n- ".join(problems[:50]))
    if not records:
        raise ValueError("No passenger row could be built. Check the Passengers sheet and the 60-minute counting rule.")
    dataset = pd.DataFrame(records)
    dataset.insert(0, ROW_ID, [f"F{i:06d}" for i in range(1, len(dataset) + 1)])
    validate_data(dataset)

    readiness = [{"Check": "Valid passenger rows", "Value": len(dataset), "Target": f">= {MIN_ROWS}",
                  "Status": "OK" if len(dataset) >= MIN_ROWS else "Collect more"},
                 {"Check": "Excluded passenger rows", "Value": len(exclusions), "Target": "as few as possible",
                  "Status": "See Exclusions sheet" if exclusions else "OK"},
                 {"Check": "Stations", "Value": dataset["Station ID"].nunique(), "Target": f">= {MIN_STATIONS}",
                  "Status": "OK" if dataset["Station ID"].nunique() >= MIN_STATIONS else "Add stations"},
                 {"Check": "Transport modes", "Value": ", ".join(sorted(dataset["Transport Mode"].unique())),
                  "Target": "One mode per file", "Status": "OK" if dataset["Transport Mode"].nunique() == 1 else "Separate Bus and Train"}]
    for column, categories in CATEGORY_VALUES.items():
        counts = dataset[column].value_counts()
        for category in categories:
            n = int(counts.get(category, 0))
            readiness.append({"Check": f"{column}: {category}", "Value": n, "Target": f">= {MIN_PER_CATEGORY}",
                              "Status": "OK" if n >= MIN_PER_CATEGORY else "Collect more"})
    methodology = [list(r) for r in wb["Sources_Methodology"].iter_rows(values_only=True)]
    return dataset, pd.DataFrame(exclusions, columns=["Passengers Excel Row", "Station ID", "Reason"]), pd.DataFrame(readiness), methodology


def write_dataset(workbook_path, output_path):
    """Build and save the upload-ready workbook (first sheet = dataset) and a CSV copy."""
    dataset, exclusions, readiness, methodology = build_dataset(workbook_path)
    if dataset["Transport Mode"].nunique() != 1:
        raise ValueError("Use a separate field workbook for Bus and Train; model inputs must contain one transport mode.")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        dataset.to_excel(writer, sheet_name="Dataset", index=False)
        pd.DataFrame(methodology).to_excel(writer, sheet_name="Sources_Methodology", index=False, header=False)
        readiness.to_excel(writer, sheet_name="Readiness", index=False)
        exclusions.to_excel(writer, sheet_name="Exclusions", index=False)
    dataset.to_csv(output_path.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    return dataset, exclusions, readiness
