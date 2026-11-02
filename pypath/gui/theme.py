"""Цветовая схема приложения: как в системе, светлая или тёмная."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

MODES = (("system", "Как в системе"), ("light", "Светлая"), ("dark", "Тёмная"))
DEFAULT = "system"

_SCHEMES = {
    "system": Qt.ColorScheme.Unknown,
    "light": Qt.ColorScheme.Light,
    "dark": Qt.ColorScheme.Dark,
}

_LIGHT = {
    "Window": "#f0f0f0", "WindowText": "#000000", "Base": "#ffffff", "AlternateBase": "#f7f7f7",
    "Text": "#000000", "Button": "#f0f0f0", "ButtonText": "#000000", "ToolTipBase": "#ffffdc",
    "ToolTipText": "#000000", "Highlight": "#0078d4", "HighlightedText": "#ffffff",
    "PlaceholderText": "#707070", "Link": "#0066cc", "BrightText": "#ff0000",
    "Light": "#ffffff", "Midlight": "#e3e3e3", "Mid": "#a0a0a0", "Dark": "#a0a0a0", "Shadow": "#696969",
}
_DARK = {
    "Window": "#2b2b2b", "WindowText": "#e6e6e6", "Base": "#1e1e1e", "AlternateBase": "#262626",
    "Text": "#e6e6e6", "Button": "#3a3a3a", "ButtonText": "#e6e6e6", "ToolTipBase": "#3a3a3a",
    "ToolTipText": "#e6e6e6", "Highlight": "#3d7fd6", "HighlightedText": "#ffffff",
    "PlaceholderText": "#8a8a8a", "Link": "#6cb0ff", "BrightText": "#ff6b6b",
    "Light": "#5a5a5a", "Midlight": "#4a4a4a", "Mid": "#777777", "Dark": "#6a6a6a", "Shadow": "#000000",
}
_DARK_QSS = (
    "QTableView::indicator { width: 14px; height: 14px; border: 1px solid #8a8a8a;"
    " border-radius: 2px; background: #1e1e1e; }"
    "QTableView::indicator:checked { background: #3d7fd6; border-color: #3d7fd6; }"
)
_DISABLED = {False: "#a0a0a0", True: "#7a7a7a"}

_mode = DEFAULT


def valid(mode):
    """Возвращает mode, если такая тема существует, иначе тему по умолчанию."""
    return mode if mode in _SCHEMES else DEFAULT


def is_dark():
    """Показывает, тёмная ли тема сейчас включена (в режиме «как в системе» смотрит на систему)."""
    if _mode == "system":
        return QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    return _mode == "dark"


def build_palette(dark):
    """Собирает палитру светлой или тёмной темы."""
    palette = QPalette()
    for name, color in (_DARK if dark else _LIGHT).items():
        palette.setColor(getattr(QPalette.ColorRole, name), QColor(color))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(_DISABLED[dark]))
    return palette


def refresh():
    """Применяет палитру, соответствующую текущему режиму."""
    dark = is_dark()
    QApplication.setPalette(build_palette(dark))
    QApplication.instance().setStyleSheet(_DARK_QSS if dark else "")


def apply(mode):
    """Включает выбранную тему; режим «как в системе» следует за настройкой Windows."""
    global _mode
    _mode = valid(mode)
    QApplication.styleHints().setColorScheme(_SCHEMES[_mode])
    refresh()
