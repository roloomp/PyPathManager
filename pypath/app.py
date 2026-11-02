import sys

from PyQt6.QtWidgets import QApplication

from pypath.config import logs, paths
from pypath.gui.main_window import MainWindow


def run():
    """Готовит папку данных и лог, создаёт окно и запускает цикл событий Qt."""
    paths.ensure()
    logs.setup()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
