from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from core.interpreters import get_all
from core.path_manager import set_active


def show_libs(win, row):
    exe = win.items[row]["path"] if 0 <= row < len(win.items) else None
    win.libs.load(exe)


def refresh(win):
    t = win.python_table
    prev = win.items[t.currentRow()]["path"] if 0 <= t.currentRow() < len(win.items) else None
    win.items = get_all()
    t.blockSignals(True)
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
    t.blockSignals(False)
    if not win.items:
        win.libs.load(None)
        win.status.setText("Python не найден.")
        return
    row = next((r for r, i in enumerate(win.items) if i["path"] == prev), None)
    if row is None:
        row = next((r for r, i in enumerate(win.items) if i["active"]), 0)
    t.blockSignals(True)
    t.setCurrentCell(row, 0)
    t.blockSignals(False)
    show_libs(win, row)


def on_confirm(win):
    row = win.python_table.currentRow()
    if row < 0:
        win.status.setText("Выберите интерпретатор в списке.")
        return
    item = win.items[row]
    if item["active"]:
        win.status.setText("Этот интерпретатор уже активен.")
        return
    try:
        set_active(item["path"], win.items)
    except PermissionError:
        QMessageBox.critical(win, "Ошибка", "Python есть в системном PATH. "
                                            "Для его изменения перезапустите программу от имени администратора "
                                            "(Файл → Перезапустить от администратора).")
        return
    except OSError as e:
        QMessageBox.critical(win, "Ошибка", f"Не удалось изменить PATH:\n{e}")
        return
    refresh(win)
    win.status.setText("PATH изменён. Перезапустите терминал, чтобы увидеть изменение.")
