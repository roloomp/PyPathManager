import os
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QMessageBox, QFileDialog)
from core.interpreters import get_all
from core.path_manager import set_active
from core.libraries import get_libs, update_libs, delete_libs, get_outdated, install_from_file
from core.task import Task


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
    t.currentCellChanged.connect(lambda row, *_: show_libs(win, row))

    lt = win.libs_table
    lt.setColumnCount(3)
    lt.setHorizontalHeaderLabels(["Библиотека", "Версия", "Последняя версия"])
    lt.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    lt.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    lt.verticalHeader().setVisible(False)
    lt.setShowGrid(False)
    lt.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    lt.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    lt.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)


def checked_libs(win):
    lt = win.libs_table
    return [lt.item(r, 0).text() for r in range(lt.rowCount())
            if lt.item(r, 0).checkState() == Qt.CheckState.Checked]


def lib_buttons(win):
    return (win.lib_update, win.lib_delete, win.lib_select_all,
            win.fin_export, win.fin_import)


def set_busy(win, busy, text=None, lock_python=True):
    for b in lib_buttons(win):
        b.setEnabled(not busy)
    lock = busy and lock_python
    win.python_table.setEnabled(not lock)
    win.py_update.setEnabled(not lock)
    win.fin_confirm.setEnabled(not lock)
    if text:
        win.status.setText(text)


def run_async(win, fn, args, on_ok, on_err):
    task = Task(fn, *args)
    win.tasks.add(task)

    def done(cb, value):
        win.tasks.discard(task)
        cb(value)

    task.ok.connect(lambda v: done(on_ok, v))
    task.err.connect(lambda m: done(on_err, m))
    task.start()


def current_exe(win):
    row = win.python_table.currentRow()
    return win.items[row]["path"] if 0 <= row < len(win.items) else None


def show_libs(win, row, note=""):
    win.libs_table.setRowCount(0)
    win.libs_token += 1
    token = win.libs_token
    if row < 0 or row >= len(win.items):
        return
    # при загрузке список интерпретаторов не блокируется: смена выбора отменяет устаревший результат
    set_busy(win, True, "Загрузка библиотек...", lock_python=False)
    run_async(win, get_libs, (win.items[row]["path"],),
              lambda libs: on_libs_loaded(win, token, libs, note),
              lambda msg: on_libs_failed(win, token, msg))


def on_libs_loaded(win, token, libs, note=""):
    if token != win.libs_token:
        return
    lt = win.libs_table
    lt.setUpdatesEnabled(False)
    lt.setRowCount(len(libs))
    for r, lib in enumerate(libs):
        name = QTableWidgetItem(lib["name"])
        name.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        name.setCheckState(Qt.CheckState.Unchecked)
        lt.setItem(r, 0, name)
        lt.setItem(r, 1, QTableWidgetItem(lib["version"]))
        lt.setItem(r, 2, QTableWidgetItem("..."))
    lt.setUpdatesEnabled(True)
    base = f"{note}Библиотек: {len(libs)}"
    set_busy(win, False, base + ". Проверка обновлений...")
    # последние версии грузятся отдельно (нужна сеть, может быть долго)
    run_async(win, get_outdated, (current_exe(win),),
              lambda latest: on_latest_loaded(win, token, latest, base),
              lambda msg: on_latest_failed(win, token, base))


def on_latest_loaded(win, token, latest, base):
    if token != win.libs_token:
        return
    lt = win.libs_table
    lt.setUpdatesEnabled(False)
    for r in range(lt.rowCount()):
        name, cur = lt.item(r, 0).text(), lt.item(r, 1).text()
        new = latest.get(name.lower())
        cell = QTableWidgetItem(new or cur)
        if new:
            cell.setBackground(QColor("#fff3cd"))
            cell.setForeground(QColor("#7a5b00"))
        lt.setItem(r, 2, cell)
    lt.setUpdatesEnabled(True)
    win.status.setText(f"{base}, устарело: {len(latest)}")


def on_latest_failed(win, token, base):
    if token != win.libs_token:
        return
    lt = win.libs_table
    for r in range(lt.rowCount()):
        lt.setItem(r, 2, QTableWidgetItem("—"))
    win.status.setText(f"{base}. Не удалось проверить обновления.")


