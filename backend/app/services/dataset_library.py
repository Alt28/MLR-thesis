"""Local ETL packages, registered by a manifest; raw downloads stay outside Git."""
import json
import os
from pathlib import Path
from ..config import PROJECT_ROOT, MAX_UPLOAD_BYTES


def library_root():
    return Path(os.environ.get("MLR_DATASET_LIBRARY_DIR", PROJECT_ROOT / "data" / "collected")).resolve()


def entries():
    root = library_root()
    manifest = root / "library.json"
    if not manifest.is_file():
        return []
    items = json.loads(manifest.read_text(encoding="utf-8"))
    available = []
    for item in items:
        file = (root / item["filename"]).resolve()
        if (file.parent == root and file.suffix in (".csv", ".xlsx")
                and file.is_file() and 0 < file.stat().st_size <= MAX_UPLOAD_BYTES):
            available.append(item)
    return available


def dataset_path(dataset_id):
    item = next((item for item in entries() if item["id"] == dataset_id), None)
    if item is None:
        raise FileNotFoundError("This library dataset is unavailable. Run the ETL import export again.")
    return library_root() / item["filename"]
