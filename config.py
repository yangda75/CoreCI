from pydantic import BaseModel


class CiConfig(BaseModel):
    builds_dir: str 
    testcase_folder: str
    output_path: str
    jobs_dir: str
    

CI_CONFIG = CiConfig(
    builds_dir="D:/test/builds",
    testcase_folder="C:/projects/AutoTest",
    output_path="D:/test/runs", 
    jobs_dir="D:/test/jobs"
)
