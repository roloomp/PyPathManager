import os
import re


def norm(p):
    return os.path.normcase(os.path.normpath(p))


def num_key(text):
    """Версия как кортеж чисел для сортировки: '3.10.1' > '3.9'."""
    return tuple(int(x) for x in re.findall(r"\d+", text))
