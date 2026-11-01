import os
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
                             QButtonGroup, QProgressBar)
from core.admin import is_admin, restart_as_admin
from gui.handlers import python_handlers as py
from gui.handlers import venv_handlers as vh
from gui.help import show_docs, show_about
from gui.path_page import PathPage
from gui.venv_page import VenvPage
from gui.widgets import make_label, make_button

SETTINGS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.ini")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyPath Manager")
        self.setMinimumSize(730, 570)
        self.settings = QSettings(SETTINGS, QSettings.Format.IniFormat)

        self.status = make_label("", 10)
        self.status.setWordWrap(True)
        self.path_page = PathPage(self.status)
        self.venv_page = VenvPage(self.status)
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
        self.progress.setRange(0, 0)  # бегущая полоска: длительность неизвестна
        self.progress.setTextVisible(False)
        self.progress.setFixedSize(120, 12)
        self.progress.hide()
        for page in (self.path_page, self.venv_page):
            page.libs.busy_changed.connect(self.update_progress)

        bottom = QHBoxLayout()
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.progress)

        central = QWidget()
        root = QVBoxLayout(central)
        root.addLayout(top)
        root.addWidget(self.stack, 1)
        root.addLayout(bottom)
        self.setCentralWidget(central)
        self.create_menu()

        vh.setup(self.venv_page)
        vh.restore_chosen(self.venv_page, self.settings.value("chosen_venv", ""))
        py.refresh(self.path_page)

    def create_menu(self):
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
        self.progress.setVisible(any(p.libs.busy or p.libs.checking
                                     for p in (self.path_page, self.venv_page)))

    def refresh(self):
        page = self.stack.currentWidget()
        if page.libs.busy:
            return
        if page is self.path_page:
            py.refresh(page)
        else:
            vh.refresh(page)

    def focus_search(self):
        search = self.stack.currentWidget().libs.search
        search.setFocus()
        search.selectAll()

    def restart_as_admin(self):
        if any(p.libs.busy for p in (self.path_page, self.venv_page)):
            self.status.setText("Дождитесь окончания операции.")
            return
        self.save_settings()
        if restart_as_admin():
            self.close()
        else:
            self.status.setText("Перезапуск отменён.")

    def show_page(self, index):
        (self.path_button, self.venv_button)[index].setChecked(True)
        self.stack.setCurrentIndex(index)
        if index == 1:
            vh.refresh_pythons(self.venv_page)
            vh.ensure_libs(self.venv_page)

    def save_settings(self):
        self.settings.setValue("chosen_venv", self.venv_page.chosen or "")
        self.settings.sync()

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)
