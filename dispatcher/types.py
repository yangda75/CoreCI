
from pydantic import BaseModel

class CreateTestJobRequest(BaseModel):
    testcase_mark: str = 'm0'
    rdscore_file_url: str = ""
    rdscore_version: str = ""
    id: str | None = None
    os: str | None = None  # windows or linux


class CreateTestJobResponse(BaseModel):
    created: bool = False
    job_id: str | None = None
    runner_id: str | None = None
    error: str | None = None


class RDSCoreVersion(BaseModel):
    os: str  # windows or linux
    md5: str
    name: str  # windows-0.1.9.240909-0.1.9.zip
    date: str # iso8601 date, upload date
    version_prefix: str  # 0.1.9

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


class RdscoreVersionTestRecord(BaseModel):
    version: str
    test_records: list[TestJob]


class RunnerHandle(BaseModel):
    id: str | None = "DefaultRunnerId"
    os: str | None = "windows"
    status: str | None = "idle" # idle, running, error, ping-failed
    baseurl: str | None = "http://127.0.0.1:10898"
