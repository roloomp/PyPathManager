from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
                             QButtonGroup, QMessageBox, QProgressBar)
from pypath.config.paths import SETTINGS_FILE
from pypath.gui.dialogs.help import show_docs, show_about
from pypath.gui.pages.path_page import PathPage
from pypath.gui.pages.venv_page import VenvPage
from pypath.gui.widgets import MARGIN, make_label, make_button
from pypath.system.admin import is_admin, restart_as_admin


class MainWindow(QMainWindow):
    def __init__(self):
        """Собирает главное окно: страницы, кнопки переключения, строку статуса, индикатор и меню."""
        super().__init__()
        self.setWindowTitle("PyPath Manager")
        self.setMinimumHeight(560)
        self.resize(900, 700)
        self.settings = QSettings(SETTINGS_FILE, QSettings.Format.IniFormat)

        self.status_stack = QStackedWidget()
        statuses = []
        for _ in range(2):
            label = make_label("", 10)
            label.setWordWrap(True)
            self.status_stack.addWidget(label)
            statuses.append(label)
        self.path_page = PathPage(statuses[0])
        self.venv_page = VenvPage(statuses[1])
        self.stack = QStackedWidget()
        self.stack.addWidget(self.path_page)
        self.stack.addWidget(self.venv_page)

        self.path_button = make_button("PATH", lambda: self.show_page(0))
        self.venv_button = make_button("venv", lambda: self.show_page(1))
        group = QButtonGroup(self)
        for b in (self.path_button, self.venv_button):
            b.setCheckable(True)
            group.addButton(b)
        self.path_button.setChecked(True)

        top = QHBoxLayout()
        top.addWidget(self.path_button)
        top.addWidget(self.venv_button)
        top.addStretch()

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedSize(120, 12)
        self.progress.hide()
        for page in (self.path_page, self.venv_page):
            page.libs.busy_changed.connect(self.update_progress)

        bottom = QHBoxLayout()
        bottom.addWidget(self.status_stack, 1)
        bottom.addWidget(self.progress)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(MARGIN, MARGIN, MARGIN, 8)
        root.setSpacing(8)
        root.addLayout(top)
        root.addWidget(self.stack, 1)
        root.addLayout(bottom)
        self.setCentralWidget(central)
        self.create_menu()

        self.venv_page.restore_chosen(self.settings.value("chosen_venv", ""))
        self.path_page.refresh()

    def create_menu(self):
        """Создаёт меню «Файл», «Вид» и «Справка» с горячими клавишами."""
        file_menu = self.menuBar().addMenu("Файл")
        self.admin_action = QAction("Запущено от администратора" if is_admin()
                                    else "Перезапустить от администратора", self)
        self.admin_action.setEnabled(not is_admin())
        self.admin_action.triggered.connect(self.restart_as_admin)
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(self.admin_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("Вид")
        for text, key, handler in (("Страница PATH", "Ctrl+1", lambda: self.show_page(0)),
                                   ("Страница venv", "Ctrl+2", lambda: self.show_page(1)),
                                   (None, None, None),
                                   ("Обновить", "F5", self.refresh),
                                   ("Поиск библиотек", "Ctrl+F", self.focus_search)):
            if text is None:
                view_menu.addSeparator()
                continue
            action = QAction(text, self)
            action.setShortcut(key)
            action.triggered.connect(handler)
            view_menu.addAction(action)

        help_menu = self.menuBar().addMenu("Справка")
        docs_action = QAction("Документация", self)
        docs_action.setShortcut("F1")
        docs_action.triggered.connect(lambda: show_docs(self))
        about_action = QAction("О приложении", self)
        about_action.triggered.connect(lambda: show_about(self))
        help_menu.addAction(docs_action)
        help_menu.addAction(about_action)

    def update_progress(self):
        """Показывает индикатор, пока на любой странице идёт операция или проверка обновлений."""
        self.progress.setVisible(any(p.libs.busy or p.libs.checking
                                     for p in (self.path_page, self.venv_page)))

    def refresh(self):
        """Перечитывает данные текущей страницы, если на ней не идёт операция."""
        page = self.stack.currentWidget()
        if page.libs.busy:
            return
        page.refresh()

    def focus_search(self):
        """Переводит фокус на поле поиска библиотек текущей страницы."""
        search = self.stack.currentWidget().libs.search
        search.setFocus()
        search.selectAll()

    def restart_as_admin(self):
        """Перезапускает программу с правами администратора, если нет активных операций."""
        if any(p.libs.busy for p in (self.path_page, self.venv_page)):
            self.status_stack.currentWidget().setText("Дождитесь окончания операции.")
            return
        self.save_settings()
        if restart_as_admin():
            self.close()
        else:
            self.status_stack.currentWidget().setText("Перезапуск отменён.")

    def show_page(self, index):
        """Переключает окно на страницу с указанным номером."""
        (self.path_button, self.venv_button)[index].setChecked(True)
        self.stack.setCurrentIndex(index)
        self.status_stack.setCurrentIndex(index)
        self.stack.widget(index).on_shown()

    def save_settings(self):
        """Сохраняет выбранный venv в файл настроек."""
        self.settings.setValue("chosen_venv", self.venv_page.chosen or "")
        self.settings.sync()

    def closeEvent(self, event):
        """Прерывает фоновые задачи (при необходимости с подтверждением) и закрывает окно."""
        pages = (self.path_page, self.venv_page)
        if any(p.libs.risky() for p in pages):
            answer = QMessageBox.question(self, "Выход", "Выполняется операция. Прервать её и выйти?")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        for task in [p.libs.abort() for p in pages]:
            if task:
                task.wait(10)
        self.save_settings()
        super().closeEvent(event)
