import os
import pathlib
import subprocess
import time

import requests


def win_kill_proc_by_port(port):
    cmd = 'for /f "tokens=5" %a in (\'netstat -ano ^| find "0.0.0.0:' + str(
        port) + '" ^| find "LISTENING"\') do taskkill /f /pid %a'
    print(cmd)
    os.system(cmd)


def linux_kill_proc_by_port(port):
    cmd = f'sudo kill -9 $(sudo lsof -i4TCP:{port} -sTCP:LISTEN -t)'
    print(cmd)
    os.system(cmd)


def kill_core(core_port=8088):
    if os.name == "nt":
        win_kill_proc_by_port(core_port)
    else:
        linux_kill_proc_by_port(core_port)


def win_start_core(path):
    os.chdir(path)
    print(os.getcwd())
    os.chdir("data/rdscore")

    print(os.getcwd())
    # TODO why cmd /c start rbk.exe 行?
    # TODO why start 不行？
    # TODO why rbk.exe 不行?
    p = subprocess.Popen(args=["cmd", "/c", "start", os.path.join(os.getcwd(), 'rbk.exe')], cwd=os.getcwd(),
                         creationflags=subprocess.DETACHED_PROCESS)
    print(p)
    time.sleep(2)
    wait_until_core_started()


def wait_until_core_started(timeout_sec=10) -> bool:
    for _ in range(timeout_sec):
        try:
            res = requests.get("http://localhost:8088/ping")
            if res:
                return True
            print(res)
        except Exception as e:
            print(e)
        time.sleep(1)
    return False


def linux_start_core(path):
    pass


def start_core(path):
    if os.name == "nt":
        win_start_core(path)
    else:
        linux_start_core(path)
