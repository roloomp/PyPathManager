from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QLabel, QPushButton, QTableWidget, QHeaderView, QAbstractItemView, QHBoxLayout

BTN_H = 33
BTN_MIN_W = 96
MARGIN = 12
SECTION_GAP = 14
OK_BG, OK_FG = "#dff3e3", "#1b5e20"
WARN_BG, WARN_FG = "#fff3cd", "#7a5b00"


def mark_ok(cell):
    """Красит ячейку в цвета успеха."""
    cell.setBackground(QColor(OK_BG))
    cell.setForeground(QColor(OK_FG))


def mark_warn(cell):
    """Красит ячейку в цвета предупреждения."""
    cell.setBackground(QColor(WARN_BG))
    cell.setForeground(QColor(WARN_FG))


def make_label(text, size):
    """Создаёт надпись с заданным размером шрифта."""
    label = QLabel(text)
    font = QFont()
    font.setPointSize(size)
    label.setFont(font)
    return label


def make_button(text, handler):
    """Создаёт кнопку стандартного размера, вызывающую handler без аргументов."""
    btn = QPushButton(text)
    btn.setMinimumHeight(BTN_H)
    btn.setMinimumWidth(BTN_MIN_W)
    btn.clicked.connect(lambda: handler())
    return btn


def setup_table(t, headers, stretch_col, selectable):
    """Единый вид таблиц: применяется и к обычной QTableWidget, и к её наследникам."""
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.setShowGrid(False)
    if selectable:
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    else:
        t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    h = t.horizontalHeader()
    for c in range(len(headers)):
        h.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch if c == stretch_col
                               else QHeaderView.ResizeMode.ResizeToContents)


def make_table(headers, stretch_col, selectable):
    """Создаёт таблицу с заголовками и общим оформлением."""
    t = QTableWidget(0, len(headers))
    setup_table(t, headers, stretch_col, selectable)
    return t


def toolbar(left, right):
    """Ряд кнопок с равными зазорами: left прижаты влево, right вправо."""
    row = QHBoxLayout()
    row.setSpacing(8)
    for b in left:
        row.addWidget(b)
    row.addStretch()
    for b in right:
        row.addWidget(b)
    return row
