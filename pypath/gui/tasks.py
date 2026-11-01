import logging
import threading

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from pypath.common.errors import Cancelled, CommandError
from pypath.gui.widgets import make_button
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
        self.confirm_text = None  # если задан, перед отменой спрашиваем пользователя этим текстом
        self._thread = None

    def cancel(self):
        self.token.cancel()

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def wait(self, timeout):
        """Ждёт завершения потока (например, перед выходом из программы)."""
        if self._thread:
            self._thread.join(timeout)

    def _emit(self, signal, *args):
        try:
            signal.emit(*args)
        except RuntimeError:
            pass  # программа закрывается: Qt уже удалил этот объект, слушать результат некому

    def _run(self):
        try:
            kwargs = {"token": self.token} if self.cancellable else {}
            result = self.fn(*self.args, **kwargs)
        except Cancelled:
            self._emit(self.cancelled)
        except CommandError as e:
            self._emit(self.err, str(e))
        except Exception as e:
            log.exception("сбой фоновой операции %s", getattr(self.fn, "__name__", self.fn))
            self._emit(self.err, str(e))
        else:
            self._emit(self.ok, result)


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


CONFIRM_ENV = "Прервать операцию?\nОкружение может остаться в промежуточном состоянии."


class TaskSlot:
    """Одна текущая отменяемая задача панели и её кнопка «Отмена» (видна, пока задача идёт)."""

    def __init__(self, parent, status):
        self.parent = parent  # для диалога подтверждения
        self.status = status  # QLabel, куда пишем «Отмена...»
        self.task = None
        self.button = make_button("Отмена", self.on_cancel)
        self.button.setShortcut("Esc")
        self.button.hide()

    def spawn(self, fn, args, on_ok, on_err, on_cancel, confirm=None):
        """Запускает задачу. confirm: текст вопроса перед отменой (если отмена небезопасна или долгая)."""
        def release(cb):
            def inner(*value):
                if self.task is task:
                    self.task = None
                    self.button.hide()
                cb(*value)
            return inner

        task = run_async(fn, args, release(on_ok), release(on_err), release(on_cancel), cancellable=True)
        task.confirm_text = confirm
        self.task = task
        self.button.show()

    def abort(self):
        """Прерывает текущую задачу без сообщений: её результат уже не нужен.
        Возвращает прерванную задачу (или None), чтобы можно было дождаться её завершения."""
        task = self.task
        if task:
            task.cancel()
            self.task = None
            self.button.hide()
        return task

    def risky(self):
        """Идёт задача, которую нежелательно обрывать без вопроса."""
        return self.task is not None and self.task.confirm_text is not None

    def on_cancel(self):
        task = self.task
        if not task:
            return
        if task.confirm_text and QMessageBox.question(
                self.parent, "Отмена", task.confirm_text) != QMessageBox.StandardButton.Yes:
            return
        if task is self.task:  # пока висел вопрос, задача могла завершиться сама
            self.status.setText("Отмена...")
            task.cancel()
