import os
import pathlib
import subprocess
import time

import requests

def win_kill_proc_by_ps():
    kill_rbk_command = 'Get-Process -Name rbk | Stop-Process'
    os.system(f'powershell -Command "{kill_rbk_command}"')
    kill_logger23_command = 'Get-Process -Name logger23 | Stop-Process'
    os.system(f'powershell -Command "{kill_logger23_command}"')

def win_kill_proc_by_port(port):
    cmd = 'netstat -ano | find "0.0.0.0:' + str(port) + '" | find "LISTENING"'
    res = os.popen(cmd).read()
    if res:
        pid = res.split()[-1]
        cmd = 'taskkill /f /pid ' + pid
        os.system(cmd)



def linux_kill_proc_by_port(port):
    cmd = f'sudo kill -9 $(sudo lsof -i4TCP:{port} -sTCP:LISTEN -t)'
    os.system(cmd)


def kill_core(core_port=8088):
    if os.name == "nt":
        win_kill_proc_by_ps()
    else:
        linux_kill_proc_by_port(core_port)

def is_core_running():
    try:
        res = requests.get("http://localhost:8088/ping")
        if res.status_code == 200:
            return True
    except Exception as e:
        print(e)
    return False

def wait_until_core_stopped(timeout_sec=10) -> bool:
    not_running_count = 0
    for _ in range(timeout_sec):
        try:
            if not is_core_running():
                not_running_count += 1
            else:
                not_running_count = 0
            if not_running_count >= 3:
                return True
        except Exception as e:
            print(e)
        time.sleep(1)
    return False

def win_start_core(path):
    # check if path exists
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path {path} does not exist")
    os.chdir(path)
    print(os.getcwd())
    os.chdir("data/rdscore")

    print(os.getcwd())
    # why cmd /c start rbk.exe 行?
    # why start 不行？
    # why rbk.exe 不行?
    p = subprocess.Popen(args=["cmd", "/c", "start", os.path.join(os.getcwd(), 'rbk.exe')], cwd=os.getcwd(),
                         creationflags=subprocess.DETACHED_PROCESS)
    print(p)
    time.sleep(2)
    wait_until_core_started()


def wait_until_core_started(timeout_sec=10) -> bool:
    running_count = 0
    for _ in range(timeout_sec):
        try:
            if is_core_running():
                running_count += 1
            else:
                running_count = 0
            if running_count >= 3:
                return True
        except Exception as e:
            print(e)
        time.sleep(1)
    return False


def linux_start_core(path):
    # TODO implement this
    pass


def start_core(path):
    if os.name == "nt":
        win_start_core(path)
    else:
        linux_start_core(path)
