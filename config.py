from pydantic import BaseModel


class CiConfig(BaseModel):
    builds_dir: str = "D:/test/builds"
    testcase_folder: str = "C:/projects/AutoTest"
    output_path: str = "D:/test/runs"
    # todo pytest path?