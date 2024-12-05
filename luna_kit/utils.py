import os
import pathlib
from typing import BinaryIO


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


def strToInt(value: str, default = 0):
    try:
        return int(float(value))
    except:
        return default

def strToFloat(value: str, default = 0.0):
    try:
        return float(value)
    except:
        return default

def strToBool(value: str):
    return str(value).lower() in ['t', 'true', '1', 'y', 'yes']


def read_ascii_string(file: BinaryIO | bytes, length: int = 64) -> str:
    if isinstance(file, (bytes, bytearray)):
        data = file
    else:
        data = file.read(length)

    return data.strip(b'\x00').decode('ascii', errors='ignore')
