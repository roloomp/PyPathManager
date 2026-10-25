from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidgetItem, QMessageBox,
                             QFileDialog, QInputDialog)
from core.libraries import (get_libs, update_libs, delete_libs, install_libs,
                            get_outdated, install_from_file)
from core.task import run_async
from gui.widgets import make_button, make_table, toolbar


class LibsPanel(QWidget):
    """Таблица библиотек выбранного интерпретатора (self.exe) и кнопки управления ими."""

    def __init__(self, status, no_exe_text):
        super().__init__()
        self.status = status
        self.no_exe_text = no_exe_text
        self.exe = None
        self.token = 0
        self.locked = []  # виджеты страницы, блокируемые на время операции
        self.table = make_table(["Библиотека", "Версия", "Последняя версия"], 0, False)

        left = [make_button("Установить", self.on_install),
                make_button("Обновить", self.on_update),
                make_button("Выбрать всё", self.on_select_all),
                make_button("Удалить", self.on_delete)]
        right = [make_button("Экспорт библиотек", self.on_export),
                 make_button("Импорт библиотек", self.on_import)]
        self.buttons = left + right

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table, 1)
        layout.addLayout(toolbar(left, right))

    def checked(self):
        t = self.table
        return [t.item(r, 0).text() for r in range(t.rowCount())
                if t.item(r, 0).checkState() == Qt.CheckState.Checked]

    def set_busy(self, busy, text=None, lock_others=True):
        for b in self.buttons:
            b.setEnabled(not busy)
        for w in self.locked:
            w.setEnabled(not (busy and lock_others))
        if text:
            self.status.setText(text)

    def need_exe(self):
        if self.exe:
            return True
        self.status.setText(self.no_exe_text)
        return False

    def load(self, exe, note=""):
        self.token += 1
        token = self.token
        self.exe = exe
        self.table.setRowCount(0)
        if not exe:
            self.set_busy(False)
            return
        # при загрузке остальные виджеты не блокируются: смена выбора отменяет устаревший результат
        self.set_busy(True, "Загрузка библиотек...", lock_others=False)
        run_async(get_libs, (exe,),
                  lambda libs: self.on_loaded(token, exe, libs, note),
                  lambda msg: self.on_failed(token, msg))

    def on_loaded(self, token, exe, libs, note):
        if token != self.token:
            return
        t = self.table
        t.setUpdatesEnabled(False)
        t.setRowCount(len(libs))
        for r, lib in enumerate(libs):
            name = QTableWidgetItem(lib["name"])
            name.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            name.setCheckState(Qt.CheckState.Unchecked)
            t.setItem(r, 0, name)
            t.setItem(r, 1, QTableWidgetItem(lib["version"]))
            t.setItem(r, 2, QTableWidgetItem("..."))
        t.setUpdatesEnabled(True)
        base = f"{note}Библиотек: {len(libs)}"
        self.set_busy(False, base + ". Проверка обновлений...")
        # последние версии грузятся отдельно (нужна сеть, может быть долго)
        run_async(get_outdated, (exe,),
                  lambda latest: self.on_latest(token, latest, base),
                  lambda msg: self.on_latest_failed(token, base))

    def on_latest(self, token, latest, base):
        if token != self.token:
            return
        t = self.table
        t.setUpdatesEnabled(False)
        for r in range(t.rowCount()):
            name, cur = t.item(r, 0).text(), t.item(r, 1).text()
            new = latest.get(name.lower())
            cell = QTableWidgetItem(new or cur)
            if new:
                cell.setBackground(QColor("#fff3cd"))
                cell.setForeground(QColor("#7a5b00"))
            t.setItem(r, 2, cell)
        t.setUpdatesEnabled(True)
        self.status.setText(f"{base}, устарело: {len(latest)}")

    def on_latest_failed(self, token, base):
        if token != self.token:
            return
        for r in range(self.table.rowCount()):
            self.table.setItem(r, 2, QTableWidgetItem("—"))
        self.status.setText(f"{base}. Не удалось проверить обновления.")

    def on_failed(self, token, msg):
        if token != self.token:
            return
        self.set_busy(False, f"Не удалось получить библиотеки: {msg}")

    def run_op(self, fn, args, start_text, ok_text):
        exe = self.exe
        self.set_busy(True, start_text)
        run_async(fn, (exe, *args),
                  lambda _: self.load(exe, ok_text + ". " if ok_text else ""),
                  lambda msg: self.set_busy(False, f"Ошибка: {msg}"))

    def on_select_all(self):
        t = self.table
        rows = range(t.rowCount())
        all_checked = all(t.item(r, 0).checkState() == Qt.CheckState.Checked for r in rows)
        state = Qt.CheckState.Unchecked if all_checked else Qt.CheckState.Checked
        for r in rows:
            t.item(r, 0).setCheckState(state)

    def on_install(self):
        if not self.need_exe():
            return
        text, ok = QInputDialog.getText(self, "Установка", "Пакеты (через пробел):")
        names = text.split()
        if ok and names:
            self.run_op(install_libs, (names,), f"Установка: {len(names)} шт...",
                        f"Установлено: {len(names)}")

    def on_update(self):
        if not self.need_exe():
            return
        t = self.table
        names, skipped = [], 0
        for r in range(t.rowCount()):
            if t.item(r, 0).checkState() != Qt.CheckState.Checked:
                continue
            cur, latest = t.item(r, 1).text(), t.item(r, 2).text()
            # "...": последняя версия неизвестна, обновляем на всякий случай
            if latest in ("...", "—") or latest != cur:
                names.append(t.item(r, 0).text())
            else:
                skipped += 1
        if not names:
            self.status.setText("Выбранные библиотеки уже актуальны." if skipped
                                else "Отметьте библиотеки для обновления.")
            return
        done = f"Обновлено: {len(names)}" + (f", пропущено актуальных: {skipped}" if skipped else "")
        self.run_op(update_libs, (names,), f"Обновление: {len(names)} шт...", done)

    def on_delete(self):
        if not self.need_exe():
            return
        names = self.checked()
        if not names:
            self.status.setText("Отметьте библиотеки для удаления.")
            return
        if QMessageBox.question(self, "Удаление", f"Удалить библиотек: {len(names)}?") \
                != QMessageBox.StandardButton.Yes:
            return
        self.run_op(delete_libs, (names,), f"Удаление: {len(names)} шт...",
                    f"Удалено библиотек: {len(names)}")

    def on_export(self):
        names = self.checked()
        if not names:
            self.status.setText("Отметьте библиотеки для экспорта.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт библиотек", "requirements.txt",
                                              "requirements.txt (*.txt)")
        if not path:
            return
        t = self.table
        lines = [f"{t.item(r, 0).text()}=={t.item(r, 1).text()}" for r in range(t.rowCount())
                 if t.item(r, 0).checkState() == Qt.CheckState.Checked]
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except OSError as e:
            self.status.setText(f"Ошибка экспорта: {e}")
            return
        self.status.setText(f"Экспортировано библиотек: {len(lines)}")

    def on_import(self):
        if not self.need_exe():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Импорт библиотек", "", "requirements.txt (*.txt)")
        if path:
            self.run_op(install_from_file, (path,), "Установка из файла...", "Импорт выполнен")
