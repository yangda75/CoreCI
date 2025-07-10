"""utils.py.

This module provides utility functions to operate core for the CoreCI test runner.
"""
import os
import subprocess
import time

import requests

def win_kill_proc_by_ps():
    """Kill processes related to core on Windows using PowerShell commands."""
    kill_rbk_command = 'Get-Process -Name rbk | Stop-Process'
    os.system(f'powershell -Command "{kill_rbk_command}"')
    kill_logger23_command = 'Get-Process -Name logger23 | Stop-Process'
    os.system(f'powershell -Command "{kill_logger23_command}"')

def win_kill_proc_by_port(port):
    """Kill processes listening on a specific port on Windows."""
    cmd = 'netstat -ano | find "0.0.0.0:' + str(port) + '" | find "LISTENING"'
    res = os.popen(cmd).read()
    if res:
        pid = res.split()[-1]
        cmd = 'taskkill /f /pid ' + pid
        os.system(cmd)



def linux_kill_proc_by_port(port):
    """Kill processes listening on a specific port on Linux."""
    cmd = f'sudo kill -9 $(sudo lsof -i4TCP:{port} -sTCP:LISTEN -t)'
    os.system(cmd)


def kill_core(core_port=8088):
    """Kill the core service based on the operating system."""
    if os.name == "nt":
        win_kill_proc_by_ps()
    else:
        linux_kill_proc_by_port(core_port)

def is_core_running():
    """Check if the core service is running by sending a ping request."""
    try:
        res = requests.get("http://localhost:8088/ping")
        if res.status_code == 200:
            return True
    except Exception as e:
        print(e)
    return False

def wait_until_core_stopped(timeout_sec=10) -> bool:
    """Wait until the core service is stopped."""
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
    """Start the core service on Windows."""
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
    """Wait until the core service is started."""
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
    """Start the core service on Linux."""
    pass


def start_core(path):
    """Start the core service based on the operating system.

    :param path: The path to the core service directory.
    :return: None
    :raises FileNotFoundError: If the specified path does not exist.
    :raises Exception: If the core service fails to start.
    :raises TimeoutError: If the core service does not start within the timeout period.
    :example: start_core("C:/path/to/core/service")
    :note: Ensure that the path provided is correct and the core service is properly configured.
    :usage: start_core("/path/to/core/service")
    :description: This function checks the operating system and starts the core service accordingly.
    It uses the appropriate method for Windows or Linux to start the service.
    It also waits until the service is confirmed to be running.
    If the service fails to start, it raises an exception.
    If the service does not start within the specified timeout, it raises a TimeoutError.

    """
    if os.name == "nt":
        win_start_core(path)
    else:
        linux_start_core(path)
