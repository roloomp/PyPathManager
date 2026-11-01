import os

from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QWidget

from pypath.gui.widgets import BTN_H, make_button
from pypath.services import venvs


class ScriptRow(QWidget):
    """Строка «файл, Обзор, Запустить»: запускает скрипт в выбранном venv."""

    def __init__(self, say, get_venv):
        """say(text): вывод в строку статуса; get_venv(): путь выбранного venv или None."""
        super().__init__()
        self.say = say
        self.get_venv = get_venv
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Исполняемый файл")
        self.edit.setMinimumHeight(BTN_H)
        self.browse_btn = make_button("Обзор", self.browse)
        self.run_btn = make_button("Запустить", self.run)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self.edit, 1)
        row.addWidget(self.browse_btn)
        row.addWidget(self.run_btn)

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "Python (*.py *.pyw);;Все файлы (*)")
        if path:
            self.edit.setText(os.path.normpath(path))

    def run(self):
        venv = self.get_venv()
        if not venv:
            self.say("Выберите venv.")
            return
        script = self.edit.text().strip()
        if not os.path.isfile(script):
            self.say("Укажите существующий файл.")
            return
        try:
            venvs.run_script(venv, script)
        except OSError as e:
            self.say(f"Ошибка запуска: {e}")
            return
        self.say(f"Запущено: {os.path.basename(script)}")
