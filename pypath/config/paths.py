"""Где программа хранит свои файлы. Рядом с кодом писать нельзя: после упаковки в exe
или установки в Program Files эта папка может быть недоступна для записи."""
import os
import shutil

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "PyPathManager")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.ini")
VENVS_FILE = os.path.join(APP_DIR, "venvs.json")
LOG_FILE = os.path.join(APP_DIR, "pypath.log")
BACKUP_DIR = os.path.join(APP_DIR, "backups")  # списки библиотек перед сменой Python у venv
PATH_HISTORY_DIR = os.path.join(APP_DIR, "path_history")  # снимки PATH перед каждым изменением


def ensure():
    """Создаёт папку данных и один раз переносит файлы старой версии из папки проекта."""
    os.makedirs(APP_DIR, exist_ok=True)
    for name in ("settings.ini", "venvs.json"):
        old = os.path.join(PROJECT_DIR, name)
        new = os.path.join(APP_DIR, name)
        if os.path.isfile(old) and not os.path.exists(new):
            try:
                shutil.copy2(old, new)
            except OSError:
                pass
