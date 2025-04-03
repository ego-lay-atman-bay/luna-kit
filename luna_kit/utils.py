import os
import pathlib
from itertools import groupby
from typing import BinaryIO, Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    import PIL.Image


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

def put_alpha(image1: 'PIL.Image.Image', image2: 'PIL.Image.Image'):
    image2 = image2.convert('L')
    image1.putalpha(image2)
    return image1

def image_has_alpha(image: 'PIL.Image.Image', opaque: int = 255) -> bool:
    if image.info.get("transparency", None) is not None:
        return True
    if image.mode == "P":
        transparent = image.info.get("transparency", -1)
        for _, index in image.getcolors():
            if index == transparent:
                return True
    elif 'A' in image.mode:
        extrema = image.getextrema()
        if extrema[3][0] < 255:
            return True

    return False


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

def split_into_chunks(value: Iterable, n: int = 2):
    result = []
    for idx, chunk in groupby(enumerate(value), key=lambda x: x[0]//n):
        result.append([v for _, v in chunk])
    
    return result

def split_list(array: Iterable, wanted_parts: int = 2):
    length = len(array)
    return [
        array[i*length // wanted_parts: (i+1)*length // wanted_parts]
        for i in range(wanted_parts)
    ]
