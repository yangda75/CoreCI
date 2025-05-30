from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class CreateTestJobRequest(BaseModel):
    testcase_mark: str = 'm0'
    rdscore_version: str | None = ""
    

class TestJobStatus(str, Enum):
    pending = "pending"
    running = "running"
    finished = "finished"
    failed = "failed"

class TestJob(BaseModel):
    id: str | None = None
    start_time: str | None = str(datetime.now())
    testcase_folder: str | None 
    testcase_mark: str = 'm0 and not imperfect'
    rdscore_version: str | None = ""
    current_case: str | None = None
    finished_cases: list[str] = []
    status: TestJobStatus = TestJobStatus.pending
    error: str | None = None
    log_path: str | None = None
    report_path: str | None = None

class CreateTestJobResponse(BaseModel):
    created: bool = False
    job: TestJob | None = None

class AcceptTestJobResponse(BaseModel):
    accepted: bool = False
    error: str | None = None