"""Read recorded observations, validate the schema, and split before learning."""
from pathlib import Path
from io import BytesIO
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from .config import PREDICTORS, CATEGORICAL, NUMERICAL, CATEGORY_VALUES, SCHEMA_VERSION, TARGET, ROW_ID

GROUP_COLUMNS = ("Station / Stop", "Station ID", "Station")


def validate_data(frame, require_target=True, allow_missing_predictors=False):
    frame = frame.copy()
    if "Observed Vehicle Frequency" in frame:
        if "Vehicle Frequency" in frame:
            raise ValueError("Use only Vehicle Frequency, or its import alias, not both columns.")
        frame = frame.rename(columns={"Observed Vehicle Frequency": "Vehicle Frequency"})
    required = [*PREDICTORS, *([TARGET] if require_target else [])]
    if frame.columns.duplicated().any():
        raise ValueError("Duplicate column names are not allowed.")
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    if frame.empty:
        raise ValueError("This file has no observations. Fill the template with recorded data first.")
    data = frame.copy()
    for col in required:
        if allow_missing_predictors and col in NUMERICAL:
            continue
        if data[col].isna().any():
            raise ValueError(f"{col}: missing values; correct the source file before importing.")
    for col in (*NUMERICAL, *([TARGET] if require_target else [])):
        if data[col].map(lambda value: isinstance(value, (bool, np.bool_))).any():
            raise ValueError(f"{col}: all values must be numerical, not booleans.")
        missing = data[col].isna() | data[col].astype(str).str.strip().eq("")
        review_only = allow_missing_predictors and col in NUMERICAL
        if missing.any() and not review_only:
            raise ValueError(f"{col}: missing values; recorded values are required.")
        try:
            data[col] = pd.to_numeric(data[col].mask(missing), errors="raise").astype(float)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{col}: all values must be numerical.") from exc
        present = data.loc[~missing, col] if review_only else data[col]
        if not np.isfinite(present).all() or (present < 0).any():
            raise ValueError(f"{col}: values must be finite and nonnegative.")
    for col in CATEGORICAL:
        data[col] = data[col].astype(str).str.strip()
        if data[col].eq("").any():
            raise ValueError(f"{col}: empty category values are not allowed.")
        if col in CATEGORY_VALUES:
            canonical = {value.casefold(): value for value in CATEGORY_VALUES[col]}
            normalized = data[col].str.casefold().map(canonical)
            if normalized.isna().any():
                raise ValueError(f"{col}: unexpected categories. Use: {', '.join(CATEGORY_VALUES[col])}.")
            data[col] = normalized
    if ROW_ID not in data:
        source_id = next((c for c in ("Observation ID", "Source Observation ID") if c in data
                          and not data[c].fillna("").astype(str).str.strip().eq("").all()), None)
        data.insert(0, ROW_ID, data[source_id] if source_id else [f"R{i:06d}" for i in range(1, len(data) + 1)])
    if data[ROW_ID].isna().any():
        raise ValueError("Record IDs must not be missing.")
    data[ROW_ID] = data[ROW_ID].astype(str).str.strip()
    if data[ROW_ID].duplicated().any() or data[ROW_ID].eq("").any():
        raise ValueError("Record IDs must be unique and nonempty.")
    validate_prediction_timing(data)
    return data.set_index(ROW_ID, drop=False)


def validate_prediction_timing(data):
    """Check supplied audit timestamps; six-column files still need a researcher declaration."""
    origin = next((c for c in ("Prediction Timestamp", "Passenger Arrival Timestamp") if c in data), None)
    if origin is None:
        return
    moments = pd.to_datetime(data[origin], errors="coerce", utc=True)
    if moments.isna().any():
        raise ValueError(f"{origin}: valid timestamps are required when timing metadata is supplied.")
    for col in ("Frequency Window End", "Passenger Volume Window End", "Inputs Available At"):
        if col in data:
            ends = pd.to_datetime(data[col], errors="coerce", utc=True)
            if ends.isna().any() or (ends > moments).any():
                raise ValueError(f"{col}: counts must be available no later than the prediction time; future-window data would leak information.")


