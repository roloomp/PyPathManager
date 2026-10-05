import os
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QMessageBox, QFileDialog)
from core.interpreters import get_all
from core.path_manager import set_active


def setup_table(win):
    t = win.python_table
    t.setColumnCount(3)
    t.setHorizontalHeaderLabels(["Версия", "Путь", "Статус"])
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.setShowGrid(False)
    t.setWordWrap(False)
    t.setTextElideMode(Qt.TextElideMode.ElideMiddle)
    h = t.horizontalHeader()
    h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)


def refresh(win):
    win.items = get_all() + win.manual
    t = win.python_table
    t.setRowCount(len(win.items))
    for r, i in enumerate(win.items):
        status = "Активный" if i["active"] else ""
        for c, text in enumerate((i["version"], i["path"], status)):
            cell = QTableWidgetItem(text)
            cell.setToolTip(text)
            if i["active"]:
                cell.setBackground(QColor("#dff3e3"))
                cell.setForeground(QColor("#1b5e20"))
            t.setItem(r, c, cell)
    if not win.items:  # поток A1
        win.status.setText("Python не найден. Укажите путь вручную.")


def on_add(win):
    path, _ = QFileDialog.getOpenFileName(win, "Выберите python.exe", "",
                                          "python.exe (python.exe)")
    if path and os.path.isfile(path):
        win.manual.append({"version": "?", "path": os.path.normpath(path), "active": False})
        refresh(win)


def on_confirm(win):
    row = win.python_table.currentRow()
    if row < 0:
        win.status.setText("Выберите интерпретатор в списке.")
        return
    item = win.items[row]
    if item["active"]:  # поток A2
        win.status.setText("Этот интерпретатор уже активен.")
        return
    try:
        set_active(item["path"], win.items)
    except OSError as e:
        QMessageBox.critical(win, "Ошибка", f"Не удалось изменить PATH:\n{e}")
        return
    win.status.setText("PATH изменён. Перезапустите терминал, чтобы увидеть изменение.")
    refresh(win)