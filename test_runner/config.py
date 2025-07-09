import os
from pydantic import BaseModel


class CiConfig(BaseModel):
    builds_dir: str 
    testcase_folder: str
    output_path: str
    jobs_dir: str
    pytest_path: str
    pytest_html_merger: str


if os.name == "nt":  # Windows
    CI_CONFIG = CiConfig(
        builds_dir="D:/test/builds",
        testcase_folder="C:/projects/AutoTest",
        output_path="D:/test/runs", 
        jobs_dir="D:/test/jobs",
        pytest_path="C:/Users/yda/anaconda3/envs/py310/Scripts/pytest.exe",
        pytest_html_merger="C:/Users/yda/anaconda3/envs/py310/Scripts/pytest_html_merger.exe"
    )
else:  # Linux
    CI_CONFIG = CiConfig(
        builds_dir="/tmp/coreci-testrunner/builds",
        testcase_folder="/tmp/coreci-testrunner/testcases",
        output_path="/tmp/coreci-testrunner/runs", 
        jobs_dir="/tmp/coreci-testrunner/jobs",
        pytest_path="/usr/bin/pytest",
        pytest_html_merger="/usr/bin/pytest_html_merger"
    )
