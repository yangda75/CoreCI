"""
分配测试任务给runner

1. 使用probe测试runner是否可用
2. 接收测试任务，分配给空闲的runner
"""
import datetime
import io
import logging
import os
import pathlib
import threading
import zipfile

import aiofiles as aiofiles
from fastapi import FastAPI, UploadFile

from config import CiConfig
from dispatcher.runner_manager import RunnerManager, RunnerHandle
from test_job import TestJob

logging.getLogger("uvicorn.access")
FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT,level=logging.INFO)

app = FastAPI(title="CoreCI.Dispatcher")

runner_manager = RunnerManager()

threading.Thread(group=None, target=runner_manager.run, daemon=True).start()
ci_config = CiConfig()


@app.get("/test/runner/")
async def get_all_runners():
    return runner_manager.get_all_runners()


@app.post("/test/job/")
async def submit_test_job(job: TestJob):
    runner_manager.submit_job(job)


@app.post("/test/runner/")
async def add_runner(runner_handle: RunnerHandle):
    runner_manager.register(runner_handle)


@app.post("/build/windows/upload/")
async def upload_build(file: UploadFile):
    """
    Create test job for uploaded file
    :param file: rdscore build to be tested
    :return: None
    """
    test_job = TestJob()
    test_job.rdscore_zip = file.file.read()
    test_job.os = "Windows"
