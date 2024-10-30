import logging
import time
import requests

import uuid

from dispatcher.types import CreateTestJobRequest, RunnerHandle



def accept_job(job: CreateTestJobRequest, runner: RunnerHandle):
    res = requests.post(f"http://{runner.ip}:{runner.port}/test/job/accept", json=job.dict())
    logging.info(res)
    logging.info(res.text)
    return res.text == "true"


def send_job(job: CreateTestJobRequest, runner: RunnerHandle):
    res = requests.post(f"http://{runner.ip}:{runner.port}/test/job", json=job.dict())
    logging.info(res)
    logging.info(res.text)
    return res.json()

class RunnerManager:
    def __init__(self):
        self.runners: list[RunnerHandle] = []
        self.jobs_to_dispatch: list[CreateTestJobRequest] = []

    def get_all_runners(self):
        if self.runners == []:
            return [RunnerHandle()]
        return self.runners

    def submit_job(self, job: CreateTestJobRequest):
        if job.id is None:
            job.id = str(uuid.uuid1())
        self.jobs_to_dispatch.append(job)

    def register(self, runner_handle: RunnerHandle):
        self.runners.append(runner_handle)

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
                return True
        return False

    def match_and_dispatch_job(self, job: CreateTestJobRequest):
        for runner in self.runners[:]:
            if accept_job(job, runner):
                self.jobs_to_dispatch.remove(job)
                self.runners.remove(runner)
                send_job(job, runner)
                return True
        return False
    def refresh_runner_status(self):
        """
        和runner通信，更新runner状态
        TODO: 心跳机制
        """
        pass