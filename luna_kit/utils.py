import io
import os
import pathlib
from typing import IO

def posix_path(path):
    result = pathlib.Path(path)
    if not result.parts:
        return ''
    else:
        return result.as_posix()

def trailing_slash(path):
    path = str(path)

    if path and not path.endswith('/'):
        path += '/'
    
    return path


def is_binary_file(file: IO):
    return isinstance(file, (io.RawIOBase, io.BufferedIOBase))


def is_text_file(file: IO):
    return isinstance(file, io.TextIOBase)


def strToInt(value: str, default = 0):
    try:
        return int(float(value))
    except:
        return default
