"""
存储
1. 上传的rdscore版本
2. 对应的测试记录
"""

import datetime
import hashlib
import logging
from pathlib import Path
from dispatcher.types import RDSCoreVersion, TestRecord
from dispatcher.config import CONFIG
import os

# possible filename formats:
# windows-0.2.0.240909-0.2.0.zip
# linux-0.2.0.240909-0.2.0.zip
# windows-0.2.0.250707.zip
# linux-0.2.0.250707.zip
# windows-0.2.0.250707-0620.zip
# windows-0.2.0.250708-fix-some-bug.zip
def parse_rdscore_version_from_filename(filename: str) -> RDSCoreVersion | None:
    """
    Parses the RDSCore version from the given filename.

    Args:
        filename (str): The filename to parse.

    Returns:
        Optional[RDSCoreVersion]: Parsed RDSCoreVersion object or None if parsing fails.
    """
    segments = filename.split("-")
    if len(segments) < 2:  # Ensure at least OS and version are present
        return None

    os = segments[0]
    version = segments[1]
    version_segments = version.split(".")
    if len(version_segments) < 3:  # Ensure major, minor, and patch are present
        return None

    version_prefix = ".".join(version_segments[:3])  # Combine major, minor, and patch
    name = filename.replace(".zip", "")  # Remove the .zip extension

    return RDSCoreVersion(
        version_prefix=version_prefix,
        date="",  # Date can be added later if needed
        os=os,
        md5="",  # MD5 can be calculated later
        name=name,
    )


def parse_rdscore_version(path: Path) -> RDSCoreVersion | None:
    logging.info(f"parse_rdscore_version: {path}")
    if not path.exists():
        logging.error(f"file {path} does not exist")
        return None
    # calculate md5 of the file
    md5 = hashlib.md5(path.read_bytes()).hexdigest()
    version = parse_rdscore_version_from_filename(path.name)
    logging.info(f"parse_rdscore_version_from_filename: {version}")
    if version is None:
        return None
    version.md5 = md5
    # version.date is iso8601 date, we can use the file modification time
    # as the date
    if not path.stat().st_mtime:
        logging.error(f"file {path} has no modification time")
        return None
    # convert to iso8601 date
    version.date = datetime.datetime.fromtimestamp(path.stat().st_mtime).isoformat()
    logging.info(f"parsed version: {version}")
    return version


class DispatcherStorage:
    def __init__(self):
        self.rdscore_versions: list[RDSCoreVersion] = []
        self.test_records: list[TestRecord] = []
        os.makedirs(CONFIG.rdscore_versions_path, exist_ok=True)
        self._load_rdscore_versions()

    def _load_rdscore_versions(self):
        self.rdscore_versions.clear()
        logging.info(f"load rdscore versions from {CONFIG.rdscore_versions_path}")
        if not Path(CONFIG.rdscore_versions_path).exists():
            logging.info(f"rdscore versions path {CONFIG.rdscore_versions_path} does not exist")
            return
        if not Path(CONFIG.rdscore_versions_path).is_dir():
            logging.error(f"rdscore versions path {CONFIG.rdscore_versions_path} is not a directory")
            return
        # 从文件夹中扫描rdscore版本
        for path in Path(CONFIG.rdscore_versions_path).iterdir():
            version = parse_rdscore_version(path)
            if version is not None:
                self.rdscore_versions.append(version)
            else:
                logging.warning(f"file {path} is not a valid rdscore zip file")

    def add_rdscore_version(self, version: str):
        self.rdscore_versions.append(version)

    def add_rdscore_zip(self, zip_file: bytes, filename: str, expected_md5: str):
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
        self._load_rdscore_versions()
        logging.info(f"add rdscore version {filename} done")

    def add_test_record(self, test_record: TestRecord):
        self.test_records.append(test_record)

    def get_test_records(self, rdscore_version: str) -> list[TestRecord]:
        return [
            record
            for record in self.test_records
            if record.rdscore_version == rdscore_version
        ]

    def list_versions(self) -> list[RDSCoreVersion]:
        logging.info(f"list_versions: {self.rdscore_versions}")
        return self.rdscore_versions

    def fetch_file_and_md5_of_version(self, version_str: str, os: str):
        # find version in rdscore_versions
        version = None
        for v in self.rdscore_versions:
            if v.full == version_str and v.os == os:
                version = v
                break
        if version is None:
            return None

        path = Path(CONFIG.rdscore_versions_path) / f"{version_str}.zip"
        if not path.exists():
            return None
        return path.read_bytes(), version.md5
    
    def get_version_info(self, version_str: str) -> RDSCoreVersion | None:
        for version in self.rdscore_versions:
            if version.name == version_str:
                return version
        return None