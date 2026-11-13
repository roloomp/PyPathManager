# Copyright (C) 2026 roloomp
# SPDX-License-Identifier: GPL-3.0-only

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QVBoxLayout

from pypath.gui.pages.base import Page
from pypath.gui.panels.libs_panel import LibsPanel
from pypath.gui.widgets import SECTION_GAP, make_button, make_label, make_table, mark_ok, toolbar
from pypath.services.interpreters import get_active_from_registry, get_all
from pypath.services import path_env


class PathPage(Page):
    """Интерпретаторы Python из реестра: выбор активного (PATH) и просмотр его библиотек."""

    def __init__(self, status):
        """Собирает страницу: таблицу интерпретаторов, кнопки и панель библиотек."""
        super().__init__(status)
        self.items = []

        self.python_table = make_table(["Версия", "Путь", "Статус"], 1, True)
        self.python_table.setWordWrap(False)
        self.python_table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.python_table.currentCellChanged.connect(lambda row, *_: self.show_libs(row))
        self.hint = make_label("", 9)
        self.hint.setWordWrap(True)
        self.hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.hint.hide()
        self.refresh_btn = make_button("Перечитать", self.refresh)
        self.activate_btn = make_button("Сделать активным", self.on_confirm)
        self.undo_btn = make_button("Откатить PATH", self.on_undo)

        self.libs = LibsPanel(status, "Выберите интерпретатор в списке.",
                              locked=[self.python_table, self.refresh_btn, self.activate_btn])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(make_label("Версия Python", 15))
        layout.addWidget(self.python_table, 1)
        layout.addWidget(self.hint)
        layout.addLayout(toolbar([self.undo_btn], [self.refresh_btn, self.activate_btn]))
        layout.addSpacing(SECTION_GAP)
        layout.addLayout(self.libs.header("Библиотеки"))
        layout.addWidget(self.libs, 3)

    def show_libs(self, row):
        """Загружает библиотеки интерпретатора из выбранной строки таблицы."""
        exe = self.items[row]["path"] if 0 <= row < len(self.items) else None
        self.libs.load(exe)

    def refresh(self):
        """Заново ищет интерпретаторы, обновляет таблицу и сохраняет выбор строки."""
        self.update_undo_button()
        t = self.python_table
        prev = self.items[t.currentRow()]["path"] if 0 <= t.currentRow() < len(self.items) else None
        self.items = get_all()
        t.blockSignals(True)
        t.setRowCount(len(self.items))
        for r, i in enumerate(self.items):
            status = "Активный" if i["active"] else ""
            for c, text in enumerate((i["version"], i["path"], status)):
                cell = QTableWidgetItem(text)
                cell.setToolTip(text)
                if i["active"]:
                    mark_ok(cell)
                t.setItem(r, c, cell)
        t.blockSignals(False)
        self.show_hint()
        if not self.items:
            self.libs.load(None)
            self.say("Python не найден.")
            return
        row = next((r for r, i in enumerate(self.items) if i["path"] == prev), None)
        if row is None:
            row = next((r for r, i in enumerate(self.items) if i["active"]), 0)
        t.blockSignals(True)
        t.setCurrentCell(row, 0)
        t.blockSignals(False)
        self.show_libs(row)

    def show_hint(self):
        """Если ни одна строка не активна, показывает под таблицей первый python.exe из PATH."""
        found = None if any(i["active"] for i in self.items) else get_active_from_registry()
        self.hint.setText(f"Первый python.exe в PATH: {found}. Его нет в списке выше." if found else "")
        self.hint.setVisible(bool(found))

    def update_undo_button(self):
        """Включает кнопку отката, если есть снимок PATH, и обновляет её подсказку."""
        snap = path_env.last_change()
        self.undo_btn.setEnabled(snap is not None)
        self.undo_btn.setToolTip(f"Вернуть PATH, каким он был до смены от {snap.time}" if snap
                                 else "Пока нечего откатывать: PATH не менялся из этой программы")

    def on_confirm(self):
        """Делает выбранный интерпретатор активным, изменяя PATH."""
        row = self.python_table.currentRow()
        if row < 0:
            self.say("Выберите интерпретатор в списке.")
            return
        item = self.items[row]
        if item["active"]:
            self.say("Этот интерпретатор уже активен.")
            return
        try:
            path_env.set_active(item["path"], self.items)
        except PermissionError:
            QMessageBox.critical(self, "Ошибка", "Python есть в системном PATH. "
                                                 "Для его изменения перезапустите программу от имени администратора "
                                                 "(Файл → Перезапустить от администратора).")
            return
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось изменить PATH:\n{e}")
            return
        self.refresh()
        self.say("PATH изменён. Перезапустите терминал, чтобы увидеть изменение. Вернуть прежний: «Откатить PATH».")

    def on_undo(self):
        """Возвращает PATH к состоянию до последней смены после подтверждения."""
        snap = path_env.last_change()
        if not snap:
            self.say("Нечего откатывать.")
            self.update_undo_button()
            return
        text = f"Вернуть PATH к состоянию до смены от {snap.time}\n(тогда активным сделали {snap.exe})?"
        if path_env.changed_since(snap):
            text += ("\n\nПосле этой смены PATH менялся ещё чем-то (например, установщиком). "
                     "Те изменения тоже будут потеряны.")
        if QMessageBox.question(self, "Откат PATH", text) != QMessageBox.StandardButton.Yes:
            return
        try:
            pending = path_env.undo(snap)
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось восстановить PATH:\n{e}")
            return
        self.refresh()
        if pending:
            QMessageBox.warning(self, "Откат PATH",
                                "Пользовательский PATH восстановлен, а системный нет: нужны права администратора.\n"
                                "Перезапустите программу от администратора (Файл → Перезапустить от администратора) "
                                "и нажмите «Откатить PATH» ещё раз.")
            self.say("PATH восстановлен частично: системный PATH ждёт прав администратора.")
        else:
            self.say("PATH восстановлен. Перезапустите терминал, чтобы увидеть изменение.")
