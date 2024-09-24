"""
存储
1. 上传的rdscore版本
2. 对应的测试记录
"""

import hashlib
import logging
from pathlib import Path
from typing import List
from dispatcher.types import RDSCoreVersion, TestRecord
from dispatcher.config import CONFIG
import os

def is_file_rdscore_zip(path: Path) -> bool:
    if not path.is_file():
        return False
    if not path.name.endswith(".zip"):
        return False
    # linux and windows:
    # windows: windows-0.2.0.240909-0.2.0.zip
    # linux: linux-0.2.0.240909-0.2.0.zip
    if not path.name.startswith("windows") and not path.name.startswith("linux"):
        return False
    segments = path.name.split("-")
    if len(segments) != 3:
        return False
    version_full = segments[1]
    version_segments = version_full.split(".")
    if len(version_segments) != 4:
        return False
    # version segments should start with 0 1 9 or 0 2 0
    if version_segments[0:2] not in [["0", "1", "9"], ["0", "2", "0"]]:
        return False
    # TODO unzip and check
    return True

def parse_rdscore_version_from_filename(filename: str) -> RDSCoreVersion | None:
    segments = filename.split("-")
    if len(segments) != 3:
        return None
    version_prefix = segments[0]
    version = segments[1]
    os = segments[2]
    return RDSCoreVersion(version_prefix=version_prefix, version=version, os=os, md5="")

def parse_rdscore_version(path: Path) -> RDSCoreVersion | None:
    if not is_file_rdscore_zip(path):
        return None 
    # calculate md5 of the file
    md5 = hashlib.md5(path.read_bytes()).hexdigest()
    version = parse_rdscore_version_from_filename(path.name)
    if version is None:
        return None
    version.md5 = md5
    return version


class DispatcherStorage:
    def __init__(self):
        self.rdscore_versions: List[RDSCoreVersion] = []
        self.test_records: List[TestRecord] = []
        os.makedirs(CONFIG.rdscore_versions_path, exist_ok=True)
        self._load_rdscore_versions()

    def _load_rdscore_versions(self):
        # 从文件夹中扫描rdscore版本
        self.rdscore_versions = [
            parse_rdscore_version(path)
            for path in Path(CONFIG.rdscore_versions_path).iterdir()
            if is_file_rdscore_zip(path)
        ]

    def add_rdscore_version(self, version: str):
        self.rdscore_versions.append(version)

    def add_rdscore_zip(self, zip_file: bytes, filename:str, expected_md5: str):
        version = parse_rdscore_version_from_filename(filename)
        if version is None:
            return
        # 检查md5
        md5 = hashlib.md5(zip_file).hexdigest()
        logging.info(f"md5: {md5}, expected_md5: {expected_md5}")
        if md5 != expected_md5:
            logging.error(f"md5 not match, {md5} != {expected_md5}")
            return
        # 保存
        path = Path(CONFIG.rdscore_versions_path) / filename
        logging.info(f"save rdscore zip to {path}")
        path.write_bytes(zip_file)
        logging.info(f"save rdscore zip to {path} done")
        # 更新rdscore_versions
        self.rdscore_versions.append(version)
        logging.info(f"add rdscore version {version} done")

    def add_test_record(self, test_record: TestRecord):
        self.test_records.append(test_record)

    def get_test_records(self, rdscore_version: str) -> List[TestRecord]:
        return [
            record
            for record in self.test_records
            if record.rdscore_version == rdscore_version
        ]

    def list_versions(self) -> List[RDSCoreVersion]:
        return self.rdscore_versions
