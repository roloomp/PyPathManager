"""Копии списков библиотек, которые делаются перед опасными операциями с venv."""
import logging
import os
import re
import time

from pypath.config.paths import BACKUP_DIR

log = logging.getLogger(__name__)

MAX_BACKUPS = 20


def save_requirements(venv_path, text):
    """Сохраняет freeze в BACKUP_DIR и возвращает путь к файлу (None, если записать не удалось).
    Файл можно установить кнопкой «Импорт» в любое окружение."""
    project = os.path.basename(os.path.dirname(venv_path))
    name = os.path.basename(venv_path).lstrip(".") or "venv"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    file = os.path.join(BACKUP_DIR, re.sub(r"[^\w.-]+", "_", f"{project}_{name}_{stamp}") + ".txt")
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        with open(file, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError as e:
        log.warning("не удалось сохранить список библиотек: %s", e)
        return None
    _prune()
    return file


def _prune():
    try:
        files = sorted((os.path.join(BACKUP_DIR, n) for n in os.listdir(BACKUP_DIR) if n.endswith(".txt")),
                       key=os.path.getmtime, reverse=True)
        for old in files[MAX_BACKUPS:]:
            os.remove(old)
    except OSError as e:
        log.warning("не удалось почистить старые копии: %s", e)
