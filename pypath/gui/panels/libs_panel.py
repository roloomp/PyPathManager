from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QInputDialog, QLineEdit, QVBoxLayout, QWidget

from pypath.common.utils import canon
from pypath.gui.dialogs import libs as dialogs
from pypath.gui.panels.libs_table import LibsTable
from pypath.gui.tasks import CONFIRM_ENV, TaskSlot
from pypath.gui.widgets import BTN_H, make_button, make_label, toolbar
from pypath.services.pip import (PROTECTED, delete_libs, get_libs, get_outdated, get_required_by, get_versions,
                                 install_from_file, install_libs, update_libs)


class LibsPanel(QWidget):
    """Библиотеки выбранного интерпретатора (self.exe): таблица, кнопки и операции pip.
    Таблица живёт в LibsTable, запуск и отмена фоновых задач в TaskSlot, здесь только сценарии."""

    busy_changed = pyqtSignal()  # изменилось self.busy или self.checking

    def __init__(self, status, no_exe_text, locked=()):
        """locked: виджеты страницы, которые блокируются на время операции."""
        super().__init__()
        self.busy = False      # выполняется загрузка или операция
        self.checking = False  # в фоне проверяются последние версии
        self.status = status
        self.no_exe_text = no_exe_text
        self.exe = None
        self.token = 0         # номер загрузки: результаты устаревших загрузок игнорируются
        self.locked = list(locked)
        self.slot = TaskSlot(self, status)
        self.table = LibsTable()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск библиотек")
        self.search.setFixedWidth(300)
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(BTN_H)
        self.search.textChanged.connect(self.table.set_filter)

        install = make_button("Установить", self.on_install)
        update = make_button("Обновить", self.on_update)
        version = make_button("Версия", self.on_version)
        delete = make_button("Удалить", self.on_delete)
        export = make_button("Экспорт", self.on_export)
        export.setToolTip("Записать отмеченные библиотеки в requirements.txt")
        import_ = make_button("Импорт", self.on_import)
        import_.setToolTip("Установить библиотеки из requirements.txt")
        self.select_all_btn = make_button("Выбрать всё", self.table.toggle_all)
        self.select_all_btn.setToolTip("Отметить или снять все видимые (найденные) библиотеки")
        # кнопка отмены (slot.button) не входит в self.buttons: set_busy её не блокирует
        self.buttons = [install, update, version, delete, export, import_, self.select_all_btn]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table, 1)
        layout.addLayout(toolbar([install, update, version, delete], [export, import_]))

    def header(self, title):
        """Строка заголовка секции: название слева, справа отмена, «Выбрать всё» и поиск."""
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(make_label(title, 15))
        row.addStretch()
        row.addWidget(self.slot.button)
        row.addWidget(self.select_all_btn)
        row.addWidget(self.search)
        return row

    # ---- фоновые задачи ----

    def spawn(self, fn, args, on_ok, on_err, on_cancel, confirm=None):
        self.slot.spawn(fn, args, on_ok, on_err, on_cancel, confirm)

    def abort(self):
        return self.slot.abort()

    def release_exe(self):
        """Останавливает всё, что держит интерпретатор панели (загрузку, проверку обновлений):
        перед удалением или пересозданием venv его файлы не должны быть заняты."""
        task = self.abort()
        self.token += 1  # поздние ответы прерванных задач игнорируются
        if self.checking:
            self.checking = False
            self.busy_changed.emit()
        if task:
            task.wait(3)

    def risky(self):
        """Идёт операция, которую нежелательно обрывать (изменение окружения или неотменяемая)."""
        return self.busy and (self.slot.task is None or self.slot.risky())

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
        self.table.fill(libs)
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
        self.table.show_latest(latest)
        self.status.setText(f"{base}, устарело: {len(latest)}")

    def on_latest_failed(self, token, base, reason="Не удалось проверить обновления."):
        if token != self.token:
            return
        self.checking = False
        self.busy_changed.emit()
        self.table.show_latest(None)
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
                   confirm=CONFIRM_ENV)

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
        names, skipped = [], 0
        for name, cur, latest in self.table.checked_rows():
            # "...": последняя версия неизвестна, обновляем на всякий случай
            if latest in ("...", "—") or latest != cur:
                names.append(name)
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
        names = self.table.checked()
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
        cur = self.table.version_of(name)
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
        checked = self.table.checked()
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
        rows = self.table.checked_rows()
        if not rows:
            self.status.setText("Отметьте библиотеки для экспорта.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт библиотек", "requirements.txt",
                                              "requirements.txt (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(f"{name}=={version}" for name, version, _ in rows) + "\n")
        except OSError as e:
            self.status.setText(f"Ошибка экспорта: {e}")
            return
        self.status.setText(f"Экспортировано библиотек: {len(rows)}")

    def on_import(self):
        if not self.need_exe():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Импорт библиотек", "", "requirements.txt (*.txt)")
        if path:
            self.run_op(install_from_file, (path,), "Установка из файла...", "Импорт выполнен")
