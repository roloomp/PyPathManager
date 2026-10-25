import json
import os
import shutil
import subprocess
import tempfile

from core.libraries import run, freeze, install_from_file
from core.utils import norm

FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venvs.json")
SCRIPTS = "Scripts" if os.name == "nt" else "bin"
PYTHON = "python.exe" if os.name == "nt" else "python"


def python_of(path):
    return os.path.join(path, SCRIPTS, PYTHON)


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
    except OSError:
        pass
    return result


def version_of(path):
    cfg = cfg_of(path)
    return cfg.get("version") or cfg.get("version_info") or "?"


def uses_python(path, python):
    return norm(cfg_of(path).get("home", "")) == norm(os.path.dirname(python))


def create(python, path):
    run([python, "-m", "venv", path], 300)


def recreate(python, path):
    """Пересоздаёт venv на другом Python и пробует вернуть прежние библиотеки."""
    try:
        old = freeze(python_of(path))
    except RuntimeError:
        old = ""
    run([python, "-m", "venv", "--clear", path], 300)
    if not old.strip():
        return
    fd, tmp = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(old)
        install_from_file(python_of(path), tmp)
    except RuntimeError as e:
        raise RuntimeError(f"Python изменён, библиотеки не переустановлены: {e}")
    finally:
        os.remove(tmp)


def remove(path):
    if not os.path.exists(path):
        return
    if not is_venv(path):
        raise RuntimeError("это не папка venv, удаление отменено")
    shutil.rmtree(path)


def run_script(venv_path, script):
    python = python_of(venv_path)
    cwd = os.path.dirname(script)
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    if os.name == "nt":
        # cmd /k оставляет окно открытым после завершения скрипта
        subprocess.Popen(f'cmd /k ""{python}" "{script}""', cwd=cwd, creationflags=flags)
    else:
        subprocess.Popen([python, script], cwd=cwd)


def load_list():
    try:
        with open(FILE, encoding="utf-8") as f:
            paths = json.load(f)
    except (OSError, ValueError):
        return []
    return [p for p in paths if isinstance(p, str) and is_venv(p)]


def save_list(paths):
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(paths, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
