"""Field-collection workbook: raw on-site tallies and stopwatch times -> model-ready recorded dataset.

Observers record only what they see: 15-minute passenger and vehicle tallies with the weather and traffic at
each block, and the arrival and boarding time of each sampled passenger. Every model column is then computed
here with the operational definitions of Table 3.1, so no value is typed in by hand or estimated.
"""
from datetime import date, datetime, time, timedelta
from pathlib import Path
import math

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from .config import ROW_ID, TARGET
from .data_loader import validate_data

BLOCK_MINUTES = 15
WINDOW_BLOCKS = 4  # four completed 15-minute blocks = the 60-minute window W of Table 3.1
WEATHER = ["Clear", "Cloudy", "Rain", "Heavy Rain"]
TRAFFIC = ["Light", "Moderate", "Heavy"]
MODES = ["Bus", "Train"]
PERIODS = [("Peak Morning", "06:00", "09:00"), ("Mid-Day", "09:00", "16:00"),
           ("Peak Evening", "16:00", "20:00"), ("Night", "20:00", "06:00")]
MIN_ROWS = 400
MIN_PER_CATEGORY = 20
MIN_STATIONS = 4
MAX_ROWS = 3000

STATION_COLUMNS = ["Station ID", "Station Name", "Transport Mode", "Route", "Direction",
                   "Route Distance (km)", "Route Distance Source"]
COUNT_COLUMNS = ["Station ID", "Date", "Block Start", "Passenger Arrivals", "Vehicles Serving",
                 "Weather Condition", "Traffic Condition", "Observer", "Notes"]
PASSENGER_COLUMNS = ["Station ID", "Date", "Arrival Time", "Boarding Time", "Full Vehicles Missed",
                     "Observer", "Notes", "Wait (min) - check only"]

SOURCE_ROWS = [
    ("Traffic Condition", "category", "Observed road congestion at the stop during the arrival's 15-minute block; Light / Moderate / Heavy.",
     "Observer, checked against the Google Maps live traffic layer (green = Light, orange = Moderate, red or dark red = Heavy)."),
    ("Weather Condition", "category", "Observed weather at the stop during the arrival's 15-minute block; Clear / Cloudy / Rain / Heavy Rain.",
     "Observer, checked against PAGASA weather and rainfall advisories (https://www.pagasa.dost.gov.ph/)."),
    ("Passenger Volume", "passengers per 60-minute window",
     "Passengers arriving for the same service, stop, and direction in the four completed 15-minute blocks before the sampled arrival.",
     "Observer tally counter, 15-minute blocks."),
    ("Route Distance", "km", "Total length of the selected service route in the observed direction.",
     "Recorded per station in the Stations sheet with its source (official line or route map, or Google Maps route measurement)."),
    ("Vehicle Frequency", "vehicles/hour",
     "60 × N / W, where N is the number of serving vehicles counted in the four completed 15-minute blocks before the arrival and W = 60 minutes.",
     "Observer tally counter, 15-minute blocks. Observed, not scheduled."),
    ("Time of Day", "category", "Period containing the passenger arrival time, using the fixed boundaries in the Lists sheet.",
     "Derived from Arrival Time."),
    ("Actual Waiting Time", "minutes",
     "Boarding Time minus Arrival Time of the sampled passenger, including waiting caused by full vehicles.",
     "Observer stopwatch / phone clock."),
]

