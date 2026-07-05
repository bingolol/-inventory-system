"""进程生命周期管理：防止孤儿进程"""

import atexit
import os
import signal
import subprocess
import sys

_child_processes: list[subprocess.Popen] = []


def track(proc: subprocess.Popen) -> subprocess.Popen:
    """注册一个子进程到清理列表，父进程退出时自动 kill"""
    _child_processes.append(proc)
    return proc


def _cleanup():
    for proc in _child_processes:
        if proc.poll() is None:
            try:
                if sys.platform == "win32":
                    proc.terminate()
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=5)
            except Exception:
                pass


atexit.register(_cleanup)


def popen_detached(args, **kwargs):
    """启动一个完全脱离父进程的子进程（永不成孤儿，始终独立）"""
    extra = {}
    if sys.platform == "win32":
        extra["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        extra["start_new_session"] = True
    return subprocess.Popen(args, **kwargs | extra)
