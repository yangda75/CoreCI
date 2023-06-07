"""
实现执行测试脚本的功能

T1
测试请求->测试任务->测试任务队列
T2
执行任务队列中的任务->报告
"""
import os
import pathlib
import queue
import subprocess
import time
import uuid

from datetime import datetime

from test_job import TestJob
from test_runner.utils import kill_core, start_core

pytest_path = "C:/Users/yda/anaconda3/envs/py310/Scripts/pytest.exe"
pytest_html_merger = "C:/Users/yda/anaconda3/envs/py310/Scripts/pytest_html_merger.exe"


def create_sample_test_job() -> TestJob:
    j = TestJob()
    j.id = uuid.uuid1()
    j.start_time = datetime.now()
    j.testcase_folder = pathlib.Path("C:/projects/AutoTest")
    j.report_path = pathlib.Path("D:/test_runs")
    return j


class TestRunner:
    _test_job_q = queue.Queue()
    _stop_current_job = False
    _current_job: TestJob | None = None
    _running = False

    def __init__(self, job_q_limit):
        self._test_job_q.maxsize = job_q_limit

    def stop(self):
        self._stop_current_job = True

    def current_job(self):
        return self._current_job

    def run(self):
        print("Started TestRunner")
        while True:
            if self._test_job_q.empty():
                time.sleep(1)
                continue
            self._running = True
            job = self._test_job_q.get()
            self._current_job = job
            self.run_test_job(job)
            self._running = False

    def run_test_job(self, job: TestJob):
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
        test_job.id = build_name + "-" + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        test_job.start_time = str(datetime.datetime.now())
        test_job.rdscore_folder = str(installed_folder)
        runner_manager.submit_job(test_job)
        # stop running core
        kill_core()
        # start core in job folder
        start_core(job.rdscore_folder)
        time.sleep(10) # todo verify core is started
        # find folders
        folders = []
        if job.testcase_folder is None:
            raise Exception("Testcase folder cannot be None")
        test_rdscore_path = pathlib.Path(job.testcase_folder).joinpath("test_rdscore")

        run_output_path = os.path.join(job.report_path, job.id)
        for entry in os.scandir(test_rdscore_path):
            if self._stop_current_job:
                self._stop_current_job = False
                print(f"{job.id} stopped")
                break
            if not entry.name.startswith("test"):
                continue
            if not entry.is_dir():
                continue
            print(f"path: {entry.path}, name: {entry.name}")
            # run test in this folder

            output_path = pathlib.Path(job.report_path, job.id, entry.name)
            os.makedirs(output_path, exist_ok=True)
            logfile = open(os.path.join(output_path, "pytest.log"), "w")
            report_html_path = os.path.join(output_path, f"{entry.name}.html")
            test_ret = subprocess.call(
                [pytest_path, "-m", job.testcase_mark, f"--html={report_html_path}", "-x", "--timeout=120", entry.path],
                stdout=logfile,
                stderr=logfile)
            print(f"{entry.name}, test result: {test_ret}, report: {report_html_path}")
            # merge report after each folder
            subprocess.call(
                [pytest_html_merger, "-i", run_output_path, "-o", os.path.join(run_output_path, "merged.html")])

    def submit_job(self, job: TestJob):
        if job.id is None:
            job.id = str(uuid.uuid1())
        self._test_job_q.put(job)
        return job

    def running(self):
        return self._running