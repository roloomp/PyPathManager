"""Интерпретаторы Python, установленные в системе, и какой из них активен в PATH."""
import os

from pypath.common.utils import norm, num_key
from pypath.system import registry


def get_active_from_registry():
    paths = []
    for where in (registry.MACHINE, registry.USER):
        try:
            paths.append(registry.read_path(where)[0])
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
    for tag, exe in registry.python_installs():
        if os.path.isfile(exe):
            found[norm(exe)] = {"version": tag, "path": exe}
    return list(found.values())


def get_all():
    items = get_from_registry()
    active = get_active_from_registry()
    active = norm(active) if active else None
    for item in items:
        item["active"] = norm(item["path"]) == active
    return sorted(items, key=lambda x: num_key(x["version"]), reverse=True)
