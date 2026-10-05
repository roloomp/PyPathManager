import ctypes
import os
import winreg
from core.interpreters import get_all
from core.utils import norm


def dirs(exe):
    d = os.path.dirname(exe)
    return {norm(d), norm(os.path.join(d, "Scripts"))}


def set_active(exe, interpreters):
    """Ставит exe первым в пользовательском PATH. Возвращает старое значение PATH."""
    known = set()
    for i in interpreters:
        known |= dirs(i["path"])

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        try:
            old, typ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            old, typ = "", winreg.REG_EXPAND_SZ

        BACKUP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "../path_backup.txt")

        with open(BACKUP, "w", encoding="utf-8") as f:
            f.write(old)

        # убираем папки всех известных Python, остальное не трогаем
        parts = [p for p in old.split(";") if p and norm(os.path.expandvars(p)) not in known]

        d = os.path.dirname(exe)
        new = [d, os.path.join(d, "Scripts")] + parts
        winreg.SetValueEx(key, "Path", 0, typ, ";".join(new))

    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, ctypes.byref(ctypes.c_ulong()))
    return old

items = get_all()
target = next(i for i in items if i["version"] == "3.14")
set_active(target["path"], items)