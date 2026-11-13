# Copyright (C) 2026 roloomp
# SPDX-License-Identifier: GPL-3.0-only

import logging
import sys
from logging.handlers import RotatingFileHandler

from pypath.config import paths


def setup():
    """Пишет лог в файл рядом с настройками и перехватывает необработанные исключения."""
    handler = RotatingFileHandler(paths.LOG_FILE, maxBytes=512_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])

    def log_unhandled(kind, value, tb):
        """Пишет необработанное исключение в лог и передаёт его стандартному обработчику."""
        logging.getLogger("pypath").critical("необработанное исключение", exc_info=(kind, value, tb))
        sys.__excepthook__(kind, value, tb)

    sys.excepthook = log_unhandled
