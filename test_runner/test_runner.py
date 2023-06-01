import datetime
import os
import threading

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse

from test_job import TestJob
from test_runner.test_runner_impl import TestRunner, create_sample_test_job
from test_runner.utils import kill_core
from pathlib import Path

app = FastAPI(title="CoreCI.TestRunner")

BASE_DIR = Path(__file__).resolve().parent

app.mount("/files", StaticFiles(directory=os.path.abspath("D:/test/runs")), name="TestOutput")
templates = Jinja2Templates(directory=str(Path(BASE_DIR, 'templates')))
runner = TestRunner(10)
threading.Thread(group=None, target=runner.run, daemon=True).start()
kill_core()

RUN_DIR = "D:/test/runs"

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/info")
async def info():
    return {"system": os.name, }  # TODO cpu, freq, mem, disk


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.post("/hi/{name}")
async def say_hi(name: str):
    return {"message": f"Hi {name}"}


@app.get("/sample/test-job")
async def sample_test_job():
    return create_sample_test_job()


@app.post("/test/job/")
async def submit_test_job(job: TestJob):
    return runner.submit_job(job)


@app.post("/test/job/accept")
async def accept_test_job(job: TestJob):
    # todo test if this runner can run the given job
    return not runner.running()


@app.get("/runs", response_class=HTMLResponse)
async def list_runs(request: Request):
    runs = os.scandir(RUN_DIR)
    [print(f.name) for f in runs]
    # [runid, report, updatetime]
    run_info_list = []
    print(len(run_info_list))
    for run in os.scandir(RUN_DIR):
        print(run.name)
        last_modified_epoch_seconds = run.stat().st_mtime
        print(last_modified_epoch_seconds)
        last_modified_time_str = datetime.datetime.fromtimestamp(last_modified_epoch_seconds)
        run_info_list.append(
            [run.name, request.base_url._url + "files/" + run.name + "/merged.html", last_modified_time_str])
    run_info_list = sorted(run_info_list, key=lambda a: a[2])
    print(run_info_list)
    base_path = request.url._url
    print(base_path)
    return templates.TemplateResponse(
        "list_runs.html",
        {"request": request, "runs": run_info_list, "base_path": base_path}
    )


@app.get("/runs/{runid}", response_class=HTMLResponse)
async def list_output_for_single_run(request: Request, runid: str):
    base_folder = os.path.join("D:/test/runs", runid)
    folders = list(filter(lambda f: f.startswith("test_"), os.listdir(base_folder)))
    base_path = request.base_url._url + "files/" + runid
    return templates.TemplateResponse(
        "files_of_run.html", {"request": request, "runid": runid, "base_path": base_path, "folders": folders}
    )


@app.post("/test/current-job/stop")
async def stop_current_job():
    runner.stop()


@app.get("/test/current-job")
async def get_current_job():
    return runner.current_job()
