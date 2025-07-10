"""
分配测试任务给runner

1. 使用probe测试runner是否可用
2. 接收测试任务，分配给空闲的runner
"""

from contextlib import asynccontextmanager
import json
import logging
import threading

import aiofiles as aiofiles
from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from dispatcher.runner_manager import RunnerManager, RunnerHandle
from dispatcher.storage import VersionStorage, TestJobStorage
from dispatcher.types import CreateTestJobRequest
from fastapi.templating import Jinja2Templates
from pathlib import Path

logging.getLogger("uvicorn.access")
FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)

runner_manager: RunnerManager | None = None
version_storage: VersionStorage | None = None
job_storage: TestJobStorage | None = None

templates = Jinja2Templates(directory=str(Path(Path(__file__).resolve().parent, "templates")))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner_manager
    global version_storage
    version_storage = VersionStorage()
    global job_storage
    job_storage = TestJobStorage()
    runner_manager = RunnerManager(version_storage, job_storage)
    threading.Thread(group=None, target=runner_manager.run, daemon=True).start()
    app.mount("/",
              StaticFiles(directory=str(Path(__file__).resolve().parent / "dist")),
              name="dist")
    yield

app = FastAPI(title="CoreCI.TestRunner", lifespan=lifespan)
# read manifest.json
ui_manifest = json.loads(
    (Path(__file__).resolve().parent / "dist" / ".vite" / "manifest.json").read_text("utf-8")
)
@app.get("/")
async def index(request: Request):
    context = {
        "request": request,
        "title": "CoreCI Test Runner",
        "version": "1.0.0",
        "manifest": ui_manifest
    }
    return templates.TemplateResponse( name="index.html",context= context)

@app.get("/api/runners/list/")
async def get_all_runners():
    return runner_manager.get_all_runners()

@app.post("/api/runners/add/")
async def add_runner(runner: RunnerHandle):
    runner_manager.add_runner(runner)

@app.post("/api/jobs/submit/")
async def submit_test_job(job: CreateTestJobRequest):
    runner_manager.submit_job(job)

@app.post("/api/versions/upload/{expected_md5}")
async def upload_build(file: UploadFile, expected_md5: str):
    version_storage.add_rdscore_zip(file.file.read(), file.filename, expected_md5)

@app.get("/api/versions/list/")
async def list_versions():
    return version_storage.list_versions()

@app.get("/api/versions/download/{version_name}")
async def download_version(version_name: str):
    version_path = Path(version_storage.rdscore_versions_path) / version_name
    if not version_path.exists():
        return {"error": "version not found"}
    async with aiofiles.open(version_path, mode='rb') as f:
        content = await f.read()
    return HTMLResponse(content=content, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={version_name}"})


@app.get("/api/jobs/list/active")
async def list_active_jobs():
    return runner_manager.get_active_jobs()