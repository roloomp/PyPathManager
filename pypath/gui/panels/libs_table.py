# Copyright (C) 2026 roloomp
# SPDX-License-Identifier: GPL-3.0-only

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

from pypath.common.utils import canon, num_key
from pypath.gui.widgets import mark_warn, setup_table


class Item(QTableWidgetItem):
    """Ячейка с собственным ключом сортировки (версии сравниваются как числа)."""

    def __init__(self, text, key=None):
        """Создаёт ячейку; ключ сортировки по умолчанию - текст в нижнем регистре."""
        super().__init__(text)
        self.key = text.lower() if key is None else key

    def __lt__(self, other):
        """Сравнивает ячейки по ключу сортировки."""
        return self.key < other.key


class LibsTable(QTableWidget):
    """Таблица библиотек: отметки, сортировка по столбцам и фильтр по имени.
    Ничего не знает ни про pip, ни про фоновые задачи: только показывает данные."""

    COLUMNS = ["Библиотека", "Версия", "Последняя версия"]

    def __init__(self):
        """Создаёт таблицу с заголовками и подключает сортировку по клику на заголовок."""
        super().__init__(0, len(self.COLUMNS))
        setup_table(self, self.COLUMNS, 0, False)
        self._query = ""
        self._sort = None
        header = self.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_sort)

    def fill(self, libs):
        """libs: список {"name", "version"} из pip. Последняя версия пока неизвестна ("...")."""
        self.setUpdatesEnabled(False)
        self.setRowCount(len(libs))
        for r, lib in enumerate(libs):
            name = Item(lib["name"])
            name.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            name.setCheckState(Qt.CheckState.Unchecked)
            self.setItem(r, 0, name)
            self.setItem(r, 1, Item(lib["version"], num_key(lib["version"])))
            self.setItem(r, 2, Item("...", (1, lib["name"].lower())))
        self._apply_filter()
        self.setUpdatesEnabled(True)
        self.resort()

    def show_latest(self, latest):
        """latest: {каноническое имя: версия} устаревших пакетов; None, если проверить не удалось."""
        self.setUpdatesEnabled(False)
        for r in range(self.rowCount()):
            name, cur = self.item(r, 0).text(), self.item(r, 1).text()
            if latest is None:
                cell = Item("—", (1, name.lower()))
            else:
                new = latest.get(canon(name))
                cell = Item(new or cur, (0 if new else 1, name.lower()))
                if new:
                    mark_warn(cell)
            self.setItem(r, 2, cell)
        self.setUpdatesEnabled(True)
        self.resort()

    def set_filter(self, text):
        """Задаёт строку поиска по имени и скрывает неподходящие строки."""
        self._query = canon(text.strip())
        self._apply_filter()

    def _apply_filter(self):
        """Скрывает строки, имя которых не содержит строку поиска."""
        for r in range(self.rowCount()):
            hidden = bool(self._query) and self._query not in canon(self.item(r, 0).text())
            self.setRowHidden(r, hidden)

    def _on_sort(self, col):
        """Сортирует по столбцу, повторный клик меняет порядок на обратный."""
        order = Qt.SortOrder.AscendingOrder
        if self._sort and self._sort[0] == col and self._sort[1] == order:
            order = Qt.SortOrder.DescendingOrder
        self._sort = (col, order)
        self.resort()

    def resort(self):
        """Столбец «Последняя версия»: по возрастанию устаревшие идут первыми."""
        if not self._sort:
            return
        col, order = self._sort
        self.sortItems(col, order)
        header = self.horizontalHeader()
        header.setSortIndicator(col, order)
        header.setSortIndicatorShown(True)
        self._apply_filter()

    def visible_rows(self):
        """Строки, видимые при текущем поиске: все операции работают только с ними."""
        return [r for r in range(self.rowCount()) if not self.isRowHidden(r)]

    def checked_rows(self):
        """[(имя, версия, последняя версия)] отмеченных видимых строк."""
        return [(self.item(r, 0).text(), self.item(r, 1).text(), self.item(r, 2).text())
                for r in self.visible_rows() if self.item(r, 0).checkState() == Qt.CheckState.Checked]

    def checked(self):
        """Возвращает имена отмеченных видимых библиотек."""
        return [name for name, _, _ in self.checked_rows()]

    def toggle_all(self):
        """Отмечает все видимые строки; если все уже отмечены, снимает отметки."""
        rows = self.visible_rows()
        all_checked = all(self.item(r, 0).checkState() == Qt.CheckState.Checked for r in rows)
        state = Qt.CheckState.Unchecked if all_checked else Qt.CheckState.Checked
        for r in rows:
            self.item(r, 0).setCheckState(state)

    def version_of(self, name):
        """Возвращает установленную версию библиотеки по имени или None."""
        return next((self.item(r, 1).text() for r in range(self.rowCount()) if self.item(r, 0).text() == name), None)

