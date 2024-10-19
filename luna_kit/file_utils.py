from typing import IO

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
