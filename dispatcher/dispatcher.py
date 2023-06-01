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
    # fixme zip should be part of test job
    # todo add field os to test job
    build_name = file.filename.strip().strip(".zip")
    logging.info(f"uploaded file: {file.filename}")
    # install to builds dir
    # todo let test runner install
    logging.info(f"installing to dir: {ci_config.builds_dir}/{build_name}")
    installed_folder = pathlib.WindowsPath(ci_config.builds_dir, build_name)
    os.makedirs(installed_folder, exist_ok=True)
    content = file.file.read()
    file_like = io.BytesIO(content)
    zip = zipfile.ZipFile(file_like)
    zip.extractall(installed_folder)

    # create test job
    test_job = TestJob()
    test_job.testcase_folder = ci_config.testcase_folder
    test_job.report_path = ci_config.output_path
    test_job.id = build_name+"-"+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    test_job.start_time = str(datetime.datetime.now())
    test_job.rdscore_folder = str(installed_folder)
    runner_manager.submit_job(test_job)