def attach_source_audit(data, audit):
    """Join only by an explicit unique identifier or an explicitly exported CSV row number."""
    keys = [c for c in (ROW_ID, "Observation ID", "Source Observation ID") if c in data and c in audit]
    row_key = "Six-column CSV row number"
    if keys:
        key = keys[0]
    elif row_key in audit:
        data = data.copy()
        data[row_key] = np.arange(2, len(data) + 2)
        key = row_key
    else:
        raise ValueError("Source_Audit needs a shared observation ID or explicit Six-column CSV row number. Duplicate predictor combinations cannot identify observations.")
    if (audit[key].isna().any() or audit[key].astype(str).str.strip().eq("").any()
            or data[key].isna().any() or data[key].astype(str).str.strip().eq("").any()
            or audit[key].duplicated().any() or data[key].duplicated().any()):
        raise ValueError("Source_Audit observation keys must be unique and complete.")
    if set(data[key]) != set(audit[key]):
        raise ValueError("Source_Audit keys do not match the dataset exactly; do not join by apparent row similarity.")
    renamed = audit.rename(columns={c: f"Source audit: {c}" for c in audit if c != key and c in data})
    return data.merge(renamed, on=key, how="left", validate="one_to_one", sort=False)


def read_frame(stream, suffix):
    text_columns = {c: str for c in (ROW_ID, "Station / Stop", "Station ID", "Station", "Observation ID", "Source Observation ID", "Source Stop ID", "Source Route ID", "MTA Complex ID")}
    if suffix == ".csv":
        header = pd.read_csv(stream, header=None, nrows=1, keep_default_na=False).iloc[0]
        stream.seek(0)
        if header.duplicated().any():
            raise ValueError("Duplicate column names are not allowed.")
        return pd.read_csv(stream, dtype=text_columns, keep_default_na=False)
    if suffix == ".xlsx":
        with pd.ExcelFile(stream) as book:
            headings = pd.read_excel(book, header=None, nrows=1, keep_default_na=False)
            if headings.empty:
                raise ValueError("This file has no observations or column headings. Fill a current template first.")
            header = headings.iloc[0]
            if header.duplicated().any():
                raise ValueError("Duplicate column names are not allowed.")
            data = pd.read_excel(book, dtype=text_columns, keep_default_na=False)
            if "Source_Audit" in book.sheet_names:
                data = attach_source_audit(data, pd.read_excel(book, sheet_name="Source_Audit", dtype=text_columns, keep_default_na=False))
            return data
    raise ValueError("Use a CSV or .xlsx Excel file.")


def load_dataset(path):
    path = Path(path)
    return load_dataset_bytes(path.name, path.read_bytes(), require_target=True)


def load_dataset_bytes(name, content, require_target=False):
    suffix = Path(name).suffix.lower()
    stream = BytesIO(content)
    data = read_frame(stream, suffix)
    return validate_data(data, require_target=require_target)


def recorded_target_mask(data):
    """Zero is a recorded wait. Only nulls and empty/whitespace cells are unknown."""
    if TARGET not in data:
        return pd.Series(False, index=data.index)
    values = data[TARGET]
    return values.notna() & values.astype(str).str.strip().ne("")


def inspect_dataset_bytes(name, content):
    """Validate an upload and identify its purpose without creating a training run."""
    data = validate_data(read_frame(BytesIO(content), Path(name).suffix.lower()),
                         require_target=False, allow_missing_predictors=True)
    missing = {col: int(data[col].isna().sum()) for col in NUMERICAL if data[col].isna().any()}
    recorded = int(recorded_target_mask(data).sum())
    if 0 < recorded < len(data):
        raise ValueError(
            f"{TARGET} is recorded for {recorded} of {len(data)} rows. "
            "Separate rows with recorded waits into a training file and rows with blank waits "
            "into a prediction file. Do not fill unknown waits with zero or estimates."
        )
    if recorded:
        validate_data(data, require_target=True)
    source_notes = []
    for col in ("Source Reference", "Source Dataset", "Passenger Volume Definition", "Vehicle Frequency Definition", "Definition Note", "Time Band Definition", "Timing Note"):
        if col in data:
            for value in data[col].dropna().astype(str).unique()[:10]:
                if value.strip(): source_notes.append(f"{col}: {value}")
    return {"purpose": "training" if recorded else "source_review" if missing else "prediction", "rows": len(data),
            "recorded_waits": recorded, "unknown_waits": len(data) - recorded,
            "target_column_present": TARGET in data.columns, "schema_version": SCHEMA_VERSION,
            "preview": json.loads(data.head(20).to_json(orient="records")),
            "columns": list(data.columns), "transport_mode": dataset_mode(data),
            "missing_predictors": missing, "source_notes": source_notes,
            "warnings": list(SOURCE_WARNINGS)}


