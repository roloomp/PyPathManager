# Copyright (C) 2026 roloomp
# SPDX-License-Identifier: GPL-3.0-only

import ctypes
import os
import subprocess
import sys


def is_admin():
    """Проверяет, запущена ли программа с правами администратора."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def restart_as_admin():
    """Запускает программу заново с запросом прав администратора (UAC).
    True, если запрос подтверждён; False, если пользователь отказался."""
    exe = sys.executable
    if getattr(sys, "frozen", False):
        args = sys.argv[1:]
    else:
        args = [os.path.abspath(sys.argv[0]), *sys.argv[1:]]
        gui_exe = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.isfile(gui_exe):
            exe = gui_exe
    folder = os.path.dirname(os.path.abspath(sys.argv[0]))
    shell_execute = ctypes.windll.shell32.ShellExecuteW
    shell_execute.restype = ctypes.c_void_p
    result = shell_execute(None, "runas", exe, subprocess.list2cmdline(args), folder, 1)
    return (result or 0) > 32
