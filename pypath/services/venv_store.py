"""Список venv, которые пользователь добавил в программу (venvs.json)."""
import json
import logging

from pypath.config.paths import VENVS_FILE
from pypath.services.venvs import is_venv

log = logging.getLogger(__name__)


def load_list():
    try:
        with open(VENVS_FILE, encoding="utf-8") as f:
            paths = json.load(f)
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as e:
        log.warning("не удалось прочитать список venv: %s", e)
        return []
    return [p for p in paths if isinstance(p, str) and is_venv(p)]


def save_list(paths):
    try:
        with open(VENVS_FILE, "w", encoding="utf-8") as f:
            json.dump(paths, f, ensure_ascii=False, indent=2)
    except OSError as e:
        log.error("не удалось сохранить список venv: %s", e)
