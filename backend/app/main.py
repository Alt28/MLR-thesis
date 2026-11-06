"""Local API and compiled React application. No external service is required."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from .config import STORAGE_ROOT, FRONTEND_DIST
from .services.experiments import ExperimentStore
from .api.routes import router


def create_app(storage_root=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.store = ExperimentStore(storage_root or STORAGE_ROOT)
        yield
        app.state.store.close()

    app = FastAPI(title="Transit Lab Research API", version="2.0.0", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def local_origin_guard(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
            from urllib.parse import urlsplit
            origin_host = urlsplit(origin).hostname
            request_host = request.url.hostname
            allowed_origins = {value.strip() for value in os.environ.get("MLR_ALLOWED_ORIGINS", "").split(",") if value.strip()}
            allowed = origin.rstrip("/") in allowed_origins or origin_host == request_host or (origin_host in ("localhost", "127.0.0.1") and request_host in ("localhost", "127.0.0.1"))
            if not allowed: return JSONResponse({"detail": "Use the local application's browser address."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(ValueError)
    @app.exception_handler(TypeError)
    def invalid_input(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    app.include_router(router)
    for folder in ("assets", "fonts"):
        if (FRONTEND_DIST / folder).exists():
            app.mount(f"/{folder}", StaticFiles(directory=FRONTEND_DIST / folder), name=folder)

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"): raise HTTPException(404, "API route not found.")
        if path == "favicon.svg" and (FRONTEND_DIST / path).exists(): return FileResponse(FRONTEND_DIST / path)
        index = FRONTEND_DIST / "index.html"
        if not index.exists(): return JSONResponse({"detail": "Frontend has not been built. Run setup.ps1 or npm run build in frontend/."}, status_code=503)
        return FileResponse(index)
    return app


app = create_app()
