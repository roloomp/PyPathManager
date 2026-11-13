# Copyright (C) 2026 roloomp
# SPDX-License-Identifier: GPL-3.0-only

from PyQt6.QtWidgets import QMessageBox


def ask_venv_delete(parent, path):
    """Возвращает "disk", "list" или None (отмена)."""
    box = QMessageBox(parent)
    box.setWindowTitle("Удаление")
    box.setText(f"Что сделать с venv?\n{path}")
    disk = box.addButton("Удалить с диска", QMessageBox.ButtonRole.DestructiveRole)
    lst = box.addButton("Убрать из списка", QMessageBox.ButtonRole.AcceptRole)
    box.addButton(QMessageBox.StandardButton.Cancel)
    box.exec()
    return {disk: "disk", lst: "list"}.get(box.clickedButton())
