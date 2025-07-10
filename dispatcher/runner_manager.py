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
        if self.runners == []:
            return [RunnerHandle()]
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
        # 从文件夹中扫描runner信息
        # create file if not exists
        os.makedirs(CONFIG.runner_infos_path, exist_ok=True)
        file_path = Path(CONFIG.runner_infos_path)/"runner_infos.db"
        if not file_path.exists():
            conn = sqlite3.connect(CONFIG.runner_infos_path+"/runner_infos.db")
            conn.execute("create table runner_infos (id text primary key, ip text, port integer, os text, status text)")
            conn.close()
            return
        conn = sqlite3.connect(CONFIG.runner_infos_path+"/runner_infos.db")

        # select * from runner_infos
        # id, ip, port, os, status
        conn.execute("create table if not exists runner_infos (id text primary key, ip text, port integer, os text, status text)")
        cursor = conn.cursor()
        cursor.execute("select * from runner_infos")
        for row in cursor.fetchall():
            runner_id, ip, port, runner_os, status = row
            self.runners.append(RunnerHandle(id=runner_id, ip=ip, port=port, os=runner_os, status=status))
        conn.close()

    def add_runner(self, runner_info: RunnerHandle):
        conn = sqlite3.connect(CONFIG.runner_infos_path+"/runner_infos.db")
        cursor = conn.cursor()
        cursor.execute("insert into runner_infos values (?, ?, ?, ?, ?)", (runner_info.id, runner_info.ip, runner_info.port, runner_info.os, runner_info.status))
        conn.commit()
        conn.close()
        self.runners.append(runner_info)

    def run(self):
        while True:
            time.sleep(1)
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
        for runner in self.runners[:]:
            # match job and runner
            if runner.os != job.os:
                continue
            if runner.status != "idle":
                continue
            # send version to runner
            zip_file_and_md5 = self.version_storage.fetch_file_and_md5_of_version(job.rdscore_version, job.os)
            if zip_file_and_md5 is None:
                job.error = f"Version {job.rdscore_version} not found for OS {job.os}."
                job.status = "failed"
                self.job_storage.update_test_job(job)
                logging.error(f"Failed to find version {job.rdscore_version} for OS {job.os}.")
                continue
            zip_file, md5 = zip_file_and_md5
            send_version(zip_file, md5, runner)
            if accept_job(job, runner):
                self.jobs_to_dispatch.remove(job)
                send_job(job, runner)
                self.jobs_running.append(job)
                return True
            else:
                self.jobs_to_dispatch.remove(job)
        return False
    
    def refresh_runner_status(self):
        """
        和runner通信，更新runner状态
        TODO: 心跳机制
        """
        pass

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