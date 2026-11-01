import logging
import threading

from PyQt6.QtCore import QObject, pyqtSignal

from pypath.common.errors import Cancelled, CommandError
from pypath.system.processes import CancelToken

log = logging.getLogger(__name__)


class Task(QObject):
    """Выполняет fn(*args) в фоновом потоке; ok/err/cancelled приходят в главный поток.
    Для cancellable-задач fn получает именованный аргумент token (CancelToken)."""
    ok = pyqtSignal(object)
    err = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, fn, args, cancellable=False):
        super().__init__()
        self.fn, self.args, self.cancellable = fn, args, cancellable
        self.token = CancelToken()
        self.confirm_cancel = False  # отмена может оставить окружение в промежуточном состоянии

    def cancel(self):
        self.token.cancel()

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            kwargs = {"token": self.token} if self.cancellable else {}
            result = self.fn(*self.args, **kwargs)
        except Cancelled:
            self.cancelled.emit()
        except CommandError as e:
            self.err.emit(str(e))
        except Exception as e:
            log.exception("сбой фоновой операции %s", getattr(self.fn, "__name__", self.fn))
            self.err.emit(str(e))
        else:
            self.ok.emit(result)


_running = set()


def run_async(fn, args, on_ok, on_err, on_cancel=None, cancellable=False):
    """Запускает fn в фоне и возвращает задачу (её можно отменить через task.cancel())."""
    task = Task(fn, args, cancellable)
    _running.add(task)

    def done(cb, *value):
        _running.discard(task)
        if cb:
            cb(*value)

    task.ok.connect(lambda v: done(on_ok, v))
    task.err.connect(lambda m: done(on_err, m))
    task.cancelled.connect(lambda: done(on_cancel))
    task.start()
    return task
