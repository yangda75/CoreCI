"""
分配测试任务给runner

1. 使用probe测试runner是否可用
2. 接收测试任务，分配给空闲的runner
"""

from contextlib import asynccontextmanager
import datetime
import logging
import threading
from typing import Optional
import uuid

import aiofiles as aiofiles
from fastapi import FastAPI, UploadFile

from dispatcher.runner_manager import RunnerManager, RunnerHandle
from dispatcher.storage import DispatcherStorage
from dispatcher.types import CreateTestJobRequest

logging.getLogger("uvicorn.access")
FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)

runner_manager: Optional[RunnerManager] = None
storage: Optional[DispatcherStorage] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner_manager
    global storage
    storage = DispatcherStorage()
    
    runner_manager = RunnerManager(storage)
    threading.Thread(group=None, target=runner_manager.run, daemon=True).start()
    yield
    runner_manager.shutdown()

app = FastAPI(title="CoreCI.TestRunner", lifespan=lifespan)

@app.get("/runners/list/")
async def get_all_runners():
    return runner_manager.get_all_runners()

@app.post("/runners/add/")
async def add_runner(runner: RunnerHandle):
    runner_manager.add_runner(runner)

@app.post("/jobs/submit/")
async def submit_test_job(job: CreateTestJobRequest):
    runner_manager.submit_job(job)


@app.post("/runners/register/")
async def add_runner(runner_handle: RunnerHandle):
    runner_manager.register(runner_handle)


@app.post("/versions/upload/{expected_md5}")
async def upload_build(file: UploadFile, expected_md5: str):
    storage.add_rdscore_zip(file.file.read(), file.filename, expected_md5)

@app.get("/versions/list/")
async def list_versions():
    return storage.list_versions()