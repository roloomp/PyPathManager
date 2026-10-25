import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox, QFileDialog, QInputDialog
from core import venvs as vn
from core.interpreters import get_all
from core.task import run_async
from core.utils import norm


def same(a, b):
    return a is not None and b is not None and norm(a) == norm(b)


def setup(win):
    win.venvs = vn.load_list()
    refresh_table(win)
    refresh_pythons(win)


def current_path(win):
    row = win.venv_table.currentRow()
    return win.venvs[row] if 0 <= row < len(win.venvs) else None


def refresh_pythons(win):
    c = win.py_combo
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


def update_select_button(win):
    win.select_btn.setText("Снять выбор" if same(current_path(win), win.chosen) else "Выбрать")


def refresh_table(win, select=None):
    t = win.venv_table
    prev = select or current_path(win)
    t.blockSignals(True)
    t.setRowCount(len(win.venvs))
    for r, path in enumerate(win.venvs):
        chosen = same(path, win.chosen)
        texts = (os.path.basename(path), os.path.dirname(path), vn.version_of(path),
                 "Выбран" if chosen else "")
        for c, text in enumerate(texts):
            cell = QTableWidgetItem(text)
            cell.setToolTip(text)
            if chosen:
                cell.setBackground(QColor("#dff3e3"))
                cell.setForeground(QColor("#1b5e20"))
            t.setItem(r, c, cell)
    row = next((r for r, p in enumerate(win.venvs) if same(p, prev)), 0 if win.venvs else -1)
    t.setCurrentCell(row, 0 if row >= 0 else -1)
    t.blockSignals(False)
    update_select_button(win)


def add_venv(win, path, text):
    win.venvs.append(path)
    vn.save_list(win.venvs)
    refresh_table(win, select=path)
    win.libs.set_busy(False, text)


def on_create(win):
    python = win.py_combo.currentData()
    if not python:
        win.status.setText("Python не найден.")
        return
    folder = QFileDialog.getExistingDirectory(win, "Папка проекта")
    if not folder:
        return
    name, ok = QInputDialog.getText(win, "Создание venv", "Название:", text=".venv")
    name = name.strip()
    if not ok or not name:
        return
    if os.path.basename(name) != name:
        win.status.setText("Некорректное название.")
        return
    path = os.path.normpath(os.path.join(folder, name))
    if any(same(v, path) for v in win.venvs):
        win.status.setText("Такой venv уже в списке.")
    elif vn.is_venv(path):
        add_venv(win, path, "Добавлен существующий venv.")
    elif os.path.exists(path):
        win.status.setText("Папка уже существует и это не venv.")
    else:
        win.libs.set_busy(True, "Создание venv...")
        run_async(vn.create, (python, path),
                  lambda _: add_venv(win, path, "venv создан."),
                  lambda msg: win.libs.set_busy(False, f"Ошибка: {msg}"))


def ask_delete(win, path):
    """Возвращает "disk", "list" или None (отмена)."""
    box = QMessageBox(win)
    box.setWindowTitle("Удаление")
    box.setText(f"Что сделать с venv?\n{path}")
    disk = box.addButton("Удалить с диска", QMessageBox.ButtonRole.DestructiveRole)
    lst = box.addButton("Убрать из списка", QMessageBox.ButtonRole.AcceptRole)
    box.addButton(QMessageBox.StandardButton.Cancel)
    box.exec()
    return {disk: "disk", lst: "list"}.get(box.clickedButton())


def on_delete(win):
    path = current_path(win)
    if not path:
        win.status.setText("Выберите venv в списке.")
        return
    mode = ask_delete(win, path)
    if not mode:
        return

    def done(text):
        if same(path, win.chosen):
            win.chosen = None
            win.libs.load(None)
        win.venvs = [v for v in win.venvs if not same(v, path)]
        vn.save_list(win.venvs)
        refresh_table(win)
        win.libs.set_busy(False, text)

    if mode == "list":
        done("venv убран из списка.")
        return
    win.libs.set_busy(True, "Удаление venv...")
    run_async(vn.remove, (path,), lambda _: done("venv удалён."),
              lambda msg: win.libs.set_busy(False, f"Ошибка: {msg}"))


def on_add(win):
    folder = QFileDialog.getExistingDirectory(win, "Папка venv или проекта")
    if not folder:
        return
    # можно указать как саму папку venv, так и папку проекта, где она лежит
    path = next((p for p in (os.path.normpath(os.path.join(folder, sub))
                             for sub in ("", ".venv", "venv")) if vn.is_venv(p)), None)
    if not path:
        win.status.setText("В этой папке нет venv (нет файла pyvenv.cfg).")
    elif any(same(v, path) for v in win.venvs):
        win.status.setText("Такой venv уже в списке.")
    else:
        add_venv(win, path, "venv добавлен.")


def on_select(win):
    path = current_path(win)
    if not path:
        win.status.setText("Выберите venv в списке.")
        return
    if same(path, win.chosen):
        win.chosen = None
        win.libs.load(None)
        win.status.setText("Выбор снят.")
    elif not os.path.isfile(vn.python_of(path)):
        win.status.setText("venv повреждён: нет python.")
        return
    else:
        win.chosen = path
        win.libs.load(vn.python_of(path))
    refresh_table(win)


def on_change(win):
    path = current_path(win)
    python = win.py_combo.currentData()
    if not path:
        win.status.setText("Выберите venv в списке.")
        return
    if not python:
        win.status.setText("Python не найден.")
        return
    if vn.uses_python(path, python):
        win.status.setText("venv уже использует этот Python.")
        return
    if QMessageBox.question(win, "Изменение Python",
                            "Пересоздать venv на выбранном Python?\n"
                            "Библиотеки будут переустановлены, если получится.") \
            != QMessageBox.StandardButton.Yes:
        return

    def finish(text):
        refresh_table(win)
        if same(path, win.chosen):
            win.libs.load(vn.python_of(path), text + " ")
        else:
            win.libs.set_busy(False, text)

    win.libs.set_busy(True, "Смена Python...")
    run_async(vn.recreate, (python, path),
              lambda _: finish("Python изменён."),
              lambda msg: finish(f"Ошибка: {msg}."))


def on_browse(win):
    path, _ = QFileDialog.getOpenFileName(win, "Выберите файл", "", "Python (*.py *.pyw);;Все файлы (*)")
    if path:
        win.script_edit.setText(os.path.normpath(path))


def on_run(win):
    if not win.chosen:
        win.status.setText("Выберите venv.")
        return
    script = win.script_edit.text().strip()
    if not os.path.isfile(script):
        win.status.setText("Укажите существующий файл.")
        return
    try:
        vn.run_script(win.chosen, script)
    except OSError as e:
        win.status.setText(f"Ошибка запуска: {e}")
        return
    win.status.setText(f"Запущено: {os.path.basename(script)}")
