from pydantic import BaseModel


class Config(BaseModel):
    rdscore_versions_path: str
    test_records_path: str
    runner_infos_path: str


CONFIG = Config(
    rdscore_versions_path="D:/test/dispatcher/rdscore_versions",
    test_records_path="D:/test/dispatcher/test_records",
    runner_infos_path="D:/test/dispatcher/runner_infos",
)
