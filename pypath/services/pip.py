"""Операции с библиотеками через `python -m pip`. Все функции принимают token для отмены."""
import json

from pypath.common.utils import canon
from pypath.system.processes import run

PROTECTED = {"pip", "setuptools", "wheel"}  # без них интерпретатор перестаёт ставить пакеты

T_QUICK = 60       # список, показ информации, версии
T_OUTDATED = 120   # проверка обновлений ходит в сеть
T_UNINSTALL = 300
T_INSTALL = 600


def _pip(exe, args, timeout, token):
    return run([exe, "-m", "pip", *args, "--disable-pip-version-check"], timeout, token)


def get_libs(exe, token=None):
    out = _pip(exe, ["list", "--format=json"], T_QUICK, token)
    return sorted(json.loads(out), key=lambda x: x["name"].lower())


def update_libs(exe, names, token=None):
    _pip(exe, ["install", "--upgrade", *names], T_INSTALL, token)


def delete_libs(exe, names, token=None):
    _pip(exe, ["uninstall", "-y", *names], T_UNINSTALL, token)


def install_libs(exe, names, token=None):
    _pip(exe, ["install", *names], T_INSTALL, token)


def get_outdated(exe, token=None):
    out = _pip(exe, ["list", "--outdated", "--format=json"], T_OUTDATED, token)
    return {canon(x["name"]): x["latest_version"] for x in json.loads(out)}


def install_from_file(exe, path, token=None):
    _pip(exe, ["install", "-r", path], T_INSTALL, token)


def install_single(exe, requirement, token=None):
    """Ставит одну строку из pip freeze без разрешения зависимостей (они уже есть в том же списке).
    Короткие таймаут и число повторов, чтобы при недоступной сети не ждать на каждом пакете."""
    spec = ["-e", requirement[3:].strip()] if requirement.startswith("-e ") else [requirement]
    _pip(exe, ["install", "--no-deps", "--retries", "1", "--timeout", "15", *spec], T_INSTALL, token)


def freeze(exe, token=None):
    return _pip(exe, ["freeze"], T_QUICK, token)


def get_versions(exe, name, token=None):
    out = _pip(exe, ["index", "versions", name], T_QUICK, token)
    for line in out.splitlines():
        if line.startswith("Available versions:"):
            return [v.strip() for v in line.partition(":")[2].split(",") if v.strip()]
    return []


def get_required_by(exe, names, token=None):
    """{имя: [пакеты, которым он нужен]} по данным pip show."""
    out = _pip(exe, ["show", *names], T_QUICK, token)
    result, name = {}, None
    for line in out.splitlines():
        if line.startswith("Name:"):
            name = line.partition(":")[2].strip()
        elif line.startswith("Required-by:") and name:
            result[name] = [x.strip() for x in line.partition(":")[2].split(",") if x.strip()]
    return result
