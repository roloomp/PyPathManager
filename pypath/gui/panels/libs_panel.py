from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QMessageBox,
                             QFileDialog, QInputDialog, QLineEdit)
from pypath.services.pip import (get_libs, update_libs, delete_libs, install_libs,
                            get_outdated, install_from_file, get_versions, get_required_by, PROTECTED)
from pypath.common.utils import canon, num_key
from pypath.gui.dialogs import libs as dialogs
from pypath.gui.tasks import run_async
from pypath.gui.widgets import BTN_H, make_label, make_button, make_table, toolbar, mark_warn


class Item(QTableWidgetItem):
    """Ячейка с собственным ключом сортировки (версии сравниваются как числа)."""

    def __init__(self, text, key=None):
        super().__init__(text)
        self.key = text.lower() if key is None else key

    def __lt__(self, other):
        return self.key < other.key


class LibsPanel(QWidget):
    """Таблица библиотек выбранного интерпретатора (self.exe) и кнопки управления ими."""

    busy_changed = pyqtSignal()  # изменилось self.busy или self.checking

    def __init__(self, status, no_exe_text):
        super().__init__()
        self.busy = False      # выполняется загрузка или операция
        self.checking = False  # в фоне проверяются последние версии
        self.status = status
        self.no_exe_text = no_exe_text
        self.exe = None
        self.token = 0
        self.task = None  # текущая отменяемая задача
        self.locked = []  # виджеты страницы, блокируемые на время операции
        self.table = make_table(["Библиотека", "Версия", "Последняя версия"], 0, False)
        self.sort = None  # (столбец, порядок) последней сортировки по клику на заголовок
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.on_sort)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск библиотек")
        self.search.setFixedWidth(300)
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(BTN_H)
        self.search.textChanged.connect(self.apply_filter)

        left = [make_button("Установить", self.on_install),
                make_button("Обновить", self.on_update),
                make_button("Версия", self.on_version),
                make_button("Выбрать всё", self.on_select_all),
                make_button("Удалить", self.on_delete)]
        right = [make_button("Экспорт библиотек", self.on_export),
                 make_button("Импорт библиотек", self.on_import)]
        self.buttons = left + right
        # кнопка отмены не входит в self.buttons: set_busy её не блокирует
        self.cancel_btn = make_button("Отмена", self.on_cancel)
        self.cancel_btn.setShortcut("Esc")
        self.cancel_btn.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table, 1)
        layout.addLayout(toolbar(left, [self.cancel_btn, *right]))

    def header(self, title):
        """Строка заголовка секции: название слева, поиск справа."""
        row = QHBoxLayout()
        row.addWidget(make_label(title, 15))
        row.addStretch()
        row.addWidget(self.search)
        return row

    # ---- фоновые задачи и отмена ----

    def spawn(self, fn, args, on_ok, on_err, on_cancel, confirm_cancel=False):
        """Запускает отменяемую задачу; кнопка «Отмена» видна, пока она выполняется.
        confirm_cancel: перед отменой спросить, т.к. окружение может остаться изменённым наполовину."""
        def release(cb):
            def inner(*value):
                if self.task is task:
                    self.task = None
                    self.cancel_btn.hide()
                cb(*value)
            return inner

        task = run_async(fn, args, release(on_ok), release(on_err), release(on_cancel), cancellable=True)
        task.confirm_cancel = confirm_cancel
        self.task = task
        self.cancel_btn.show()

    def abort(self):
        """Прерывает текущую задачу без сообщений: её результат всё равно устарел."""
        if self.task:
            self.task.cancel()
            self.task = None
            self.cancel_btn.hide()

    def risky(self):
        """Идёт операция, которую нежелательно обрывать (изменение окружения или неотменяемая)."""
        return self.busy and (self.task is None or self.task.confirm_cancel)

    def on_cancel(self):
        task = self.task
        if not task:
            return
        if task.confirm_cancel and QMessageBox.question(
                self, "Отмена", "Прервать операцию?\nОкружение может остаться в промежуточном состоянии."
        ) != QMessageBox.StandardButton.Yes:
            return
        if task is self.task:  # пока висел вопрос, задача могла завершиться сама
            self.status.setText("Отмена...")
            task.cancel()

    # ---- таблица ----

    def on_sort(self, col):
        order = Qt.SortOrder.AscendingOrder
        if self.sort and self.sort[0] == col and self.sort[1] == order:
            order = Qt.SortOrder.DescendingOrder
        self.sort = (col, order)
        self.resort()

    def resort(self):
        """Столбец «Последняя версия»: по возрастанию устаревшие идут первыми."""
        if not self.sort:
            return
        col, order = self.sort
        self.table.sortItems(col, order)
        header = self.table.horizontalHeader()
        header.setSortIndicator(col, order)
        header.setSortIndicatorShown(True)
        self.apply_filter()  # скрытые строки привязаны к позиции, после сортировки пересчитываем

    def rows(self):
        """Строки, видимые при текущем поиске: все операции работают только с ними."""
        return [r for r in range(self.table.rowCount()) if not self.table.isRowHidden(r)]

    def apply_filter(self):
        q = canon(self.search.text().strip())
        for r in range(self.table.rowCount()):
            name = canon(self.table.item(r, 0).text())
            self.table.setRowHidden(r, bool(q) and q not in name)

    def checked(self):
        t = self.table
        return [t.item(r, 0).text() for r in self.rows()
                if t.item(r, 0).checkState() == Qt.CheckState.Checked]

    def set_busy(self, busy, text=None, lock_others=True):
        self.busy = busy
        self.busy_changed.emit()
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

    # ---- загрузка списка ----

    def reload(self):
        if self.exe and not self.busy:
            self.load(self.exe)

    def load(self, exe, note=""):
        self.abort()  # предыдущая загрузка или проверка обновлений уже не нужна
        self.token += 1
        token = self.token
        self.checking = False
        self.exe = exe
        self.table.setRowCount(0)
        if not exe:
            self.set_busy(False)
            return
        # при загрузке остальные виджеты не блокируются: смена выбора отменяет устаревший результат
        self.set_busy(True, "Загрузка библиотек...", lock_others=False)
        self.spawn(get_libs, (exe,),
                   lambda libs: self.on_loaded(token, exe, libs, note),
                   lambda msg: self.on_failed(token, msg),
                   lambda: self.on_load_cancelled(token))

    def on_loaded(self, token, exe, libs, note):
        if token != self.token:
            return
        t = self.table
        t.setUpdatesEnabled(False)
        t.setRowCount(len(libs))
        for r, lib in enumerate(libs):
            name = Item(lib["name"])
            name.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            name.setCheckState(Qt.CheckState.Unchecked)
            t.setItem(r, 0, name)
            t.setItem(r, 1, Item(lib["version"], num_key(lib["version"])))
            t.setItem(r, 2, Item("...", (1, lib["name"].lower())))
        self.apply_filter()
        t.setUpdatesEnabled(True)
        self.resort()
        base = f"{note}Библиотек: {len(libs)}"
        self.checking = True
        self.set_busy(False, base + ". Проверка обновлений...")
        # последние версии грузятся отдельно (нужна сеть, может быть долго)
        self.spawn(get_outdated, (exe,),
                   lambda latest: self.on_latest(token, latest, base),
                   lambda msg: self.on_latest_failed(token, base),
                   lambda: self.on_latest_failed(token, base, "Проверка обновлений отменена."))

    def on_latest(self, token, latest, base):
        if token != self.token:
            return
        self.checking = False
        self.busy_changed.emit()
        t = self.table
        t.setUpdatesEnabled(False)
        for r in range(t.rowCount()):
            name, cur = t.item(r, 0).text(), t.item(r, 1).text()
            new = latest.get(canon(name))
            cell = Item(new or cur, (0 if new else 1, name.lower()))
            if new:
                mark_warn(cell)
            t.setItem(r, 2, cell)
        t.setUpdatesEnabled(True)
        self.resort()
        self.status.setText(f"{base}, устарело: {len(latest)}")

    def on_latest_failed(self, token, base, reason="Не удалось проверить обновления."):
        if token != self.token:
            return
        self.checking = False
        self.busy_changed.emit()
        for r in range(self.table.rowCount()):
            self.table.setItem(r, 2, Item("—", (1, self.table.item(r, 0).text().lower())))
        self.status.setText(f"{base}. {reason}")

    def on_failed(self, token, msg):
        if token != self.token:
            return
        self.set_busy(False, f"Не удалось получить библиотеки: {msg}")

    def on_load_cancelled(self, token):
        if token != self.token:
            return
        self.set_busy(False, "Загрузка отменена. Обновить: F5.")

    # ---- операции ----

    def run_op(self, fn, args, start_text, ok_text):
        exe = self.exe
        self.set_busy(True, start_text)
        self.spawn(fn, (exe, *args),
                   lambda _: self.load(exe, ok_text + ". " if ok_text else ""),
                   lambda msg: self.set_busy(False, f"Ошибка: {msg}"),
                   # прерванная операция могла изменить часть пакетов: показываем реальное состояние
                   lambda: self.load(exe, "Операция отменена. "),
                   confirm_cancel=True)

    def on_select_all(self):
        t = self.table
        rows = self.rows()
        all_checked = all(t.item(r, 0).checkState() == Qt.CheckState.Checked for r in rows)
        state = Qt.CheckState.Unchecked if all_checked else Qt.CheckState.Checked
        for r in rows:
            t.item(r, 0).setCheckState(state)

    def on_install(self):
        if not self.need_exe():
            return
        answer = dialogs.ask_install(self)
        if not answer or not answer[0]:
            return
        names, ver = answer
        if ver:
            if len(names) != 1:
                self.status.setText("Версию можно указать только для одного пакета.")
                return
            names = [f"{names[0]}=={ver}"]
        self.run_op(install_libs, (names,), f"Установка: {', '.join(names)}...",
                    f"Установлено: {', '.join(names)}")

    def on_update(self):
        if not self.need_exe():
            return
        t = self.table
        names, skipped = [], 0
        for r in self.rows():
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

    def on_version(self):
        if not self.need_exe():
            return
        names = self.checked()
        if len(names) != 1:
            self.status.setText("Отметьте одну библиотеку.")
            return
        name = names[0]
        self.set_busy(True, f"Получение версий {name}...")
        self.spawn(get_versions, (self.exe, name),
                   lambda versions: self.pick_version(name, versions),
                   lambda msg: self.set_busy(False, f"Не удалось получить версии: {msg}"),
                   lambda: self.set_busy(False, "Отменено."))

    def pick_version(self, name, versions):
        self.set_busy(False)
        if not versions:
            self.status.setText(f"Версии {name} не найдены.")
            return
        t = self.table
        cur = next((t.item(r, 1).text() for r in range(t.rowCount()) if t.item(r, 0).text() == name), None)
        ver, ok = QInputDialog.getItem(self, "Версия", f"{name}, установлена {cur}:", versions,
                                       versions.index(cur) if cur in versions else 0, False)
        if not ok:
            return
        if ver == cur:
            self.status.setText("Эта версия уже установлена.")
            return
        self.run_op(install_libs, ([f"{name}=={ver}"],), f"Установка {name} {ver}...",
                    f"{name}: установлена версия {ver}")

    def on_delete(self):
        if not self.need_exe():
            return
        checked = self.checked()
        names = [n for n in checked if canon(n) not in PROTECTED]
        skipped = len(checked) - len(names)
        if not names:
            self.status.setText("pip, setuptools и wheel удалять нельзя." if skipped
                                else "Отметьте библиотеки для удаления.")
            return
        self.set_busy(True, "Проверка зависимостей...")
        # если проверка не удалась, просто спрашиваем без предупреждения
        self.spawn(get_required_by, (self.exe, names),
                   lambda info: self.confirm_delete(names, skipped, info),
                   lambda msg: self.confirm_delete(names, skipped, {}),
                   lambda: self.set_busy(False, "Отменено."))

    def confirm_delete(self, names, skipped, info):
        self.set_busy(False)
        if not dialogs.ask_delete(self, names, info):
            self.status.setText("")
            return
        self.run_op(delete_libs, (names,), f"Удаление: {len(names)} шт...",
                    f"Удалено библиотек: {len(names)}" + (f", пропущено защищённых: {skipped}" if skipped else ""))

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
        lines = [f"{t.item(r, 0).text()}=={t.item(r, 1).text()}" for r in self.rows()
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
