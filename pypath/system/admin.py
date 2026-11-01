import ctypes
import os
import subprocess
import sys


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def restart_as_admin():
    """Запускает программу заново с запросом прав администратора (UAC).
    True, если запрос подтверждён; False, если пользователь отказался."""
    if getattr(sys, "frozen", False):
        args = sys.argv[1:]
    else:
        args = [os.path.abspath(sys.argv[0]), *sys.argv[1:]]
    folder = os.path.dirname(os.path.abspath(sys.argv[0]))
    shell_execute = ctypes.windll.shell32.ShellExecuteW
    shell_execute.restype = ctypes.c_void_p
    result = shell_execute(None, "runas", sys.executable, subprocess.list2cmdline(args), folder, 1)
    return (result or 0) > 32
