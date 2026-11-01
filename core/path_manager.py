import ctypes
import os
import winreg
from core.utils import norm

MACHINE = (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
USER = (winreg.HKEY_CURRENT_USER, "Environment")


def dirs(exe):
    d = os.path.dirname(exe)
    return {norm(d), norm(os.path.join(d, "Scripts"))}


def _read(where):
    try:
        with winreg.OpenKey(where[0], where[1]) as key:
            return winreg.QueryValueEx(key, "Path")
    except FileNotFoundError:
        return "", winreg.REG_EXPAND_SZ


def _write(where, value, typ):
    with winreg.OpenKey(where[0], where[1], 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "Path", 0, typ, value)


def _strip(value, known):
    return [p for p in value.split(";") if p and norm(os.path.expandvars(p)) not in known]


def set_active(exe, interpreters):
    known = set()
    for i in interpreters:
        known |= dirs(i["path"])

    user_old, user_typ = _read(USER)
    machine_old, machine_typ = _read(MACHINE)
    machine_parts = _strip(machine_old, known)

    # Системный PATH приоритетнее пользовательского: если в нём есть Python, его нужно убрать.
    # Без прав администратора здесь будет PermissionError, пользовательский PATH остаётся нетронутым.
    if len(machine_parts) != len([p for p in machine_old.split(";") if p]):
        _write(MACHINE, ";".join(machine_parts), machine_typ)

    d = os.path.dirname(exe)
    new = [d, os.path.join(d, "Scripts")] + _strip(user_old, known)
    _write(USER, ";".join(new), user_typ)

    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, ctypes.byref(ctypes.c_ulong()))
