from typing import IO, BinaryIO, TextIO, TypeAlias
import io
from contextlib import nullcontext

import os

def is_eof(file: IO):
    char = b'' if is_binary_file(file) else ''
    
    pos = file.tell()
    s = file.read(1)
    if s != char:    # restore position
        file.seek(pos)
    return s == char

def peek(file: IO, n: int):
    pos = file.tell()
    s = file.read(n)
    file.seek(pos)
    return s

def is_text_file(file: IO):
    return isinstance(file, io.TextIOBase)

def is_binary_file(file: IO):
    return isinstance(file, (io.RawIOBase, io.BufferedIOBase))

def is_file_like(file: IO):
    return isinstance(file, io.IOBase)

def get_filesize(file: IO):
    pos = file.tell()
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(pos)
    return size

PathOrBinaryFile: TypeAlias = str | bytes | bytearray | BinaryIO
PathOrTextFile: TypeAlias = str | TextIO
PathOrFile: TypeAlias = PathOrBinaryFile | PathOrTextFile

class BinaryReader():
    pass

def open_binary(file: PathOrBinaryFile, mode = 'r') -> BinaryIO:
    """Open binary file

    Args:
        file (PathOrBinaryFile): The file input. Can be path to file, file-like object, `bytes`, or `bytearray`
        mode (str, optional): File mode. Will always add `'b'` if not in the mode. Note: this only applies to opening from path. Defaults to `'r'`.

    Raises:
        TypeError: file must be open in binary mode
        TypeError: cannot open file

    Returns:
        BinaryIO: File-like object. Note: if a file-like object was passed in, `.__exit__()` will not do anything.
    """
    if 'b' not in mode:
        mode += 'b'
    
    if isinstance(file, str) and os.path.isfile(file):
        context_manager = open(file, mode)
    elif isinstance(file, (bytes, bytearray)):
        context_manager = io.BytesIO(file)
    elif is_binary_file(file):
        context_manager = nullcontext(file)
    elif is_text_file(file):
        raise TypeError('file must be open in binary mode')
    else:
        raise TypeError('cannot open file')
    
    return context_manager

def open_text_file(file: PathOrTextFile, mode = 'r') -> TextIO:
    """Open text file

    Args:
        file (PathOrTextFile): The file input. Can be path to file or file-like object.
        mode (str, optional): File mode. Note: this only applies to opening from path. Defaults to `'r'`.

    Raises:
        TypeError: file must be open in text mode
        TypeError: cannot open file

    Returns:
        BinaryIO: File-like object. Note: if a file-like object was passed in, `.__exit__()` will not do anything.
    """
    if isinstance(file, str) and os.path.isfile(file):
        context_manager = open(file, 'r')
    elif isinstance(file, str):
        context_manager = io.StringIO(file)
    elif is_text_file(file):
        context_manager = nullcontext(file)
    elif is_binary_file(file):
        raise TypeError('file must be open in text mode')
    else:
        raise TypeError('cannot open file')
    
    return context_manager