def on_libs_failed(win, token, msg):
    if token != win.libs_token:
        return
    set_busy(win, False, f"Не удалось получить библиотеки: {msg}")


def run_lib_op(win, fn, args, start_text, ok_text):
    exe = current_exe(win)
    set_busy(win, True, start_text)

    def ok(_):
        show_libs(win, win.python_table.currentRow(), ok_text + ". " if ok_text else "")

    def err(msg):
        set_busy(win, False, f"Ошибка: {msg}")

    run_async(win, fn, (exe, *args), ok, err)


def on_select_all(win):
    lt = win.libs_table
    rows = range(lt.rowCount())
    all_checked = all(lt.item(r, 0).checkState() == Qt.CheckState.Checked for r in rows)
    state = Qt.CheckState.Unchecked if all_checked else Qt.CheckState.Checked
    for r in rows:
        lt.item(r, 0).setCheckState(state)


def on_lib_update(win):
    lt = win.libs_table
    names, skipped = [], 0
    for r in range(lt.rowCount()):
        if lt.item(r, 0).checkState() != Qt.CheckState.Checked:
            continue
        cur, latest = lt.item(r, 1).text(), lt.item(r, 2).text()
        # "..." / "—": последняя версия неизвестна, обновляем на всякий случай
        if latest in ("...", "—") or latest != cur:
            names.append(lt.item(r, 0).text())
        else:
            skipped += 1
    if not names:
        win.status.setText("Выбранные библиотеки уже актуальны." if skipped
                           else "Отметьте библиотеки для обновления.")
        return
    done = f"Обновлено: {len(names)}" + (f", пропущено актуальных: {skipped}" if skipped else "")
    run_lib_op(win, update_libs, (names,), f"Обновление: {len(names)} шт...", done)


def on_lib_delete(win):
    names = checked_libs(win)
    if not names:
        win.status.setText("Отметьте библиотеки для удаления.")
        return
    if QMessageBox.question(win, "Удаление", f"Удалить библиотек: {len(names)}?") \
            != QMessageBox.StandardButton.Yes:
        return
    run_lib_op(win, delete_libs, (names,), f"Удаление: {len(names)} шт...",
               f"Удалено библиотек: {len(names)}")


def on_export(win):
    names = checked_libs(win)
    if not names:
        win.status.setText("Отметьте библиотеки для экспорта.")
        return
    path, _ = QFileDialog.getSaveFileName(win, "Экспорт библиотек", "requirements.txt",
                                          "requirements.txt (*.txt)")
    if not path:
        return
    lt = win.libs_table
    lines = [f"{lt.item(r, 0).text()}=={lt.item(r, 1).text()}" for r in range(lt.rowCount())
             if lt.item(r, 0).checkState() == Qt.CheckState.Checked]
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError as e:
        win.status.setText(f"Ошибка экспорта: {e}")
        return
    win.status.setText(f"Экспортировано библиотек: {len(lines)}")


def on_import(win):
    if not current_exe(win):
        win.status.setText("Выберите интерпретатор в списке.")
        return
    path, _ = QFileDialog.getOpenFileName(win, "Импорт библиотек", "", "requirements.txt (*.txt)")
    if path:
        run_lib_op(win, install_from_file, (path,), "Установка из файла...", "Импорт выполнен")


def refresh(win):
    prev = win.items[win.python_table.currentRow()]["path"] if 0 <= win.python_table.currentRow() < len(win.items) else None
    win.items = get_all() + win.manual
    t = win.python_table
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
        t.setRowCount(0)
        win.libs_table.setRowCount(0)
        win.libs_token += 1
        set_busy(win, False, "Python не найден. Укажите путь вручную.")
        return
    row = next((r for r, i in enumerate(win.items) if i["path"] == prev), None)
    if row is None:
        row = next((r for r, i in enumerate(win.items) if i["active"]), 0)
    t.blockSignals(True)
    t.setCurrentCell(row, 0)
    t.blockSignals(False)
    show_libs(win, row)


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
    if item["active"]:
        win.status.setText("Этот интерпретатор уже активен.")
        return
    try:
        set_active(item["path"], win.items)
    except OSError as e:
        QMessageBox.critical(win, "Ошибка", f"Не удалось изменить PATH:\n{e}")
        return
    refresh(win)
    win.status.setText("PATH изменён. Перезапустите терминал, чтобы увидеть изменение.")