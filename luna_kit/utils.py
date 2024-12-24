import os
import pathlib
from typing import BinaryIO

import PIL.IcnsImagePlugin
import PIL.ImageChops


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
    
    if b'\x00' in data:
        data = data[:data.index(b'\x00')]

    return data.decode('ascii', errors='ignore')


def get_PIL_format(extension: str):
    import PIL.Image
    
    if not extension.startswith('.'):
        extension = '.' + extension
    extension = extension.lower()
    format = None
    extensions = PIL.Image.registered_extensions()
    try:
        format = extensions[extension]
    except KeyError as e:
        msg = f"unknown file extension: {extension}"
        raise ValueError(msg) from e
    
    return format


def split_name_num(name: str):
    head = name.rstrip('0123456789#')
    tail = name[len(head):]
    return head, tail

def increment_name_num(name: str, amount: int = 1):
    head, tail = split_name_num(name)
    number = 0

    if tail:
        number = int(tail)
        number += amount
        return '{head}{number:0{length}d}'.format(
            head = head,
            number = number,
            length = len(tail),
        )
    else:
        return name
