"""История изменений PATH: снимок до и после каждой смены активного Python.
Снимки лежат файлами JSON, новейший имеет самое большое имя. Откат берёт снимки с конца, как стек."""
import json
import logging
import os
import time
from dataclasses import asdict, dataclass

from pypath.config.paths import PATH_HISTORY_DIR

log = logging.getLogger(__name__)

MAX_SNAPSHOTS = 20


@dataclass
class Snapshot:
    id: str
    time: str                # когда сделана смена, для показа пользователю
    exe: str                 # какой интерпретатор делали активным
    before: dict             # {"user": [значение, тип], "machine": [значение, тип]} до смены
    machine_changed: bool    # трогали ли системный PATH (иначе при откате его не нужно писать)
    after: dict | None = None  # то, что записали; по нему видно, менял ли PATH кто-то ещё

    @classmethod
    def new(cls, exe, before, machine_changed):
        now = time.time()
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
        micros = int(now * 1_000_000) % 1_000_000
        snap_id = f"{stamp}-{micros:06d}"
        while os.path.exists(_file(snap_id)) and micros < 999_999:  # смены не должны затирать друг друга
            micros += 1
            snap_id = f"{stamp}-{micros:06d}"
        return cls(snap_id, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)), exe, before, machine_changed)


def _file(snap_id):
    return os.path.join(PATH_HISTORY_DIR, snap_id + ".json")


def save(snap):
    """Записывает снимок. Если не вышло, OSError: менять PATH без копии нельзя."""
    os.makedirs(PATH_HISTORY_DIR, exist_ok=True)
    with open(_file(snap.id), "w", encoding="utf-8") as f:
        json.dump(asdict(snap), f, ensure_ascii=False, indent=2)
    _prune()


def discard(snap):
    try:
        os.remove(_file(snap.id))
    except OSError as e:
        log.warning("не удалось удалить снимок PATH %s: %s", snap.id, e)


def latest():
    """Самый свежий читаемый снимок или None."""
    try:
        names = sorted((n for n in os.listdir(PATH_HISTORY_DIR) if n.endswith(".json")), reverse=True)
    except OSError:
        return None
    for name in names:
        try:
            with open(os.path.join(PATH_HISTORY_DIR, name), encoding="utf-8") as f:
                return Snapshot(**json.load(f))
        except (OSError, ValueError, TypeError) as e:
            log.warning("снимок PATH %s повреждён: %s", name, e)
    return None


def _prune():
    try:
        names = sorted(n for n in os.listdir(PATH_HISTORY_DIR) if n.endswith(".json"))
        for old in names[:-MAX_SNAPSHOTS]:
            os.remove(os.path.join(PATH_HISTORY_DIR, old))
    except OSError as e:
        log.warning("не удалось почистить историю PATH: %s", e)
