from pydantic import BaseModel
from datetime import datetime


class TestJob(BaseModel):
    id: str | None = None
    start_time: str | None = str(datetime.now())
    # testcase_folder: str | None = "C:/projects/AutoTest"
    # report_path: str | None = "D:/test_runs"
    testcase_mark: str = 'm0'
    rdscore_zip: bytes = bytes()
    build_name: str = "UNKNOWN"
    os: str = "Windows"
