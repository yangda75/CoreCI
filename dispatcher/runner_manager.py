import logging
import time
import requests

from pydantic import BaseModel
import uuid

from test_job import TestJob


class RunnerHandle(BaseModel):
    id: str | None = "DefaultRunnerId"
    ip: str | None = "127.0.0.1"
    port: int | None = 10898


def accept_job(job: TestJob, runner: RunnerHandle):
    res = requests.post(f"http://{runner.ip}:{runner.port}/test/job/accept", json=job.dict())
    logging.info(res)
    logging.info(res.text)
    return res.text == "true"


def send_job(job: TestJob, runner: RunnerHandle):
    requests.post(f"http://{runner.ip}:{runner.port}/test/job", json=job.dict())


class RunnerManager:
    def __init__(self):
        self.runners: list[RunnerHandle] = []
        self.jobs_to_dispatch: list[TestJob] = []

    def get_all_runners(self):
        return self.runners

    def submit_job(self, job: TestJob):
        if job.id is None:
            job.id = str(uuid.uuid1())
        self.jobs_to_dispatch.append(job)

    def register(self, runner_handle: RunnerHandle):
        # TODO 去重
        self.runners.append(runner_handle)

    def run(self):
        while True:
            time.sleep(1)
            if not self.jobs_to_dispatch:
                continue
            while True:
                find_match = False
                for job in self.jobs_to_dispatch[:]:
                    for runner in self.runners[:]:
                        if accept_job(job, runner):
                            find_match = True
                            self.jobs_to_dispatch.remove(job)
                            self.runners.remove(runner)
                            send_job(job, runner)
                            break
                    if find_match:
                        break
                if not find_match:
                    break
