import sys

from PyQt6.QtWidgets import QApplication

from pypath.config import logs, paths
from pypath.gui.main_window import MainWindow


def run():
    paths.ensure()  # до создания окна: оно читает файлы настроек
    logs.setup()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
