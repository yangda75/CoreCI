"""
实现执行测试脚本的功能

T1
测试请求->测试任务->测试任务队列
T2
执行任务队列中的任务->报告
"""

import os
import pathlib
import subprocess
import time
import uuid

from datetime import datetime

from test_runner.config import CI_CONFIG
from test_runner.test_job import AcceptTestJobResponse, CreateTestJobResponse, TestJob, CreateTestJobRequest, TestJobStatus
from test_runner.utils import (
    is_core_running,
    kill_core,
    start_core,
    wait_until_core_started,
    wait_until_core_stopped,
)

def create_sample_test_job() -> TestJob:
    j = TestJob()
    j.id = str(uuid.uuid1())
    j.start_time = datetime.now().isoformat()
    j.testcase_folder = CI_CONFIG.testcase_folder
    j.report_path = CI_CONFIG.output_path
    return j


def identify_os():
    return os.name

class TestRunner:
    _stop_current_job = False
    _current_job: TestJob | None = None
    _running = False
    _os: str

    def __init__(self, job_q_limit):
        self._os = "windows" if identify_os() == "nt" else "linux"
        print("os: "+self._os)
        
    def stop(self):
        self._stop_current_job = True

    def current_job(self):
        return self._current_job
    
    def run(self):
        print("Started TestRunner")
        #self.load_unfinished_jobs()
        while True:
            if self._current_job is None:
                print("No current job, waiting for new job")
            if self._stop_current_job:
                print("Stopping current job")
                if self._current_job:
                    self._current_job.status = TestJobStatus.failed
                    self._current_job.error = "Stopped by user"
                self._stop_current_job = False
                continue
            self._running = True

    def accept_test_job(self, job: CreateTestJobRequest)->AcceptTestJobResponse:
        # 如果正在执行，就不能接受新任务
        if self._running:
            return AcceptTestJobResponse(accepted=False, error="TestRunner is currently running a job")
        return AcceptTestJobResponse(accepted=True)

    def run_test_job(self, job: TestJob):
        if job.testcase_folder is None:
            job.status = TestJobStatus.failed
            job.error = "Testcase folder cannot be None"
            return
        if job.rdscore_version is None:
            job.status = TestJobStatus.failed
            job.error = "Rdscore version cannot be None"
            return

        if not self._stop_core_and_start(job):
            job.status = TestJobStatus.failed
            job.error = "Core did not start successfully"
            return

        job.status = TestJobStatus.running

        test_rdscore_path = pathlib.Path(job.testcase_folder).joinpath("test_rdscore")
        run_output_path = os.path.join(job.report_path, job.id)

        for entry in os.scandir(test_rdscore_path):
            if not entry.name.startswith("test") or not entry.is_dir():
                continue
            if not self._process_entry(entry, job, run_output_path):
                job.status = TestJobStatus.failed
                job.error = "Failed to process entry"
                break

        job.status = TestJobStatus.finished

    def get_info(self):
        return {"os": CI_CONFIG.os, "current_job": self._current_job}

    def _stop_core_and_start(self, job: TestJob) -> bool:
        if is_core_running():
            kill_core()
        if not wait_until_core_stopped(timeout_sec=30):
            job.status = TestJobStatus.failed
            job.error = "Core did not stop successfully within 30 seconds"
            return False

        start_core(job.rdscore_file_path_abs)
        if not wait_until_core_started(timeout_sec=30):
            job.status = TestJobStatus.failed
            job.error = "Core did not start successfully within 30 seconds"
            return False
        return True

    def _process_entry(self, entry, job: TestJob, run_output_path: str) -> bool:
        if entry.name in job.finished_cases:
            print(f"skip {entry.name} because it is already finished")
            return True
        if self._stop_current_job:
            self._stop_current_job = False
            print(f"{job.id} stopped")
            job.status = TestJobStatus.failed
            job.error = "Stopped by user"
            return False

        job.current_case = entry.name
        if not is_core_running():
            start_core(job.rdscore_file_path_abs)
        if not wait_until_core_started(timeout_sec=30):
            job.status = TestJobStatus.failed
            job.error = "Core did not start successfully within 30 seconds"
            return False

        output_path = pathlib.Path(job.report_path, job.id, entry.name)
        os.makedirs(output_path, exist_ok=True)
        logfile = open(os.path.join(output_path, "pytest.log"), "w")
        report_html_path = os.path.join(output_path, f"{entry.name}.html")
        test_ret = subprocess.call(
            [
                CI_CONFIG.pytest_path,
                "-m",
                job.testcase_mark,
                f"--html={report_html_path}",
                "-x",
                "--timeout=120",
                entry.path,
            ],
            stdout=logfile,
            stderr=logfile,
        )
        print(f"{entry.name}, test result: {test_ret}, report: {report_html_path}")
        job.current_case = None
        job.finished_cases.append(entry.name)
        subprocess.call(
            [
                CI_CONFIG.pytest_html_merger,
                "-i",
                run_output_path,
                "-o",
                os.path.join(run_output_path, "merged.html"),
            ]
        )
        return True
  
    def submit_job(self, job_input: CreateTestJobRequest):
        if not self.accept_test_job(job_input):
            return CreateTestJobResponse(created=False)
        job = TestJob(**job_input.dict())
        job.status = TestJobStatus.pending
        job.testcase_folder = CI_CONFIG.testcase_folder
        job.report_path = CI_CONFIG.output_path
        job.id = str(uuid.uuid1())
        job.start_time = datetime.now().isoformat()
        job.rdscore_file_url = job_input.rdscore_file_url
        self._test_job_q.put(job)
        return CreateTestJobResponse(created=True, job=job)

    def running(self):
        return self._running
