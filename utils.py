# -*- coding: utf-8 -*-

import os
import sys


def parse_str(s):
    try:
        return int(s)
    except:
        try:
            return float(s)
        except:
            if s.lower() == "true":
                return True
            elif s.lower() == "false":
                return False
    return s


def str2num(s, default=0):
    try:
        return int(s)
    except:
        try:
            return float(s)
        except:
            return default


def str2int(str_val, default=0):
    try:
        return int(str_val)
    except:
        return default


def uniq(seq):
    # order preserving
    noDupes = []
    [noDupes.append(i) for i in seq if i not in noDupes]
    return noDupes


def rListFiles(path):
    files = []
    for f in os.listdir(path):
        if os.path.isdir(os.path.join(path, f)):
            files += rListFiles(os.path.join(path, f))
        else:
            files.append(os.path.join(path, f))
    return files


def uni(path, encoding=None):
    """
    Декодирует строку из кодировки файловой системы
    """
    if encoding is None:
        encoding = sys.getfilesystemencoding()
    if isinstance(path, str):
        path = path.decode(encoding, errors='ignore')
    return path


def utf(path):
    """
    Кодирует в utf8
    """
    if isinstance(path, unicode):
        return path.encode('utf8', errors='ignore')
    return path


def true_enc(path):
    """
    Для файловых операций в windows нужен unicode.
    Для остальных - utf8
    """
    if sys.platform.startswith('win'):
        return uni(path)
    return utf(path)


def fs_enc(path):
    """
    windows workaround. Используется в Popen.
    """
    return uni(path).encode(sys.getfilesystemencoding(), 'ignore')
