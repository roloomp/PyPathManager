from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit
from gui.handlers import venv_handlers as vh
from gui.libs_panel import LibsPanel
from gui.widgets import BTN_H, make_label, make_button, make_table, toolbar


class VenvPage(QWidget):
    def __init__(self, status):
        super().__init__()
        self.status = status
        self.venvs = []
        self.chosen = None

        self.venv_table = make_table(["Название", "Путь проекта", "Python", "Статус"], 1, True)
        self.venv_table.setWordWrap(False)
        self.venv_table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.venv_table.currentCellChanged.connect(lambda *_: vh.update_select_button(self))

        self.create_btn = make_button("Создать", lambda: vh.on_create(self))
        self.add_btn = make_button("Добавить", lambda: vh.on_add(self))
        self.delete_btn = make_button("Удалить", lambda: vh.on_delete(self))
        self.py_combo = QComboBox()
        self.py_combo.setMinimumHeight(BTN_H)
        self.change_btn = make_button("Изменить", lambda: vh.on_change(self))
        self.select_btn = make_button("Выбрать", lambda: vh.on_select(self))

        self.libs = LibsPanel(status, "Выберите venv.")

        self.script_edit = QLineEdit()
        self.script_edit.setPlaceholderText("Исполняемый файл")
        self.script_edit.setMinimumHeight(BTN_H)
        self.browse_btn = make_button("Обзор", lambda: vh.on_browse(self))
        self.run_btn = make_button("Запустить", lambda: vh.on_run(self))

        self.libs.locked = [self.venv_table, self.create_btn, self.add_btn, self.delete_btn, self.py_combo,
                            self.change_btn, self.select_btn, self.run_btn]

        run_row = QHBoxLayout()
        run_row.setSpacing(8)
        run_row.addWidget(self.script_edit, 1)
        run_row.addWidget(self.browse_btn)
        run_row.addWidget(self.run_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(make_label("Управление виртуальным окружением", 15))
        layout.addWidget(self.venv_table, 1)
        layout.addLayout(toolbar([self.create_btn, self.add_btn, self.delete_btn],
                                 [self.py_combo, self.change_btn, self.select_btn]))
        layout.addWidget(make_label("Библиотеки", 15))
        layout.addWidget(self.libs, 3)
        layout.addLayout(run_row)
