class CommandError(RuntimeError):
    """Внешняя команда (pip, venv) завершилась с ошибкой."""


class Cancelled(Exception):
    """Операция прервана пользователем."""
