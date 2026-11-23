"""Traceable, bounded-size system exports. No target or frequency imputation.

Used by collect_real_bus_train_six_predictors_v2.py. Only the overview workbook
is sampled (smallest deterministic ID hashes per date); all rows passed to the
writer remain in CSV parts. Bus sampling happens explicitly in the collector.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import heapq
from functools import lru_cache
import io
import json
import pathlib
import shutil
from zoneinfo import ZoneInfo

PREDICTORS = ["Passenger Volume", "Vehicle Frequency", "Station / Stop",
              "Time of Day", "Day of Week", "Month of Year"]
BASE = ["Record ID", *PREDICTORS, "Actual Waiting Time", "Transport Mode"]
TIME_BANDS = "Local observation hour: Morning 05-09; Midday 10-13; Afternoon 14-16; Evening 17-20; Night 21-04 (ETL v2 convention)."


def time_band(hour):
    if 5 <= hour < 10: return "Morning"
    if 10 <= hour < 14: return "Midday"
    if 14 <= hour < 17: return "Afternoon"
    if 17 <= hour < 21: return "Evening"
    return "Night"


@lru_cache(maxsize=10000)
def local_hour_status(hour, zone):
    """Never collapse a repeated DST hour or manufacture a nonexistent hour."""
    tz = ZoneInfo(zone)
    offsets = set()
    for fold in (0, 1):
        aware = hour.replace(tzinfo=tz, fold=fold)
        back = aware.astimezone(dt.timezone.utc).astimezone(tz).replace(tzinfo=None)
        if back == hour: offsets.add(aware.utcoffset())
    return "nonexistent" if not offsets else "ambiguous" if len(offsets) > 1 else "unambiguous"


def observation(mode, source, station, hour, passengers, frequency, audit):
    identity = json.dumps([source, station, hour.isoformat()], ensure_ascii=False)
    record_id = mode.upper() + "-" + hashlib.sha256(identity.encode()).hexdigest()[:24]
    return {"Record ID": record_id, "Passenger Volume": passengers, "Vehicle Frequency": frequency,
            "Station / Stop": station, "Time of Day": time_band(hour.hour),
            "Day of Week": hour.strftime("%A"), "Month of Year": hour.strftime("%B"),
            "Actual Waiting Time": "", "Transport Mode": mode.title(),
            "Source Dataset": source, "Observation Hour Local": hour.isoformat(sep=" "),
            "Observation Window End Local": (hour + dt.timedelta(hours=1)).isoformat(sep=" "),
            "Time Band Definition": TIME_BANDS, **audit}


def sha256(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()


class SystemExport:
    def __init__(self, output, prefix, mode, overview_per_day=64, max_bytes=20 * 1024 * 1024,
                 title=None, target_note=None):
        self.title = title or ("NYC Train" if mode == "train" else "AC Transit Bus")
        self.target_note = target_note
        self.output = pathlib.Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.prefix, self.mode = prefix, mode
        self.overview_per_day, self.max_bytes = overview_per_day, max_bytes
        self.fields = None
        self.file = None
        self.parts = []
        self.samples = {}
        self.rows = 0
        self.day_counts = {}
        self._buffer = io.StringIO(newline="")
        self._writer = csv.writer(self._buffer)

    def encoded_row(self, values):
        self._buffer.seek(0); self._buffer.truncate()
        self._writer.writerow(values)
        return self._buffer.getvalue().encode("utf-8")

    def finish_part(self):
        if self.file:
            self.file.close()
            self.pending.replace(self.path)
            self.parts[-1]["bytes"] = self.path.stat().st_size
            self.parts[-1]["sha256"] = sha256(self.path)
            self.file = None

    def add(self, row):
        if self.fields is None: self.fields = list(row)
        if list(row) != self.fields: raise ValueError("Inconsistent export audit columns.")
        values = self.encoded_row([row[c] for c in self.fields])
        header = self.encoded_row(self.fields)
        if len(values) + len(header) + 3 > self.max_bytes:
            raise ValueError("A source row exceeds the CSV part size limit.")
        if self.file is None or self.file.tell() + len(values) > self.max_bytes:
            self.finish_part()
            name = f"{self.prefix}_part_{len(self.parts)+1:03d}.csv"
            self.path = self.output / name
            self.pending = self.output / (name + ".part")
            self.file = self.pending.open("wb")
            self.file.write(b"\xef\xbb\xbf" + header)
            self.parts.append({"filename": name, "records": 0})
        self.file.write(values)
        self.parts[-1]["records"] += 1
        self.rows += 1
        day = row["Observation Hour Local"][:10]
        self.day_counts[day] = self.day_counts.get(day, 0) + 1
        heap = self.samples.setdefault(day, [])
        score = int(hashlib.sha256(row["Record ID"].encode()).hexdigest(), 16)
        entry = (-score, row["Record ID"], row)
        if len(heap) < self.overview_per_day: heapq.heappush(heap, entry)
        elif score < -heap[0][0]: heapq.heapreplace(heap, entry)

    def close(self, manifest, library=None, note=""):
        self.finish_part()
        if not self.rows: raise ValueError("No source records matched; no import package was registered.")
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        rows = sorted((entry[2] for heap in self.samples.values() for entry in heap),
                      key=lambda row: (row["Observation Hour Local"], row["Station / Stop"]))
        book = Workbook()
        sheet = book.active; sheet.title = "Dataset"
        audit = book.create_sheet("Source_Audit")
        audit_fields = ["Record ID", *(c for c in self.fields if c not in BASE)]
        sheet.append(BASE); audit.append(audit_fields)
        for row in rows:
            sheet.append([row[c] for c in BASE]); audit.append([row[c] for c in audit_fields])
        sources = book.create_sheet("Sources_Methodology")
        sources.append(["Variable", "Unit", "Definition", "Source"])
        sample = rows[0]
        for col, unit, key in [("Passenger Volume", "passengers/hour", "Passenger Volume Definition"),
                                ("Vehicle Frequency", "vehicles/hour", "Vehicle Frequency Definition")]:
            sources.append([col, unit, sample.get(key, ""), sample.get("Source Reference", "")])
        sources.append(["Actual Waiting Time", "minutes", self.target_note or "Not observed; deliberately blank. No model training or accuracy evaluation from these files.", ""])
        sources.append(["Time of Day", "category", TIME_BANDS, "Derived from observation hour, not an invented prediction timestamp."])
        sources.append(["Overview selection", "", f"Up to {self.overview_per_day} smallest SHA-256 record-ID hashes per local date; {len(rows)} of {self.rows} exported rows. Reproducible descriptive subset, not a representative passenger sample.", ""])
        sources.append(["Export status", "", note, ""])
        sources.append(["Availability", "", "Retrospective source windows; source publication and availability at prediction time are not established. Do not assert these totals were available at the start of the hour.", ""])
        sources.append(["Collection manifest", "", f"{self.prefix}_MANIFEST.json", "Original download URLs and SHA-256 hashes retained there."])
        sources.append(["Collection results", "", json.dumps(manifest.get("results", {}), ensure_ascii=False, default=str)[:32000], ""])
        for s in book:
            s.freeze_panes = "A2"; s.auto_filter.ref = s.dimensions
            for cell in s[1]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="17364A")
            for column in s.columns: s.column_dimensions[column[0].column_letter].width = min(65, max(18, len(str(column[0].value)) + 2))
        overview = self.output / f"{self.prefix}_OVERVIEW.xlsx"
        temporary = overview.with_suffix(".part.xlsx"); book.save(temporary); temporary.replace(overview)
        files = [{"filename": overview.name, "records": len(rows), "bytes": overview.stat().st_size, "sha256": sha256(overview)}, *self.parts]
        manifest["system_export"] = {"schema_version": "station-calendar-v2", "rows": self.rows,
                                     "day_counts": self.day_counts, "files": files,
                                     "overview_selection": f"Up to {self.overview_per_day} smallest SHA-256 observation-ID hashes per date.",
                                     "note": note, "target_imputation": False,
                                     "target_definition": self.target_note or "blank"}
        path = self.output / f"{self.prefix}_MANIFEST.json"
        path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        if library:
            library = pathlib.Path(library); library.mkdir(parents=True, exist_ok=True)
            index = library / "library.json"
            existing = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
            existing = [item for item in existing if not item["id"].startswith(self.prefix.lower() + "-")]
            for number, item in enumerate(files):
                source_file = self.output / item["filename"]
                if source_file.stat().st_size > 25 * 1024 * 1024: raise ValueError("Library package exceeds upload limit.")
                if source_file.resolve() != (library / source_file.name).resolve(): shutil.copy2(source_file, library / source_file.name)
                title = self.title + (" - overview" if number == 0 else f" - CSV part {number}")
                existing.append({"id": f"{self.prefix.lower()}-{number}", "title": title, "mode": self.mode.title(),
                                 "filename": source_file.name, "records": item["records"], "recordLabel": "source observations",
                                 "kind": "source_review" if self.mode == "bus" else "collected", "note": note})
            if path.resolve() != (library / path.name).resolve(): shutil.copy2(path, library / path.name)
            temporary_index = index.with_suffix(".json.part")
            temporary_index.write_text(json.dumps(existing, indent=2), encoding="utf-8"); temporary_index.replace(index)
        print(f"System export: {self.rows:,} rows; {len(self.parts)} CSV parts; {len(rows):,} overview rows. {path}")
        return manifest["system_export"]
