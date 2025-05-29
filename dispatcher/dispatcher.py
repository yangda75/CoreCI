"""
分配测试任务给runner

1. 使用probe测试runner是否可用
2. 接收测试任务，分配给空闲的runner
"""

from contextlib import asynccontextmanager
import datetime
import json
import logging
import threading
from typing import Optional
import uuid

import aiofiles as aiofiles
from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Json

from dispatcher.runner_manager import RunnerManager, RunnerHandle
from dispatcher.storage import DispatcherStorage
from dispatcher.types import CreateTestJobRequest
from fastapi.templating import Jinja2Templates
from pathlib import Path

logging.getLogger("uvicorn.access")
FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)

runner_manager: Optional[RunnerManager] = None
storage: Optional[DispatcherStorage] = None

templates = Jinja2Templates(directory=str(Path(Path(__file__).resolve().parent, "templates")))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner_manager
    global storage
    storage = DispatcherStorage()
    
    runner_manager = RunnerManager(storage)
    threading.Thread(group=None, target=runner_manager.run, daemon=True).start()
    app.mount("/",
              StaticFiles(directory=str(Path(__file__).resolve().parent / "dist")),
              name="dist")
    yield
    runner_manager.shutdown()

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


@app.post("/api/runners/register/")
async def add_runner(runner_handle: RunnerHandle):
    runner_manager.register(runner_handle)


@app.post("/api/versions/upload/{expected_md5}")
async def upload_build(file: UploadFile, expected_md5: str):
    storage.add_rdscore_zip(file.file.read(), file.filename, expected_md5)

@app.get("/api/versions/list/")
async def list_versions():
    return storage.list_versions()