"""Реестр Windows: переменная Path и список установленных Python (PEP 514)."""
import ctypes
import winreg

MACHINE = (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
USER = (winreg.HKEY_CURRENT_USER, "Environment")

_HWND_BROADCAST = 0xFFFF
_WM_SETTINGCHANGE = 0x001A
_SMTO_ABORTIFHUNG = 0x0002


def read_path(where):
    """(значение, тип) переменной Path; если её нет - пустая строка."""
    try:
        with winreg.OpenKey(where[0], where[1]) as key:
            return winreg.QueryValueEx(key, "Path")
    except FileNotFoundError:
        return "", winreg.REG_EXPAND_SZ


def write_path(where, value, typ):
    with winreg.OpenKey(where[0], where[1], 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "Path", 0, typ, value)


def broadcast_env_change():
    """Сообщает запущенным программам, что переменные окружения изменились."""
    ctypes.windll.user32.SendMessageTimeoutW(
        _HWND_BROADCAST, _WM_SETTINGCHANGE, 0, "Environment", _SMTO_ABORTIFHUNG, 5000,
        ctypes.byref(ctypes.c_ulong()))


def _subkeys(key):
    i = 0
    while True:
        try:
            yield winreg.EnumKey(key, i)
        except OSError:
            return
        i += 1


def _install_exe(company_key, tag):
    try:
        with winreg.OpenKey(company_key, tag + r"\InstallPath") as key:
            return winreg.QueryValueEx(key, "ExecutablePath")[0]
    except OSError:
        return None


def python_installs():
    """Пары (тег версии, путь к python.exe) из Software\\Python\\<компания>\\<тег>\\InstallPath.
    Один интерпретатор может встретиться несколько раз (разные ветки и разрядность реестра)."""
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                root = winreg.OpenKey(hive, r"Software\Python", 0, winreg.KEY_READ | view)
            except OSError:
                continue
            with root:
                for company in _subkeys(root):
                    try:
                        with winreg.OpenKey(root, company) as company_key:
                            for tag in _subkeys(company_key):
                                exe = _install_exe(company_key, tag)
                                if exe:
                                    yield tag, exe
                    except OSError:
                        pass
