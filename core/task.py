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
