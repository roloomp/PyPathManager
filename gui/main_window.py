from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QButtonGroup
from gui.handlers import python_handlers as py
from gui.handlers import venv_handlers as vh
from gui.path_page import PathPage
from gui.venv_page import VenvPage
from gui.widgets import make_label, make_button


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyPath Manager")
        self.setMinimumSize(730, 570)

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

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.stack, 1)
        root.addWidget(self.status)

        vh.setup(self.venv_page)
        py.refresh(self.path_page)

    def show_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == 1:
            vh.refresh_pythons(self.venv_page)
