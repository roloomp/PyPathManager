import ctypes
import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from pypath.config import logs, paths
from pypath.gui.main_window import MainWindow


def run():
    """Готовит папку данных и лог, создаёт окно и запускает цикл событий Qt."""
    paths.ensure()
    logs.setup()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("roloomp.PyPathManager")
    if os.path.isfile(paths.ICON_FILE):
        app.setWindowIcon(QIcon(paths.ICON_FILE))
    window = MainWindow()
    window.show()
    return app.exec()
