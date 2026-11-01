"""Запуск внешних процессов с таймаутом и отменой."""
import os
import subprocess
import threading

from pypath.common.errors import Cancelled, CommandError

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

# pip на русской Windows может писать не в UTF-8: принудительно просим UTF-8
_ENV_UTF8 = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def kill_tree(proc):
    """Завершает процесс вместе с дочерними: pip собирает пакеты отдельными процессами."""
    if proc.poll() is not None:
        return
    try:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=10, creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        pass
    if proc.poll() is None:
        proc.kill()


class CancelToken:
    """Связывает кнопку «Отмена» с запущенным процессом. cancel() можно звать из любого потока."""

    def __init__(self):
        self._lock = threading.Lock()
        self._proc = None
        self.cancelled = False

    def attach(self, proc):
        with self._lock:
            self._proc = proc
            kill_now = self.cancelled
        if kill_now:  # отмена пришла раньше, чем процесс запустился
            kill_tree(proc)

    def detach(self):
        with self._lock:
            self._proc = None

    def cancel(self):
        with self._lock:
            self.cancelled = True
            proc = self._proc
        if proc:
            kill_tree(proc)

    def check(self):
        """Точка отмены между шагами составной операции."""
        if self.cancelled:
            raise Cancelled()


def run(cmd, timeout, token=None):
    """Запускает команду и возвращает stdout. token позволяет прервать её (Cancelled)."""
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace", creationflags=NO_WINDOW,
                                env={**os.environ, **_ENV_UTF8})
    except OSError as e:
        raise CommandError(str(e)) from e
    if token:
        token.attach(proc)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        proc.communicate()
        raise CommandError(f"превышено время ожидания ({timeout} с)") from None
    finally:
        if token:
            token.detach()
    if proc.returncode != 0:
        if token and token.cancelled:
            raise Cancelled()
        lines = err.strip().splitlines()
        raise CommandError(lines[-1] if lines else "команда завершилась с ошибкой")
    return out


def open_console(python, script):
    """Запускает скрипт в новом окне консоли; cmd /k оставляет окно открытым после завершения."""
    subprocess.Popen(f'cmd /k ""{python}" "{script}""', cwd=os.path.dirname(script),
                     creationflags=NEW_CONSOLE)
