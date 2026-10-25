from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from gui.handlers import python_handlers as py
from gui.libs_panel import LibsPanel
from gui.widgets import make_label, make_button, make_table, toolbar


class PathPage(QWidget):
    def __init__(self, status):
        super().__init__()
        self.status = status
        self.items = []

        self.python_table = make_table(["Версия", "Путь", "Статус"], 1, True)
        self.python_table.setWordWrap(False)
        self.python_table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.python_table.currentCellChanged.connect(lambda row, *_: py.show_libs(self, row))
        self.py_update = make_button("Перечитать", lambda: py.refresh(self))
        self.fin_confirm = make_button("Сделать активным", lambda: py.on_confirm(self))

        self.libs = LibsPanel(status, "Выберите интерпретатор в списке.", )
        self.libs.locked = [self.python_table, self.py_update, self.fin_confirm]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(make_label("Версия Python", 15))
        layout.addWidget(self.python_table, 1)
        layout.addLayout(toolbar([], [self.py_update, self.fin_confirm]))
        layout.addWidget(make_label("Библиотеки", 15))
        layout.addWidget(self.libs, 3)
