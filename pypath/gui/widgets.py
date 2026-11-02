from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton, QStyle,
                             QStyledItemDelegate, QStyleOptionViewItem, QTableWidget)

from pypath.gui import theme

BTN_H = 33
BTN_MIN_W = 96
MARGIN = 12
SECTION_GAP = 14
MARK_ROLE = Qt.ItemDataRole.UserRole + 1
MARK_COLORS = {
    "ok": {False: ("#dff3e3", "#1b5e20"), True: ("#1f4d2b", "#a5d6a7")},
    "warn": {False: ("#fff3cd", "#7a5b00"), True: ("#5c4a00", "#ffd54f")},
}


def paint(cell):
    """Красит ячейку по её отметке в цвета текущей темы; «ok» ещё и выделяет жирным, чтобы
    отметка была видна, даже когда строку закрывает выделение."""
    kind = cell.data(MARK_ROLE)
    if kind:
        bg, fg = MARK_COLORS[kind][theme.is_dark()]
        cell.setBackground(QColor(bg))
        cell.setForeground(QColor(fg))
        font = cell.font()
        font.setBold(kind == "ok")
        cell.setFont(font)


class MarkDelegate(QStyledItemDelegate):
    """Рисует выделенную строку поверх цвета отметки, а не вместо него: активный элемент виден всегда."""

    def paint(self, painter, option, index):
        """Для выделенной ячейки с отметкой рисует её цвета и накладывает полупрозрачное выделение."""
        if not (index.data(MARK_ROLE) and option.state & QStyle.StateFlag.State_Selected):
            super().paint(painter, option, index)
            return
        plain = QStyleOptionViewItem(option)
        plain.state &= ~QStyle.StateFlag.State_Selected
        super().paint(painter, plain, index)
        tint = option.palette.highlight().color()
        tint.setAlpha(70)
        painter.fillRect(option.rect, tint)


def mark_ok(cell):
    """Красит ячейку в цвета успеха."""
    cell.setData(MARK_ROLE, "ok")
    paint(cell)


def mark_warn(cell):
    """Красит ячейку в цвета предупреждения."""
    cell.setData(MARK_ROLE, "warn")
    paint(cell)


def recolor(table):
    """Перекрашивает отмеченные ячейки таблицы после смены темы."""
    for r in range(table.rowCount()):
        for c in range(table.columnCount()):
            cell = table.item(r, c)
            if cell:
                paint(cell)


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
    t.setItemDelegate(MarkDelegate(t))
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
