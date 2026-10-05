import os
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget
from gui.handlers import python_handlers as py

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_PATH = os.path.join(ROOT, "ui", "main_window.ui")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi(UI_PATH, self)
        self.setWindowTitle("PyPath Manager")
        self.manual = []
        self.items = []

        py.setup_table(self)
        self.py_update.clicked.connect(lambda: py.refresh(self))
        self.py_add.clicked.connect(lambda: py.on_add(self))
        self.fin_confirm.clicked.connect(lambda: py.on_confirm(self))

        for b in (self.py_delete, self.lib_download, self.lib_update,
                  self.lib_select_all, self.lib_delete, self.fin_export,
                  self.fin_import, self.fin_backup,
                  self.path_button, self.venv_button):
            b.clicked.connect(self.not_ready)

        py.refresh(self)

    def not_ready(self):
        self.status.setText("Пока не реализовано.")