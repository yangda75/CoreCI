from importlib.metadata import files
import os
import json
from pathlib import Path
import zipfile
from test_runner.config import CI_CONFIG
from test_runner.test_job import TestJob, TestJobStatus


class TestRunnerStorage:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def has_version(self, version: str):
        return os.path.exists(self.get_version_abs_path(version))

    def get_version_abs_path(self, version: str):
        return os.path.join(self.base_dir, version)

    def list_rdscore_versions(self):
        return os.listdir(self.base_dir)
    
    def add_rdscore_version(self, zip_file:bytes, filename:str, expected_md5:str):
        version = filename
        if version is None:
            return
        # if version is present, return
        if self.has_version(version):
            return
        path = Path(self.base_dir) / filename
        path.write_bytes(zip_file)
        print(f"save rdscore zip to {path}")
        # unzip
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(self.base_dir)
        print(f"unzip rdscore zip to {path}")
        
    def save_job(self, job: TestJob):
        job_path = os.path.join(CI_CONFIG.jobs_dir, job.id)
        # make sure job folder exists
        if not os.path.exists(CI_CONFIG.jobs_dir):
            os.makedirs(CI_CONFIG.jobs_dir)

        # Convert TestJobStatus to a serializable format
        job_data = job.dict()
        job_data["status"] = job_data["status"].name  # Ensure status is a string

        with open(job_path, "w") as f:
            json.dump(job_data, f)

    def remove_job(self, job_id: str):
        job_path = os.path.join(CI_CONFIG.jobs_dir, job_id)
        if os.path.isfile(job_path):
            # try remove file
            try:
                os.remove(job_path)
            except Exception as e:
                print(f"Failed to remove job {job_id}: {e}")

    def list_unfinished_jobs(self):
        unfinished_jobs = []
        if not os.path.exists(CI_CONFIG.jobs_dir):
            return []
        files_to_remove = []
        for file in os.listdir(CI_CONFIG.jobs_dir):
            # try load file as json
            try:
                with open(os.path.join(CI_CONFIG.jobs_dir, file), "r") as f:
                    job_data = json.load(f)
                    status_str = job_data["status"]
                    if status_str in ["finished", "failed"]:
                        files_to_remove.append(job_data["id"])
                        continue

                    # Check if status is valid before creating TestJob
                    if status_str not in [status.name for status in TestJobStatus]:
                        print(f"Invalid status: {status_str}")
                        files_to_remove.append(job_data["id"])
                        continue  # Skip invalid statuses

                    job = TestJob(
                        id=job_data["id"],
                        start_time=job_data["start_time"],
                        testcase_folder=job_data["testcase_folder"],
                        testcase_mark=job_data["testcase_mark"],
                        rdscore_version=job_data["rdscore_version"],
                        current_case=job_data["current_case"],
                        finished_cases=job_data["finished_cases"],
                        status=TestJobStatus(status_str),
                        error=job_data["error"],
                        log_path=job_data["log_path"],
                        report_path=job_data["report_path"],
                    )
                    unfinished_jobs.append(job)
            except json.JSONDecodeError:
                continue
        for job_id in files_to_remove:
            self.remove_job(job_id)
        return unfinished_jobs
