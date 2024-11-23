from typing import IO, BinaryIO, TextIO
import io
from contextlib import nullcontext

import os

def is_eof(f: IO):
    s = f.read(1)
    if s != b'':    # restore position
        f.seek(-1, os.SEEK_CUR)
    return s == b''

def peek(f: IO, n: int):
    s = f.read(n)
    f.seek(-len(s), os.SEEK_CUR)
    return s


def is_text_file(file: IO):
    return isinstance(file, io.TextIOBase)


def is_binary_file(file: IO):
    return isinstance(file, (io.RawIOBase, io.BufferedIOBase))

def get_filesize(file: IO):
    pos = file.tell()
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(pos)
    return size

type PathOrBinaryFile = str | bytes | bytearray | BinaryIO

class BinaryReader():
    pass

def open_binary(file: PathOrBinaryFile) -> BinaryIO:
    if isinstance(file, str) and os.path.isfile(file):
        context_manager = open(file, 'rb')
    elif isinstance(file, (bytes, bytearray)):
        context_manager = io.BytesIO(file)
    elif is_binary_file(file):
        context_manager = nullcontext(file)
    elif is_text_file(file):
        raise TypeError('file must be open in binary mode')
    else:
        raise TypeError('cannot open file')
    
    return context_manager
