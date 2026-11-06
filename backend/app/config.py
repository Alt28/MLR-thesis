"""Server settings; research defaults remain in src/config.py."""
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_ROOT = Path(os.environ.get("MLR_STORAGE_DIR", PROJECT_ROOT / ".web-data")).resolve()
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
