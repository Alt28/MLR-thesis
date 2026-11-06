"""Read recorded observations, validate the schema, and split before learning."""
from pathlib import Path
from io import BytesIO
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from .config import PREDICTORS, CATEGORICAL, NUMERICAL, TARGET, ROW_ID


def validate_data(frame, require_target=True):
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
        if data[col].isna().any():
            raise ValueError(f"{col}: missing values; correct the source file before importing.")
    for col in (*NUMERICAL, *([TARGET] if require_target else [])):
        try:
            data[col] = pd.to_numeric(data[col], errors="raise").astype(float)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{col}: all values must be numerical.") from exc
        if not np.isfinite(data[col]).all() or (data[col] < 0).any():
            raise ValueError(f"{col}: values must be finite and nonnegative.")
    for col in CATEGORICAL:
        data[col] = data[col].astype(str).str.strip()
        if data[col].eq("").any():
            raise ValueError(f"{col}: empty category values are not allowed.")
    if ROW_ID not in data:
        data.insert(0, ROW_ID, [f"R{i:06d}" for i in range(1, len(data) + 1)])
    elif data[ROW_ID].isna().any():
        raise ValueError("Record IDs must not be missing.")
    data[ROW_ID] = data[ROW_ID].astype(str).str.strip()
    if data[ROW_ID].duplicated().any() or data[ROW_ID].eq("").any():
        raise ValueError("Record IDs must be unique and nonempty.")
    return data.set_index(ROW_ID, drop=False)


def load_dataset(path):
    path = Path(path)
    text_columns = {ROW_ID: str, "Station ID": str, "Station": str}
    if path.suffix.lower() == ".csv":
        data = pd.read_csv(path, dtype=text_columns, keep_default_na=False)
    elif path.suffix.lower() == ".xlsx":
        data = pd.read_excel(path, dtype=text_columns, keep_default_na=False)
    else:
        raise ValueError("Use a CSV or .xlsx Excel file.")
    return validate_data(data)


def load_dataset_bytes(name, content, require_target=False):
    suffix = Path(name).suffix.lower()
    stream = BytesIO(content)
    text_columns = {ROW_ID: str, "Station ID": str, "Station": str}
    if suffix == ".csv":
        data = pd.read_csv(stream, dtype=text_columns, keep_default_na=False)
    elif suffix == ".xlsx":
        data = pd.read_excel(stream, dtype=text_columns, keep_default_na=False)
    else:
        raise ValueError("Use a CSV or .xlsx Excel file.")
    return validate_data(data, require_target=require_target)


def split_dataset(data, config):
    config.validate()
    if len(data) < 10:
        raise ValueError("At least 10 recorded observations are needed to create a split; substantially more are needed for research.")
    train, test = train_test_split(data, test_size=config.test_size, random_state=config.random_state)
    if len(train) < 2 or len(test) < 2:
        raise ValueError("The chosen split needs at least two training and two test rows.")
    return train.copy(), test.copy()


def write_templates(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(columns=PREDICTORS + (TARGET, "Station ID"))
    for suffix in ("csv", "xlsx"):
        path = directory / f"transportation_template.{suffix}"
        if not path.exists():
            if suffix == "csv":
                frame.to_csv(path, index=False)
            else:
                frame.to_excel(path, index=False)
