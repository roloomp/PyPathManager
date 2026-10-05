import os
import winreg

from core.utils import norm


def get_active_from_registry():
    paths = []
    for hive, sub in (
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        (winreg.HKEY_CURRENT_USER, "Environment"),
    ):
        try:
            with winreg.OpenKey(hive, sub) as k:
                paths.append(winreg.QueryValueEx(k, "Path")[0])
        except OSError:
            pass
    for p in ";".join(paths).split(";"):
        if not p:
            continue
        exe = os.path.join(os.path.expandvars(p), "python.exe")
        if os.path.isfile(exe):
            return exe
    return None


def get_from_registry():
    found = {}
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                root = winreg.OpenKey(hive, r"Software\Python", 0, winreg.KEY_READ | view)
            except OSError:
                continue
            with root:
                i = 0
                while True:
                    try:
                        company = winreg.EnumKey(root, i)
                    except OSError:
                        break
                    i += 1
                    try:
                        with winreg.OpenKey(root, company) as ck:
                            j = 0
                            while True:
                                try:
                                    tag = winreg.EnumKey(ck, j)
                                except OSError:
                                    break
                                j += 1
                                try:
                                    with winreg.OpenKey(ck, tag + r"\InstallPath") as ik:
                                        exe, _ = winreg.QueryValueEx(ik, "ExecutablePath")
                                        if os.path.isfile(exe):
                                            found[norm(exe)] = {"version": tag, "path": exe}
                                except OSError:
                                    pass
                    except OSError:
                        pass
    return list(found.values())


def get_all():
    items = get_from_registry()
    active = get_active_from_registry()
    active = norm(active) if active else None
    for item in items:
        item["active"] = norm(item["path"]) == active
    return sorted(items, key=lambda x: x["version"], reverse=True)