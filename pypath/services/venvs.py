"""Виртуальные окружения: создание, пересоздание, удаление, запуск скриптов."""
import logging
import os
import shutil
import tempfile

from pypath.common.errors import Cancelled, CommandError
from pypath.common.utils import norm
from pypath.services.pip import freeze, install_from_file
from pypath.system.processes import open_console, run

log = logging.getLogger(__name__)

T_VENV = 300


def python_of(path):
    return os.path.join(path, "Scripts", "python.exe")


def is_venv(path):
    return os.path.isfile(os.path.join(path, "pyvenv.cfg"))


def cfg_of(path):
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
    cfg = cfg_of(path)
    return cfg.get("version") or cfg.get("version_info") or "?"


def uses_python(path, python):
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


def recreate(python, path):
    """Пересоздаёт venv на другом Python и пробует вернуть прежние библиотеки."""
    try:
        old = freeze(python_of(path))
    except RuntimeError:
        old = ""
    run([python, "-m", "venv", "--clear", path], T_VENV)
    if not old.strip():
        return
    fd, tmp = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(old)
        install_from_file(python_of(path), tmp)
    except RuntimeError as e:
        raise CommandError(f"Python изменён, библиотеки не переустановлены: {e}") from e
    finally:
        os.remove(tmp)


def remove(path):
    if not os.path.exists(path):
        return
    if not is_venv(path):
        raise CommandError("это не папка venv, удаление отменено")
    shutil.rmtree(path)


def run_script(venv_path, script):
    open_console(python_of(venv_path), script)
