import threading
from PyQt6.QtCore import QObject, pyqtSignal


class Task(QObject):
    """Выполняет fn(*args) в фоновом потоке; ok/err приходят в главный поток."""
    ok = pyqtSignal(object)
    err = pyqtSignal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn, self.args = fn, args

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            result = self.fn(*self.args)
        except Exception as e:
            self.err.emit(str(e))
        else:
            self.ok.emit(result)


_running = set()


def run_async(fn, args, on_ok, on_err):
    task = Task(fn, *args)
    _running.add(task)

    def done(cb, value):
        _running.discard(task)
        cb(value)

    task.ok.connect(lambda v: done(on_ok, v))
    task.err.connect(lambda m: done(on_err, m))
    task.start()
