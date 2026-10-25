from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QPushButton, QTableWidget, QHeaderView, QAbstractItemView, QHBoxLayout

BTN_H = 33


def make_label(text, size):
    label = QLabel(text)
    font = QFont()
    font.setPointSize(size)
    label.setFont(font)
    return label


def make_button(text, handler):
    btn = QPushButton(text)
    btn.setMinimumHeight(BTN_H)
    btn.clicked.connect(lambda: handler())
    return btn


def make_table(headers, stretch_col, selectable):
    t = QTableWidget(0, len(headers))
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
    return t


def toolbar(left, right):
    row = QHBoxLayout()
    row.setSpacing(8)
    for b in left:
        row.addWidget(b)
    row.addStretch()
    for b in right:
        row.addWidget(b)
    return row
