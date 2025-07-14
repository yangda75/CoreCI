import logging
from pathlib import Path
import sqlite3
import time
import requests

import uuid
import os

from dispatcher.config import CONFIG
from dispatcher.types import CreateTestJobRequest, RunnerHandle, TestJob
from dispatcher.storage import VersionStorage, TestJobStorage

def send_version(zip_file: bytes, expected_md5: str, runner: RunnerHandle):
    res = requests.post(f"{runner.baseurl}/test/storage/versions/upload/{expected_md5}", files={"file": zip_file})
    logging.info(f"try to send version {runner.id} {res.text}")


def accept_job(job: CreateTestJobRequest, runner: RunnerHandle):
    res = requests.post(f"{runner.baseurl}/test/job/accept", json=job.dict())
    logging.info(f"try to accept job {runner.id} {res.text}")
    return res.json()["accepted"]


def send_job(job: CreateTestJobRequest, runner: RunnerHandle):
    res = requests.post(f"{runner.baseurl}/test/job", json=job.dict())
    logging.info(res)
    logging.info(res.text)
    return res.json()

class RunnerManager:
    def __init__(self, version_storage: VersionStorage, job_storage: TestJobStorage):
        self.runners: list[RunnerHandle] = []
        self._load_runner_infos()
        self.version_storage = version_storage
        self.job_storage = job_storage
        
    def get_all_runners(self):
        return self.runners

    def submit_job(self, job_req: CreateTestJobRequest):
        if job_req.id is None:
            job_req.id = str(uuid.uuid1())
        if job_req.os is None:
            # determine os by rdscore_version
            if job_req.rdscore_version is not None:
                version_info = self.version_storage.get_version_info(job_req.rdscore_version)
                if version_info is not None:
                    job_req.os = version_info.os
                else:
                    logging.error(f"Version {job_req.rdscore_version} not found in storage.")
                    return
            else:
                logging.error("Job OS is not specified and rdscore_version is not provided.")
                return
        if job_req.os not in ["windows", "linux"]:
            logging.error(f"Unsupported OS: {job_req.os}. Only 'windows' and 'linux' are supported.")
            return
        if job_req.rdscore_version is None:
            logging.error("Job rdscore_version is not specified.")
            return
        # check if job already exists
        existing_job = self.job_storage.get_test_job_by_id(job_req.id)
        if existing_job is not None:
            logging.warning(f"Job with ID {job_req.id} already exists. Updating job status to 'waiting'.")
            existing_job.status = "waiting"
            self.job_storage.update_test_job(existing_job)
            return
        # add job to jobs_to_dispatch
        job = TestJob(
            id=job_req.id,
            runner_id="",
            os=job_req.os,
            testcase_mark=job_req.testcase_mark,
            rdscore_version=job_req.rdscore_version,
            status="waiting",
            start_time=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        )
        self.job_storage.add_test_job(job)
        logging.info(f"Submitting job {job_req.id} for OS {job_req.os} with rdscore version {job_req.rdscore_version}.")
                
    def _load_runner_infos(self):
        # 从文件夹中扫描runner
        self.runners = []
        runner_infos_path = Path(CONFIG.runner_infos_path)
        if not runner_infos_path.exists():
            logging.info(f"Runner infos path {runner_infos_path} does not exist. Creating it.")
            runner_infos_path.mkdir(parents=True)
        for file in runner_infos_path.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    runner_info = RunnerHandle.model_validate_json(f.read())
                    self.runners.append(runner_info)
                    logging.info(f"Loaded runner info from {file}: {runner_info}")
            except Exception as e:
                logging.error(f"Failed to load runner info from {file}: {e}")
                continue
        if not self.runners:
            logging.info("No runner infos found. Starting with an empty list.")


    def add_runner(self, runner_info: RunnerHandle):
        # add to runners list
        if runner_info.id is None or runner_info.id == "":
            runner_info.id = str(uuid.uuid1())
        if runner_info.os is None:
            runner_info.os = "-"
        if runner_info.status is None:
            runner_info.status = "idle"
        self.runners.append(runner_info)
                # save runner info as json files in config.runner_infos_path
        if not os.path.exists(CONFIG.runner_infos_path):
            os.makedirs(CONFIG.runner_infos_path)
        file_path = Path(CONFIG.runner_infos_path) / f"{runner_info.id}.json"
        if file_path.exists():
            logging.warning(f"Runner with ID {runner_info.id} already exists. Updating existing runner.")
            with open(file_path, 'w') as f:
                f.write(runner_info.model_dump_json())
            return
        with open(file_path, 'w') as f:
            f.write(runner_info.model_dump_json())

    def remove_runner(self, runner_id: str):
        self.runners = [runner for runner in self.runners if runner.id != runner_id]
        logging.info(f"Removed runner with ID {runner_id} from the manager.")
        # remove runner info file
        file_path = Path(CONFIG.runner_infos_path) / f"{runner_id}.json"
        if file_path.exists():
            os.remove(file_path)
            logging.info(f"Removed runner info file {file_path}.")
        else:
            logging.warning(f"Runner info file {file_path} does not exist. Cannot remove.")

    def run(self):
        while True:
            time.sleep(1)
            self.refresh_runner_status()
            if self.process_jobs():
                break

    def process_jobs(self):
        jobs_waiting = self.job_storage.list_test_jobs_by_status("waiting")
        if not jobs_waiting:
            return False
        for job in jobs_waiting:
            if self.match_and_dispatch_job(job):
                # remove job from jobs_to_dispatch
                return True
        return False

    def match_and_dispatch_job(self, job: TestJob):
        logging.info(f"Trying to match job {job.id} with available runners.")
        for runner in self.runners[:]:
            logging.info(f"Checking runner {runner.id} with status {runner.status} for job {job.id}.")
            # match job and runner
            if runner.os != job.os:
                logging.info(f"Runner {runner.id} OS {runner.os} does not match job OS {job.os}.")
                continue
            if runner.status != "idle":
                logging.info(f"Runner {runner.id} is not idle, skipping.")
                continue
            if accept_job(job, runner):
                res_json = send_job(job, runner)
                logging.info(f"Job {job.id} submitted to runner {runner.id}. Response: {res_json}")
                job.runner_id = runner.id
                job.status = "running"
                self.job_storage.update_test_job(job)
                logging.info(f"Job {job.id} dispatched to runner {runner.id}.")
                # runner status is managed by the runner itself
                self.jobs_running.append(job)
                return True
            else:
                logging.info(f"Runner {runner.id} rejected job {job.id}.")
        return False
    
    def refresh_runner_status(self):
        """
        和runner通信，更新runner状态
        /info
        """
        for runner in self.runners:
            try:
                res = requests.get(f"{runner.baseurl}/info")
                if res.status_code == 200:
                    runner.status = "idle"
                else:
                    runner.status = "ping-failed"
                runner_os = res.json()["os"]
                if runner_os != runner.os:
                    logging.warning(f"Runner {runner.id} OS {runner.os} does not match reported OS {runner_os}. Updating runner info.")
                    runner.os = runner_os
                    # update runner info file
                    file_path = Path(CONFIG.runner_infos_path) / f"{runner.id}.json"
                    if file_path.exists():
                        with open(file_path, 'w') as f:
                            f.write(runner.model_dump_json())

            except requests.RequestException as e:
                logging.error(f"Failed to ping runner {runner.id}: {e}")
                runner.status = "error"        

    def get_jobs_to_dispatch(self) -> list[TestJob]:
        """
        获取待分发的任务
        """
        return self.job_storage.list_test_jobs_by_status("waiting")
    
    def get_running_jobs(self) -> list[TestJob]:
        """
        获取正在运行的任务
        """
        return self.job_storage.list_test_jobs_by_status("running")
    
    def get_active_jobs(self) -> list[TestJob]:
        """
        获取所有活跃的任务（待分发和正在运行的任务）
        """
        return self.get_jobs_to_dispatch() + self.get_running_jobs()