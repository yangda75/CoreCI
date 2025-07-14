from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class TestJobStatus(str, Enum):
    pending = "pending"
    running = "running"
    finished = "finished"
    failed = "failed"

# status: the status of the job (waiting, running, finished, failed)
class TestJob(BaseModel):
    id: str
    runner_id: str
    os: str
    testcase_mark: str
    rdscore_version: str
    status: str
    error: str | None = None
    report_url: str | None = None
    tested_cases: list[str] = []
    start_time: str


class RunnerTestJob(BaseModel):
    id: str | None = None
    start_time: str | None = str(datetime.now())
    testcase_mark: str = 'm0 and not imperfect'
    rdscore_version: str | None = ""
    current_case: str | None = None
    finished_cases: list[str] = []
    runner_status: TestJobStatus = TestJobStatus.pending
    error: str | None = None
    rdscore_file_path_abs : str | None = None # This is the absolute path to the rdscore file
    rdscore_file_url: str | None = None # This is the URL to download the rdscore file, not the local path
    report_url: str | None = None  # URL to access the report after the job is finished
    log_url: str | None = None  # URL to access the log file after the job is finished


class TestJobCtx(BaseModel):
    job: RunnerTestJob
    run_output_path: str  # Path where the test output will be stored
    rdscore_file_path_abs: str  # Absolute path to the rdscore file
    rdscore_file_url: str  # URL to download the rdscore file
    rdscore_version: str  # Version of the rdscore being used
    current_case: str | None = None  # Current test case being executed

class CreateTestJobResponse(BaseModel):
    created: bool = False
    job: RunnerTestJob | None = None

class AcceptTestJobResponse(BaseModel):
    accepted: bool = False
    error: str | None = None