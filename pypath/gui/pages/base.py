from PyQt6.QtWidgets import QWidget


class Page(QWidget):
    """Страница главного окна: своя строка статуса и панель библиотек (self.libs)."""

    def __init__(self, status):
        super().__init__()
        self.status = status
        self.libs = None  # LibsPanel, создаётся в наследнике

    def say(self, text):
        self.status.setText(text)

    def refresh(self):
        """Перечитать данные страницы (F5)."""
        raise NotImplementedError

    def on_shown(self):
        """Страницу открыли: подтянуть то, что могло измениться, пока она была скрыта."""
