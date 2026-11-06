from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Request, UploadFile, File, Query, HTTPException
from fastapi.responses import FileResponse
from ..schemas.requests import AnalysisRequest, CloudImportRequest, ConfigRequest, ReviewRequest, TrainingRequest
from ..config import PROJECT_ROOT, MAX_UPLOAD_BYTES
from src.config import ResearchConfig, PREDICTORS, TARGET
from src.data_loader import write_templates

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok", "application": "transit-lab", "version": "2.0.0"}


@router.get("/schema")
def schema():
    return {"predictors": PREDICTORS, "target": TARGET, "defaults": ResearchConfig().to_dict(), "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024)}


@router.get("/templates/{extension}")
def template(extension: str):
    if extension not in ("csv", "xlsx"): raise HTTPException(404, "Template not found.")
    write_templates(PROJECT_ROOT / "data")
    path = PROJECT_ROOT / "data" / f"transportation_template.{extension}"
    return FileResponse(path, filename=path.name)


@router.get("/experiments")
def experiments(request: Request):
    return request.app.state.store.list()


@router.post("/experiments", status_code=201)
async def upload(request: Request, file: UploadFile = File(...)):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(content) > MAX_UPLOAD_BYTES: raise HTTPException(413, "The dataset exceeds the 25 MB upload limit.")
    if not content: raise ValueError("Choose a nonempty recorded dataset.")
    # Run parsing in a thread, keeping the API responsive while Excel is read.
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(request.app.state.store.create, file.filename or "dataset.csv", content)


@router.get("/experiments/{sid}")
def experiment(sid: str, request: Request):
    store = request.app.state.store
    with store.lock: return store.summary(store.get(sid))


@router.post("/cloud-import", status_code=201)
async def cloud_import(payload: CloudImportRequest, request: Request):
    from ..services.cloud_import import fetch_dataset
    from starlette.concurrency import run_in_threadpool
    name, content = await fetch_dataset(payload.url, payload.provider)
    return await run_in_threadpool(request.app.state.store.create, name, content)


@router.put("/experiments/{sid}/config")
def configuration(sid: str, payload: ConfigRequest, request: Request):
    return request.app.state.store.configure(sid, payload)


@router.put("/experiments/{sid}/reviews")
def review(sid: str, payload: ReviewRequest, request: Request):
    return request.app.state.store.review(sid, payload)


@router.post("/experiments/{sid}/train", status_code=202)
def train(sid: str, payload: TrainingRequest, request: Request):
    return request.app.state.store.train(sid, payload)


@router.post("/experiments/{sid}/analyze", status_code=202)
def analyze(sid: str, payload: AnalysisRequest, request: Request):
    return request.app.state.store.analyze(sid, payload)


@router.get("/experiments/{sid}/tables/{name}")
def table(sid: str, name: str, request: Request, search: str = "", offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=200), transport_mode: Literal["all", "bus", "train", "unspecified"] = "all"):
    return request.app.state.store.table(sid, name, search, offset, limit, transport_mode)


@router.get("/experiments/{sid}/records/{record_id:path}")
def record(sid: str, record_id: str, request: Request):
    return request.app.state.store.record(sid, record_id)


@router.get("/experiments/{sid}/figures/{name}")
def figure(sid: str, name: str, request: Request, theme: Literal["light", "dark"] = "light"):
    return FileResponse(request.app.state.store.figure(sid, name, theme), media_type="image/png")


@router.get("/experiments/{sid}/download/{kind}")
def download(sid: str, kind: str, request: Request, table: str | None = None):
    path = request.app.state.store.artifact(sid, kind, table)
    return FileResponse(path, filename=path.name)
