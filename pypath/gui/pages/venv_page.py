import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QFileDialog, QInputDialog, QMessageBox, QTableWidgetItem,
                             QVBoxLayout)

from pypath.common.utils import norm
from pypath.gui.dialogs.venv import ask_venv_delete
from pypath.gui.pages.base import Page
from pypath.gui.panels.libs_panel import LibsPanel
from pypath.gui.panels.script_row import ScriptRow
from pypath.gui.tasks import run_async
from pypath.gui.widgets import BTN_H, SECTION_GAP, make_button, make_label, make_table, mark_ok, toolbar
from pypath.services import venv_store
from pypath.services import venvs as vn
from pypath.services.interpreters import get_all


def same(a, b):
    """Сравнивает два пути как одинаковые; None не равен ничему."""
    return a is not None and b is not None and norm(a) == norm(b)


class VenvPage(Page):
    """Список виртуальных окружений: создание, смена Python, выбор, запуск скриптов и их библиотеки."""

    def __init__(self, status):
        """Собирает страницу: таблицу venv, кнопки, панель библиотек и строку запуска скрипта."""
        super().__init__(status)
        self.venvs = venv_store.load_list()
        self.chosen = None

        self.venv_table = make_table(["Название", "Путь проекта", "Python", "Статус"], 1, True)
        self.venv_table.setWordWrap(False)
        self.venv_table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.venv_table.currentCellChanged.connect(lambda *_: self.update_select_button())

        self.create_btn = make_button("Создать", self.on_create)
        self.add_btn = make_button("Добавить", self.on_add)
        self.delete_btn = make_button("Удалить", self.on_delete)
        self.py_combo = QComboBox()
        self.py_combo.setMinimumHeight(BTN_H)
        self.change_btn = make_button("Изменить", self.on_change)
        self.select_btn = make_button("Выбрать", self.on_select)
        self.script_row = ScriptRow(self.say, lambda: self.chosen)

        self.libs = LibsPanel(status, "Выберите venv.",
                              locked=[self.venv_table, self.create_btn, self.add_btn, self.delete_btn,
                                      self.py_combo, self.change_btn, self.select_btn, self.script_row.run_btn])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(make_label("Управление виртуальным окружением", 15))
        layout.addWidget(self.venv_table, 1)
        layout.addLayout(toolbar([self.create_btn, self.add_btn, self.delete_btn],
                                 [self.py_combo, self.change_btn, self.select_btn]))
        layout.addSpacing(SECTION_GAP)
        layout.addLayout(self.libs.header("Библиотеки"))
        layout.addWidget(self.libs, 3)
        layout.addSpacing(SECTION_GAP)
        layout.addWidget(self.script_row)

        self.refresh_table()
        self.refresh_pythons()

    def refresh(self):
        """Перечитывает список Python, таблицу venv и библиотеки."""
        self.refresh_pythons()
        self.refresh_table()
        self.libs.reload()

    def on_shown(self):
        """Обновляет список Python и загружает библиотеки выбранного venv при открытии страницы."""
        self.refresh_pythons()
        self.ensure_libs()

    def restore_chosen(self, path):
        """Возвращает выбор venv с прошлого запуска; библиотеки загрузятся при открытии страницы."""
        saved = next((v for v in self.venvs if path and same(v, path)), None)
        if saved and os.path.isfile(vn.python_of(saved)):
            self.chosen = saved
            self.refresh_table(select=saved)

    def ensure_libs(self):
        """Загружает библиотеки выбранного venv, если они ещё не загружены."""
        if self.chosen and not self.libs.exe:
            self.libs.load(vn.python_of(self.chosen))

    def current_path(self):
        """Возвращает путь venv из выделенной строки таблицы или None."""
        row = self.venv_table.currentRow()
        return self.venvs[row] if 0 <= row < len(self.venvs) else None

    def refresh_pythons(self):
        """Заполняет список Python и сохраняет прежний выбор; по умолчанию выбран активный."""
        c = self.py_combo
        prev = c.currentData()
        c.clear()
        for i in get_all():
            c.addItem(f"Python {i['version']}", i["path"])
            c.setItemData(c.count() - 1, i["path"], Qt.ItemDataRole.ToolTipRole)
            if i["active"]:
                c.setCurrentIndex(c.count() - 1)
        idx = c.findData(prev) if prev else -1
        if idx >= 0:
            c.setCurrentIndex(idx)

    def update_select_button(self):
        """Меняет подпись кнопки на «Снять выбор» или «Выбрать» в зависимости от строки."""
        self.select_btn.setText("Снять выбор" if same(self.current_path(), self.chosen) else "Выбрать")

    def refresh_table(self, select=None):
        """Перерисовывает таблицу venv и выделяет строку select или прежнюю."""
        t = self.venv_table
        prev = select or self.current_path()
        t.blockSignals(True)
        t.setRowCount(len(self.venvs))
        for r, path in enumerate(self.venvs):
            chosen = same(path, self.chosen)
            texts = (os.path.basename(path), os.path.dirname(path), vn.version_of(path),
                     "Выбран" if chosen else "")
            for c, text in enumerate(texts):
                cell = QTableWidgetItem(text)
                cell.setToolTip(text)
                if chosen:
                    mark_ok(cell)
                t.setItem(r, c, cell)
        row = next((r for r, p in enumerate(self.venvs) if same(p, prev)), 0 if self.venvs else -1)
        t.setCurrentCell(row, 0 if row >= 0 else -1)
        t.blockSignals(False)
        self.update_select_button()

    def add_venv(self, path, text):
        """Добавляет venv в список, сохраняет список и выводит сообщение."""
        self.venvs.append(path)
        venv_store.save_list(self.venvs)
        self.refresh_table(select=path)
        self.libs.set_busy(False, text)

    def on_create(self):
        """Создаёт новый venv в выбранной папке на выбранном Python."""
        python = self.py_combo.currentData()
        if not python:
            self.say("Python не найден.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Папка проекта")
        if not folder:
            return
        name, ok = QInputDialog.getText(self, "Создание venv", "Название:", text=".venv")
        name = name.strip()
        if not ok or not name:
            return
        if os.path.basename(name) != name:
            self.say("Некорректное название.")
            return
        path = os.path.normpath(os.path.join(folder, name))
        if any(same(v, path) for v in self.venvs):
            self.say("Такой venv уже в списке.")
        elif vn.is_venv(path):
            self.add_venv(path, "Добавлен существующий venv.")
        elif os.path.exists(path):
            self.say("Папка уже существует и это не venv.")
        else:
            self.libs.set_busy(True, "Создание venv...")
            self.libs.spawn(vn.create, (python, path),
                            lambda _: self.add_venv(path, "venv создан."),
                            lambda msg: self.libs.set_busy(False, f"Ошибка: {msg}"),
                            lambda: self.libs.set_busy(False, "Создание venv отменено."))

    def on_add(self):
        """Добавляет в список существующий venv из выбранной папки."""
        folder = QFileDialog.getExistingDirectory(self, "Папка venv или проекта")
        if not folder:
            return
        path = next((p for p in (os.path.normpath(os.path.join(folder, sub))
                                 for sub in ("", ".venv", "venv")) if vn.is_venv(p)), None)
        if not path:
            self.say("В этой папке нет venv (нет файла pyvenv.cfg).")
        elif any(same(v, path) for v in self.venvs):
            self.say("Такой venv уже в списке.")
        else:
            self.add_venv(path, "venv добавлен.")

    def on_delete(self):
        """Удаляет выделенный venv с диска или только из списка."""
        path = self.current_path()
        if not path:
            self.say("Выберите venv в списке.")
            return
        mode = ask_venv_delete(self, path)
        if not mode:
            return

        def done(text):
            """Убирает venv из списка, сбрасывает выбор, если он был выбран, и сохраняет список."""
            if same(path, self.chosen):
                self.chosen = None
                self.libs.load(None)
            self.venvs = [v for v in self.venvs if not same(v, path)]
            venv_store.save_list(self.venvs)
            self.refresh_table()
            self.libs.set_busy(False, text)

        if mode == "list":
            done("venv убран из списка.")
            return
        self.libs.release_exe()
        self.libs.set_busy(True, "Удаление venv...")
        run_async(vn.remove, (path,), lambda _: done("venv удалён."),
                  lambda msg: self.libs.set_busy(False, f"Ошибка: {msg}"))

    def on_select(self):
        """Выбирает выделенный venv и загружает его библиотеки или снимает выбор."""
        path = self.current_path()
        if not path:
            self.say("Выберите venv в списке.")
            return
        if same(path, self.chosen):
            self.chosen = None
            self.libs.load(None)
            self.say("Выбор снят.")
        elif not os.path.isfile(vn.python_of(path)):
            self.say("venv повреждён: нет python.")
            return
        else:
            self.chosen = path
            self.libs.load(vn.python_of(path))
        self.refresh_table()

    def on_change(self):
        """Пересоздаёт выделенный venv на Python, выбранном в списке."""
        path = self.current_path()
        python = self.py_combo.currentData()
        if not path:
            self.say("Выберите venv в списке.")
            return
        if not python:
            self.say("Python не найден.")
            return
        if vn.uses_python(path, python):
            self.say("venv уже использует этот Python.")
            return
        if QMessageBox.question(self, "Изменение Python",
                                "Пересоздать venv на выбранном Python?\n"
                                "Библиотеки будут переустановлены. Если не получится, venv вернётся "
                                "в прежнее состояние, а список библиотек сохранится в файл.") \
                != QMessageBox.StandardButton.Yes:
            return

        def finish(text):
            """Обновляет таблицу и библиотеки после завершения смены Python."""
            self.refresh_table()
            if same(path, self.chosen):
                self.libs.load(vn.python_of(path), text + " ")
            else:
                self.libs.set_busy(False, text)

        def done(result):
            """Формирует итоговое сообщение о смене Python с числом непоставленных библиотек."""
            text = "Python изменён."
            if result.failed:
                text = f"Python изменён, но не удалось установить библиотек: {len(result.failed)}."
                if result.backup:
                    text += f" Прежний список: {result.backup}"
            finish(text)

        self.libs.release_exe()
        self.libs.set_busy(True, "Смена Python...")
        self.libs.spawn(vn.recreate, (python, path), done,
                        lambda msg: finish(f"Ошибка: {msg}."),
                        lambda: finish("Смена Python отменена, venv в прежнем состоянии."),
                        confirm="Прервать смену Python?\nvenv будет возвращён в прежнее состояние.")
