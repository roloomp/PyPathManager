"""Виртуальные окружения: создание, пересоздание, удаление, запуск скриптов."""
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field

from pypath.common.errors import Cancelled, CommandError
from pypath.common.utils import norm
from pypath.services.backups import save_requirements
from pypath.services.pip import freeze, install_from_file, install_single
from pypath.system.processes import open_console, run

log = logging.getLogger(__name__)

T_VENV = 300
NO_PROGRESS_LIMIT = 3


def python_of(path):
    """Возвращает путь к python.exe внутри venv."""
    return os.path.join(path, "Scripts", "python.exe")


def is_venv(path):
    """Проверяет, что в папке есть файл pyvenv.cfg."""
    return os.path.isfile(os.path.join(path, "pyvenv.cfg"))


def cfg_of(path):
    """Читает pyvenv.cfg в словарь; при ошибке возвращает пустой словарь."""
    result = {}
    try:
        with open(os.path.join(path, "pyvenv.cfg"), encoding="utf-8") as f:
            for line in f:
                key, sep, value = line.partition("=")
                if sep:
                    result[key.strip()] = value.strip()
    except OSError as e:
        log.warning("не удалось прочитать pyvenv.cfg в %s: %s", path, e)
    return result


def version_of(path):
    """Возвращает версию Python venv или «?»."""
    cfg = cfg_of(path)
    return cfg.get("version") or cfg.get("version_info") or "?"


def uses_python(path, python):
    """Проверяет, создан ли venv на данном интерпретаторе."""
    return norm(cfg_of(path).get("home", "")) == norm(os.path.dirname(python))


def create(python, path, token=None):
    """Создаёт venv. При ошибке или отмене убирает недосозданную папку, если её не было раньше."""
    existed = os.path.exists(path)
    try:
        run([python, "-m", "venv", path], T_VENV, token)
    except (Cancelled, CommandError):
        if not existed:
            shutil.rmtree(path, ignore_errors=True)
        raise


@dataclass
class RecreateResult:
    failed: list = field(default_factory=list)
    backup: str | None = None


def recreate(python, path, token=None):
    """Пересоздаёт venv на другом Python и возвращает прежние библиотеки.

    Прежняя папка не стирается, а переименовывается в <venv>.old. Если что-то пошло не так
    (не создался venv, не поставилась ни одна библиотека, отмена), новая папка удаляется,
    а прежняя возвращается на место. Список библиотек при этом сохраняется в файл."""
    try:
        frozen = freeze(python_of(path), token)
    except CommandError:
        frozen = ""
    requirements = [x.strip() for x in frozen.splitlines() if x.strip() and not x.startswith("#")]
    backup = save_requirements(path, frozen) if requirements else None

    parked = path.rstrip("\\/") + ".old"
    if os.path.exists(parked):
        raise CommandError(f"рядом уже есть {parked}: удалите или переименуйте её и повторите")
    if token:
        token.check()
    try:
        os.replace(path, parked)
    except OSError as e:
        raise CommandError(f"не удалось подготовить venv (закройте программы, которые его используют): {e}") from e

    try:
        run([python, "-m", "venv", path], T_VENV, token)
        failed = _reinstall(python_of(path), requirements, frozen, token)
    except Cancelled:
        _rollback(path, parked)
        raise
    except CommandError as e:
        _rollback(path, parked)
        raise CommandError(f"{e}. venv возвращён в прежнее состояние") from e
    except Exception:
        _rollback(path, parked)
        raise
    shutil.rmtree(parked, ignore_errors=True)
    return RecreateResult(failed, backup)


def _reinstall(exe, requirements, frozen, token):
    """Ставит библиотеки в новый venv. Возвращает те, что поставить не удалось.
    Если не встала ни одна, бросает CommandError (вызывающий откатит изменения)."""
    if not requirements:
        return []
    fd, tmp = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(frozen)
        install_from_file(exe, tmp, token)
        return []
    except CommandError:
        pass
    finally:
        os.remove(tmp)
    failed, installed, streak, last = [], 0, 0, ""
    for line in requirements:
        if token:
            token.check()
        try:
            install_single(exe, line, token)
            installed, streak = installed + 1, 0
        except CommandError as e:
            failed.append(line)
            streak, last = streak + 1, str(e)
            if installed == 0 and streak >= NO_PROGRESS_LIMIT:
                break
    if installed == 0:
        raise CommandError(f"не удалось установить библиотеки ({last})")
    return failed


def _rollback(path, parked):
    """Удаляет новую папку venv и возвращает прежнюю из .old."""
    shutil.rmtree(path, ignore_errors=True)
    try:
        os.replace(parked, path)
    except OSError as e:
        raise CommandError(f"не удалось вернуть прежний venv, его копия лежит в {parked}: {e}") from e


def remove(path):
    """Удаляет папку venv с диска, если это действительно venv."""
    if not os.path.exists(path):
        return
    if not is_venv(path):
        raise CommandError("это не папка venv, удаление отменено")
    shutil.rmtree(path)


def run_script(venv_path, script):
    """Запускает скрипт интерпретатором venv в новом окне консоли."""
    open_console(python_of(venv_path), script)
