from pydantic import BaseModel
import os 

class Config(BaseModel):
    rdscore_versions_path: str
    test_records_path: str
    runner_infos_path: str

if os.name == "nt":  # Windows
    CONFIG = Config(
        rdscore_versions_path="D:/test/dispatcher/rdscore_versions",
        test_records_path="D:/test/dispatcher/test_records",
        runner_infos_path="D:/test/dispatcher/runner_infos",
    )
else:
    CONFIG = Config(
        rdscore_versions_path="/tmp/coreci-dispatcher/rdscore_versions",
        test_records_path="/tmp/coreci-dispatcher/test_records",
        runner_infos_path="/tmp/coreci-dispatcher/runner_infos",
    )

