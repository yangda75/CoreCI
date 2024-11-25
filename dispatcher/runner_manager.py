import logging
from pathlib import Path
import sqlite3
import time
from typing import List
import requests

import uuid
import os

from dispatcher.config import CONFIG
from dispatcher.types import CreateTestJobRequest, RunnerHandle

def send_version(zip_file: bytes, expected_md5: str, runner: RunnerHandle):
    res = requests.post(f"http://{runner.ip}:{runner.port}/test/storage/versions/upload/{expected_md5}", files={"file": zip_file})
    logging.info(f"try to send version {runner.id} {res.text}")

def accept_job(job: CreateTestJobRequest, runner: RunnerHandle):
    res = requests.post(f"http://{runner.ip}:{runner.port}/test/job/accept", json=job.dict())
    logging.info(f"try to accept job {runner.id} {res.text}")
    return res.text == "true"


def send_job(job: CreateTestJobRequest, runner: RunnerHandle):
    res = requests.post(f"http://{runner.ip}:{runner.port}/test/job", json=job.dict())
    logging.info(res)
    logging.info(res.text)
    return res.json()

class RunnerManager:
    def __init__(self, storage):
        self.runners: list[RunnerHandle] = []
        self.jobs_to_dispatch: list[CreateTestJobRequest] = []
        self.jobs_running: list[CreateTestJobRequest] = []
        self._load_runner_infos()
        self.storage = storage

    def get_all_runners(self):
        if self.runners == []:
            return [RunnerHandle()]
        return self.runners

    def submit_job(self, job: CreateTestJobRequest):
        if job.id is None:
            job.id = str(uuid.uuid1())
        self.jobs_to_dispatch.append(job)
        
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
        if not self.jobs_to_dispatch:
            return False
        for job in self.jobs_to_dispatch[:]:
            if self.match_and_dispatch_job(job):
                # remove job from jobs_to_dispatch
                self.jobs_to_dispatch.remove(job)
                self.jobs_running.append(job)
                return True
        return False

    def match_and_dispatch_job(self, job: CreateTestJobRequest):
        for runner in self.runners[:]:
            # match job and runner
            if runner.os != job.os:
                continue
            if runner.status != "idle":
                continue
            # send version to runner
            zip_file_and_md5 = self.storage.fetch_file_and_md5_of_version(job.rdscore_version, job.os)
            if zip_file_and_md5 is None:
                self.jobs_to_dispatch.remove(job)
                continue
            zip_file, md5 = zip_file_and_md5
            send_version(zip_file, md5, runner)
            if accept_job(job, runner):
                self.jobs_to_dispatch.remove(job)
                send_job(job, runner)
                return True
        return False
    
    def refresh_runner_status(self):
        """
        和runner通信，更新runner状态
        TODO: 心跳机制
        """
        pass