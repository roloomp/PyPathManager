"""Интерпретаторы Python, установленные в системе, и какой из них активен в PATH."""
import os

from pypath.common.utils import norm, num_key
from pypath.system import registry


def _entries(value):
    """Перебирает каталоги из значения Path: без кавычек, лишних пробелов и пустых элементов."""
    for part in value.split(";"):
        folder = os.path.expandvars(part.strip().strip('"').strip())
        if folder:
            yield folder


def _same(a, b):
    """Проверяет, что a и b указывают на один и тот же файл (регистр, короткие имена, ссылки)."""
    if norm(a) == norm(b):
        return True
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def get_active_from_registry():
    """Возвращает первый python.exe, который находится по PATH, или None."""
    paths = []
    for where in (registry.MACHINE, registry.USER):
        try:
            paths.append(registry.read_path(where)[0])
        except OSError:
            pass
    for folder in _entries(";".join(paths)):
        exe = os.path.join(folder, "python.exe")
        if os.path.isfile(exe):
            return exe
    return None


def get_from_registry():
    """Возвращает список установленных интерпретаторов из реестра без повторов."""
    found = {}
    for tag, exe in registry.python_installs():
        if os.path.isfile(exe):
            found[norm(exe)] = {"version": tag, "path": exe}
    return list(found.values())


def get_all():
    """Возвращает интерпретаторы с отметкой активного, новейшие версии первыми."""
    items = get_from_registry()
    active = get_active_from_registry()
    for item in items:
        item["active"] = bool(active) and _same(item["path"], active)
    return sorted(items, key=lambda x: num_key(x["version"]), reverse=True)
