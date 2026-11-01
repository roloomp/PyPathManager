"""Смена активного Python: правка переменной Path в реестре."""
import os

from pypath.common.utils import norm
from pypath.system import registry


def dirs(exe):
    d = os.path.dirname(exe)
    return {norm(d), norm(os.path.join(d, "Scripts"))}


def _strip(value, known):
    return [p for p in value.split(";") if p and norm(os.path.expandvars(p)) not in known]


def set_active(exe, interpreters):
    known = set()
    for i in interpreters:
        known |= dirs(i["path"])

    user_old, user_typ = registry.read_path(registry.USER)
    machine_old, machine_typ = registry.read_path(registry.MACHINE)
    machine_parts = _strip(machine_old, known)

    # Системный PATH приоритетнее пользовательского: если в нём есть Python, его нужно убрать.
    # Без прав администратора здесь будет PermissionError, пользовательский PATH остаётся нетронутым.
    if len(machine_parts) != len([p for p in machine_old.split(";") if p]):
        registry.write_path(registry.MACHINE, ";".join(machine_parts), machine_typ)

    d = os.path.dirname(exe)
    new = [d, os.path.join(d, "Scripts")] + _strip(user_old, known)
    registry.write_path(registry.USER, ";".join(new), user_typ)
    registry.broadcast_env_change()
