# Copyright (C) 2026 roloomp
# SPDX-License-Identifier: GPL-3.0-only

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox

from pypath.common.utils import canon


def ask_install(parent):
    """Возвращает (список имён, версия) или None, если пользователь отказался."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("Установка")
    names_edit = QLineEdit()
    names_edit.setPlaceholderText("например: requests flask")
    ver_edit = QLineEdit()
    ver_edit.setPlaceholderText("пусто = последняя")
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    form = QFormLayout(dlg)
    form.addRow("Пакеты:", names_edit)
    form.addRow("Версия:", ver_edit)
    form.addRow(box)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return names_edit.text().split(), ver_edit.text().strip()


def ask_delete(parent, names, info):
    """info: {имя: [кому нужен]}. Показывает зависимости, которые останутся без пакета."""
    gone = {canon(n) for n in names}
    lines = []
    for name, users in info.items():
        left = [u for u in users if canon(u) not in gone]
        if left:
            lines.append(f"• {name} ← {', '.join(left)}")
    text = f"Удалить библиотек: {len(names)}?"
    if lines:
        shown = lines[:8] + ([f"…и ещё {len(lines) - 8}"] if len(lines) > 8 else [])
        text += "\n\nЭти библиотеки нужны другим пакетам:\n" + "\n".join(shown)
    return QMessageBox.question(parent, "Удаление", text) == QMessageBox.StandardButton.Yes