INSTRUCTIONS = [
    "FIELD COLLECTION WORKBOOK - Enhanced MLR train and bus wait-time study",
    "",
    "WHAT TO RECORD (only what you observe; never estimate or copy values from other sources)",
    "1. Stations sheet: one row per stop/station and direction you observe. Fill Route Distance (km) and where the distance came from.",
    "2. Counts sheet (Counter role): every 15 minutes write one row - passengers who arrived for the observed service and direction, "
    "vehicles that stopped and served that direction, and the weather and traffic in that block. Block Start must be :00, :15, :30, or :45.",
    "3. Passengers sheet (Timer role): pick the next passenger who joins the queue, write the time they arrive at the waiting area "
    "and the time they board. If a full vehicle passes them, keep timing and add 1 to Full Vehicles Missed.",
    "",
    "IMPORTANT TIMING RULE",
    "Start counting at least 60 minutes before you start timing passengers. Each passenger needs the four complete 15-minute "
    "count blocks before their arrival block; passengers without them are excluded automatically with a reason.",
    "",
    "TARGETS",
    f"- At least {MIN_ROWS} valid passenger rows in total (about 21 model terms x 10-20 rows per term).",
    f"- At least {MIN_PER_CATEGORY} rows for every weather, traffic, and time-of-day category: include peak and off-peak hours and some rainy days.",
    f"- At least {MIN_STATIONS} stations (6 or more is better), with both Bus and Train, so the grouped split by Station ID works.",
    "- Example pace: one timer records about 6-10 passengers per hour, so 400 rows is roughly 25 hours with two timers.",
    "",
    "ETHICS (Republic Act 10173, Data Privacy Act of 2012)",
    "Record times and counts only. No names, faces, photos, or other personal information. Ask station management or the "
    "operator before observing inside paid areas of train stations.",
    "",
    "AFTER COLLECTION",
    "Run:  .\\.venv\\Scripts\\python.exe scripts\\field_data.py build <this workbook>",
    "It writes data\\recorded_dataset.xlsx (ready to upload) plus a list of excluded rows and a readiness report.",
    "Do not edit the Sources_Methodology unit rows; the system reads the units from them.",
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

    stations = sheet("Stations", STATION_COLUMNS, [12, 28, 14, 22, 18, 18, 50])
    counts = sheet("Counts", COUNT_COLUMNS, [12, 13, 12, 18, 16, 18, 17, 14, 40])
    passengers = sheet("Passengers", PASSENGER_COLUMNS, [12, 13, 13, 14, 19, 14, 40, 20])

    lists = sheet("Lists", ["Weather Condition", "Traffic Condition", "Transport Mode", "",
                            "Time of Day", "Start (HH:MM)", "End (HH:MM)"], [18, 18, 15, 3, 16, 14, 14])
    for i in range(max(len(WEATHER), len(TRAFFIC), len(PERIODS))):
        lists.append([WEATHER[i] if i < len(WEATHER) else None, TRAFFIC[i] if i < len(TRAFFIC) else None,
                      MODES[i] if i < len(MODES) else None, None,
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
    distance = DataValidation(type="decimal", operator="greaterThan", formula1="0", allow_blank=True, showErrorMessage=True)
    stations.add_data_validation(distance)
    distance.add(f"F2:F{last}")
    for ws in (counts, passengers):
        dropdown(ws, "A", f"=Stations!$A$2:$A${last}")
    dropdown(counts, "F", "=Lists!$A$2:$A$5")
    dropdown(counts, "G", "=Lists!$B$2:$B$4")
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
    for row in _rows(wb, "Stations", STATION_COLUMNS, 7):
        sid = "" if _blank(row["Station ID"]) else str(row["Station ID"]).strip()
        try:
            if not sid:
                raise ValueError("Station ID is empty")
            if sid in stations:
                raise ValueError("duplicate Station ID")
            if row["Transport Mode"] not in MODES:
                raise ValueError("Transport Mode must be Bus or Train")
            km = float(row["Route Distance (km)"])
            if not math.isfinite(km) or km <= 0:
                raise ValueError("Route Distance (km) must be a positive number")
            if _blank(row["Route Distance Source"]):
                raise ValueError("Route Distance Source is required")
        except (TypeError, ValueError) as exc:
            problems.append(f"Stations row {row['Excel Row']}: {exc}")
            continue
        stations[sid] = {**row, "Route Distance (km)": km}

    blocks = {}
    for row in _rows(wb, "Counts", COUNT_COLUMNS, 7):
        try:
            sid = str(row["Station ID"]).strip()
            if sid not in stations:
                raise ValueError(f"Station ID '{sid}' is not a valid row in the Stations sheet")
            start = datetime.combine(_date(row["Date"]), _time(row["Block Start"]))
            if start.minute % BLOCK_MINUTES or start.second:
                raise ValueError("Block Start must be on :00, :15, :30, or :45")
            if row["Weather Condition"] not in WEATHER or row["Traffic Condition"] not in TRAFFIC:
                raise ValueError("choose Weather and Traffic from the dropdown lists")
            key = (sid, start)
            if key in blocks:
                raise ValueError("duplicate count block for this station and time")
            blocks[key] = {"passengers": _count(row["Passenger Arrivals"], "Passenger Arrivals"),
                           "vehicles": _count(row["Vehicles Serving"], "Vehicles Serving"),
                           "weather": row["Weather Condition"], "traffic": row["Traffic Condition"]}
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
        elif (sid, current) not in blocks:
            reason = f"No count block at {current:%H:%M} for the weather and traffic at arrival."
        elif any((sid, start) not in blocks for start in window):
            reason = (f"Fewer than four completed 15-minute count blocks before arrival "
                      f"({window[0]:%H:%M}-{current:%H:%M} needed).")
        if reason:
            exclusions.append({"Passengers Excel Row": row["Excel Row"], "Station ID": sid, "Reason": reason})
            continue
        station, now = stations[sid], blocks[(sid, current)]
        vehicles = sum(blocks[(sid, start)]["vehicles"] for start in window)
        records.append({
            "Traffic Condition": now["traffic"], "Weather Condition": now["weather"],
            "Passenger Volume": sum(blocks[(sid, start)]["passengers"] for start in window),
            "Route Distance": station["Route Distance (km)"],
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
                  "Target": "Bus and Train", "Status": "OK" if dataset["Transport Mode"].nunique() == 2 else "Add the missing mode"}]
    for column, categories in (("Weather Condition", WEATHER), ("Traffic Condition", TRAFFIC),
                               ("Time of Day", [p[0] for p in periods])):
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
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        dataset.to_excel(writer, sheet_name="Dataset", index=False)
        pd.DataFrame(methodology).to_excel(writer, sheet_name="Sources_Methodology", index=False, header=False)
        readiness.to_excel(writer, sheet_name="Readiness", index=False)
        exclusions.to_excel(writer, sheet_name="Exclusions", index=False)
    dataset.to_csv(output_path.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    return dataset, exclusions, readiness
