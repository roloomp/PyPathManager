"""Смена активного Python: правка переменной Path в реестре, с откатом."""
import logging
import os

from pypath.common.utils import norm
from pypath.services import path_history as history
from pypath.system import registry

log = logging.getLogger(__name__)


def dirs(exe):
    d = os.path.dirname(exe)
    return {norm(d), norm(os.path.join(d, "Scripts"))}


def _strip(value, known):
    return [p for p in value.split(";") if p and norm(os.path.expandvars(p)) not in known]


def _state():
    """Текущие значения Path: {"user": [значение, тип], "machine": [значение, тип]}."""
    return {"user": list(registry.read_path(registry.USER)),
            "machine": list(registry.read_path(registry.MACHINE))}


def set_active(exe, interpreters):
    """Делает exe активным. Перед записью сохраняется снимок PATH; если смена не удалась,
    изменения откатываются сами, а снимок убирается. Без прав администратора, если Python есть
    в системном PATH, будет PermissionError, и ничего не изменится."""
    known = set()
    for i in interpreters:
        known |= dirs(i["path"])

    before = _state()
    user_old, user_typ = before["user"]
    machine_old, machine_typ = before["machine"]
    # Системный PATH приоритетнее пользовательского: если в нём есть Python, его нужно убрать
    machine_parts = _strip(machine_old, known)
    machine_changed = len(machine_parts) != len([p for p in machine_old.split(";") if p])
    machine_new = ";".join(machine_parts) if machine_changed else machine_old
    d = os.path.dirname(exe)
    user_new = ";".join([d, os.path.join(d, "Scripts")] + _strip(user_old, known))

    snap = history.Snapshot.new(exe, before, machine_changed)
    history.save(snap)  # нет копии, нет и изменений
    machine_written = False
    try:
        if machine_changed:
            registry.write_path(registry.MACHINE, machine_new, machine_typ)
            machine_written = True
        try:
            registry.write_path(registry.USER, user_new, user_typ)
        except OSError:
            if machine_written:  # не оставляем полуприменённое состояние
                try:
                    registry.write_path(registry.MACHINE, machine_old, machine_typ)
                    machine_written = False
                except OSError as e:
                    log.error("не удалось вернуть системный PATH после сбоя: %s", e)
            raise
    except Exception:
        if not machine_written:  # состояние прежнее: снимок не нужен
            history.discard(snap)
        raise
    snap.after = {"user": [user_new, user_typ], "machine": [machine_new, machine_typ]}
    history.save(snap)
    registry.broadcast_env_change()


def last_change():
    """Последняя смена PATH, которую можно откатить (Snapshot) или None."""
    return history.latest()


def changed_since(snap):
    """True, если PATH после этой смены менял кто-то ещё (откат затрёт и эти изменения)."""
    return snap.after is None or _state() != snap.after


def undo(snap):
    """Возвращает PATH к состоянию до смены. Возвращает True, если системный PATH восстановить
    не удалось из-за нехватки прав: пользовательский уже восстановлен, снимок остаётся, и после
    перезапуска от администратора откат можно повторить."""
    current = _state()
    if current["user"] != snap.before["user"]:
        registry.write_path(registry.USER, *snap.before["user"])
    machine_pending = False
    if snap.machine_changed and current["machine"] != snap.before["machine"]:
        try:
            registry.write_path(registry.MACHINE, *snap.before["machine"])
        except PermissionError:
            machine_pending = True
    if not machine_pending:
        history.discard(snap)
    registry.broadcast_env_change()
    return machine_pending
