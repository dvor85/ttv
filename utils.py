# -*- coding: utf-8 -*-
# Writer (c) 2017, Vorotilin D.V., E-mail: dvor85@mail.ru


import os
import sys
import six

PY2 = sys.version_info[0] == 2


def parse_str(s):
    try:
        s = uni(s)
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


def cmp(a, b):  # @ReservedAssignment
    return (a > b) - (a < b)


def uni(s, from_encoding='utf8'):
    """
    Декодирует строку из кодировки encoding
    :path: строка для декодирования
    :from_encoding: Кодировка из которой декодировать.
    :return: unicode path
    """

    if isinstance(s, six.binary_type):
        return s.decode(from_encoding, 'ignore')
    return s


def str2(s, to_encoding='utf8'):
    """
    PY2 - Кодирует :s: в :to_encoding:
    """
    try:
        return six.ensure_str(s, to_encoding, errors='ignore')
    except TypeError:
        try:
            return six.text_type(s)
        except:
            return s


def to_bytes(s, to_encoding='utf8'):
    """
    PY2 - Кодирует :s: в :to_encoding:
    """
    try:
        return six.ensure_binary(s, to_encoding, errors='ignore')
    except TypeError:
        try:
            return six.binary_type(s)
        except:
            return s


def fs_str(s):
    if sys.platform.startswith('win'):
        return uni(s)
    return six.ensure_binary(s, encoding='utf8', errors='ignore')


def fs_enc(path, from_encoding='utf8'):
    """
    windows workaround. Используется в Popen.
    """
    if PY2:
        enc = sys.getfilesystemencoding()
        if enc is None:
            enc = 'utf8'
        return uni(path, from_encoding).encode(enc, 'ignore')
    return uni(path, from_encoding)


def makedirs(path, mode=0o0775):
    try:
        if not os.path.exists(path):
            os.makedirs(path, mode)
    except Exception as e:
        print(e)