SOURCE_WARNINGS = (
    "Passenger Volume and Vehicle Frequency must be recorded in windows ending no later than the prediction time; full future-hour totals would leak future information.",
    "NYC subway: Vehicle Frequency is station-complex service, potentially across multiple platforms; it is not necessarily service on the passenger's platform.",
    "AC Transit APC: counts may cover only counter-equipped buses. They must not be described as complete fleet service frequency.",
    "SUNT: repeated vehicle-presence counts are not distinct hourly bus arrivals. Identify service events before calculating Vehicle Frequency.",
)


def dataset_mode(data):
    from .transport_metadata import transport_labels
    from .config import ResearchConfig
    labels, column = transport_labels(data, ResearchConfig())
    modes = set(labels)
    if column and (len(modes) != 1 or "unspecified" in modes):
        raise ValueError("Use separate Bus and Train datasets, with a consistent valid Transport Mode on every row.")
    return next(iter(modes)) if column else "unknown"


def load_prediction_dataset_bytes(name, content):
    data = load_dataset_bytes(name, content, require_target=False)
    if recorded_target_mask(data).any():
        raise ValueError(
            f"Prediction-only files must omit {TARGET} or leave every value in that column blank; "
            "use the training and evaluation workflow for recorded waits."
        )
    # An empty target is neither a predictor nor an observed outcome. Never impute it.
    return data.drop(columns=[TARGET], errors="ignore")


def resolve_group_column(data, config):
    """Metadata identifier that keeps related observations in one partition; never a predictor."""
    configured = str(getattr(config, "split_group_column", "") or "").strip()
    lookup = {str(column).strip().lower(): column for column in data.columns}
    for name in ([configured] if configured else list(GROUP_COLUMNS)):
        if name.strip().lower() in lookup:
            return lookup[name.strip().lower()]
    if configured:
        raise ValueError(f"Grouped splitting needs the '{configured}' column; this dataset does not contain it.")
    raise ValueError("Grouped splitting needs a Station ID (or Station) column, or a configured group column.")


def grouped_split(data, config):
    """Keep every observation of one group together, so repeated trips cannot span both partitions."""
    column = resolve_group_column(data, config)
    groups = data[column].astype(str).str.strip()
    if data[column].isna().any() or groups.eq("").any():
        raise ValueError(f"{column}: grouped splitting requires a group value for every observation.")
    if groups.nunique() < 2:
        raise ValueError(f"{column}: grouped splitting requires at least two distinct groups.")
    splitter = GroupShuffleSplit(n_splits=1, test_size=config.test_size, random_state=config.random_state)
    train_rows, test_rows = next(splitter.split(data, groups=groups))
    return data.iloc[train_rows], data.iloc[test_rows], column


def split_dataset(data, config):
    config.validate()
    if len(data) < 10:
        raise ValueError("At least 10 recorded observations are needed to create a split; substantially more are needed for research.")
    if config.split_method == "grouped":
        train, test, column = grouped_split(data, config)
        if len(train) < 2 or len(test) < 2:
            raise ValueError(f"The grouped split needs at least two training and two test rows. Adjust the test fraction or add more {column} groups.")
    else:
        train, test = train_test_split(data, test_size=config.test_size, random_state=config.random_state)
        if len(train) < 2 or len(test) < 2:
            raise ValueError("The chosen split needs at least two training and two test rows.")
    return train.copy(), test.copy()


def write_templates(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(columns=PREDICTORS + (TARGET, "Transport Mode", "Observation ID"))
    for suffix in ("csv", "xlsx"):
        path = directory / f"transportation_template.{suffix}"
        if path.exists():
            existing = pd.read_csv(path) if suffix == "csv" else pd.read_excel(path)
            if not existing.empty:
                raise ValueError(f"{path.name} contains observations. Preserve it and choose a different template directory.")
            if list(existing.columns) == list(frame.columns):
                continue
        if suffix == "csv":
            frame.to_csv(path, index=False)
        else:
            frame.to_excel(path, index=False)
