from contextlib import asynccontextmanager
import datetime
import os
import threading
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from test_runner.config import CI_CONFIG
from test_runner.test_job import CreateTestJobRequest
from test_runner.test_runner_impl import TestRunner, create_sample_test_job
from pathlib import Path

templates = {}
runner: Optional[TestRunner] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # setup
    if not os.path.exists(CI_CONFIG.output_path):
        os.makedirs(CI_CONFIG.output_path)
    if not os.path.exists(CI_CONFIG.jobs_dir):
        os.makedirs(CI_CONFIG.jobs_dir)
    global templates
    templates = Jinja2Templates(
        directory=str(Path(Path(__file__).resolve().parent, "templates"))
    )
    app.mount(
        "/files",
        StaticFiles(directory=os.path.abspath(CI_CONFIG.output_path)),
        name="TestOutput",
    )
    global runner
    runner = TestRunner(10)
    threading.Thread(group=None, target=runner.run, daemon=True).start()

    yield

    # teardown
    runner.stop()


app = FastAPI(title="CoreCI.TestRunner", lifespan=lifespan)


@app.get("/ping")
async def root():
    return {"message": "pong"}

@app.get("/info")
async def info():
    return runner.get_info()

@app.get("/sample/test-job")
async def sample_test_job():
    return create_sample_test_job()


@app.post("/test/job/")
async def submit_test_job(job: CreateTestJobRequest):
    return runner.submit_job(job)


@app.get("/test/storage/versions")
async def list_versions():
    return runner.storage.list_rdscore_versions()


@app.post("/test/job/accept")
async def accept_test_job(job: CreateTestJobRequest):
    return runner.accept_test_job(job)


@app.get("/runs", response_class=HTMLResponse)
async def list_runs(request: Request):
    # [runid, report, updatetime]
    run_info_list = []
    for run in os.scandir(CI_CONFIG.output_path):
        last_modified_epoch_seconds = run.stat().st_mtime
        last_modified_time_str = datetime.datetime.fromtimestamp(
            last_modified_epoch_seconds
        )
        run_info_list.append(
            [
                run.name,
                request.base_url._url + "files/" + run.name + "/merged.html",
                last_modified_time_str,
            ]
        )
    run_info_list = sorted(run_info_list, key=lambda a: a[2])
    base_path = request.url._url
    return templates.TemplateResponse(
        "list_runs.html",
        {"request": request, "runs": run_info_list, "base_path": base_path},
    )


@app.get("/runs/{runid}", response_class=HTMLResponse)
async def list_output_for_single_run(request: Request, runid: str):
    base_folder = os.path.join(CI_CONFIG.output_path, runid)
    folders = list(filter(lambda f: f.startswith("test_"), os.listdir(base_folder)))
    base_path = request.base_url._url + "files/" + runid
    return templates.TemplateResponse(
        "files_of_run.html",
        {
            "request": request,
            "runid": runid,
            "base_path": base_path,
            "folders": folders,
        },
    )


@app.post("/test/current-job/stop")
async def stop_current_job():
    runner.stop()


@app.get("/test/current-job")
async def get_current_job():
    return runner.current_job()
