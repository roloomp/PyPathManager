import os
import re


def norm(p):
    """Приводит путь к нормальному виду для сравнения: без лишних разделителей и в нижнем регистре."""
    return os.path.normcase(os.path.normpath(p))


def canon(name):
    """Каноническое имя пакета (PEP 503): 'Zope_Interface' и 'zope.interface' сравниваются одинаково."""
    return re.sub(r"[-_.]+", "-", name).lower()


_PRE = re.compile(r"[-_.]?(a|b|c|rc|alpha|beta|pre|preview|dev)", re.IGNORECASE)


def num_key(text):
    """Ключ сортировки версии: '3.10.1' > '3.9', '1.0rc1' < '1.0'."""
    m = re.match(r"(\d+(?:\.\d+)*)(.*)", text)
    if not m:
        return (), 0, text
    nums = tuple(int(x) for x in m[1].split("."))
    rest = m[2]
    return nums, 0 if _PRE.match(rest) else 1, rest
