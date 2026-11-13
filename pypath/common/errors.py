# Copyright (C) 2026 roloomp
# SPDX-License-Identifier: GPL-3.0-only

class CommandError(RuntimeError):
    """Внешняя команда (pip, venv) завершилась с ошибкой."""


class Cancelled(Exception):
    """Операция прервана пользователем."""
