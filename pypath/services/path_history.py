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
    time: str
    exe: str
    before: dict
    machine_changed: bool
    after: dict | None = None

    @classmethod
    def new(cls, exe, before, machine_changed):
        """Создаёт снимок с уникальным идентификатором по текущему времени."""
        now = time.time()
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
        micros = int(now * 1_000_000) % 1_000_000
        snap_id = f"{stamp}-{micros:06d}"
        while os.path.exists(_file(snap_id)) and micros < 999_999:
            micros += 1
            snap_id = f"{stamp}-{micros:06d}"
        return cls(snap_id, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)), exe, before, machine_changed)


def _file(snap_id):
    """Возвращает путь к файлу снимка по его идентификатору."""
    return os.path.join(PATH_HISTORY_DIR, snap_id + ".json")


def save(snap):
    """Записывает снимок. Если не вышло, OSError: менять PATH без копии нельзя."""
    os.makedirs(PATH_HISTORY_DIR, exist_ok=True)
    with open(_file(snap.id), "w", encoding="utf-8") as f:
        json.dump(asdict(snap), f, ensure_ascii=False, indent=2)
    _prune()


def discard(snap):
    """Удаляет файл снимка."""
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
    """Удаляет самые старые снимки, оставляя не больше MAX_SNAPSHOTS."""
    try:
        names = sorted(n for n in os.listdir(PATH_HISTORY_DIR) if n.endswith(".json"))
        for old in names[:-MAX_SNAPSHOTS]:
            os.remove(os.path.join(PATH_HISTORY_DIR, old))
    except OSError as e:
        log.warning("не удалось почистить историю PATH: %s", e)
