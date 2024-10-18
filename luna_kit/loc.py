import contextlib
import io
import json
import os
import struct
from typing import Annotated, BinaryIO

import dataclasses_struct as dcs

from . import file_utils
from .utils import is_binary_file, is_text_file


@dcs.dataclass()
class Header():
    magic: Annotated[bytes, 4] = bytes([0x59, 0x71, 0x00, 0x00])

class LocalizationFile():
    def __init__(self, file: str | bytes | bytearray | BinaryIO) -> None:
        self.header = Header()
        self.filename = ''
        
        self.read(file)

    def read(self, file: str | bytes | bytearray | BinaryIO):
        self.filename = ''

        if isinstance(file, str) and os.path.isfile(file):
            context_manager = open(file, 'rb')
            self.filename = file
        elif isinstance(file, (bytes, bytearray)):
            context_manager = io.BytesIO(file)
        elif is_binary_file(file):
            context_manager = contextlib.nullcontext(file)
        elif is_text_file(file):
            raise TypeError('file must be open in binary mode')
        else:
            raise TypeError('cannot open file')

        self.strings = {}
        
        with context_manager as open_file:
            self.__read_header(open_file)

            while not file_utils.is_eof(open_file):
                key = self.__read_key(open_file)
                value = self.__read_value(open_file)
                self.strings[key] = value
    
    def export(self, filename: str | None = None, **kwargs):
        """Export strings to a json file. Extra keyword arguments are passed into `json.dump()`, so you can do `.export('file.json', indent = 2)`.

        Args:
            filename (str | None, optional): Filename to save to. Defaults to original filename with .json file extension.
        """
        if filename == None:
            filename = os.path.splitext(self.filename)[0] + '.json'
        
        self.filename = filename
        
        with open(filename, 'w', encoding = 'utf-8') as file:
            json.dump(self.strings, file, **kwargs)
    
    def __read_header(self, file: BinaryIO):
        self.header = Header.from_packed(
            file.read(dcs.get_struct_size(Header))
        )
    
    def __read_key(self, file: BinaryIO):
        """Read the string key from the file. This assumes that the current position in the file object is on the key length.

        Args:
            file (BinaryIO): File-like object in binary read mode.

        Returns:
            str: string key
        """
        length = struct.unpack(
            'I',
            file.read(4),
        )[0]
        
        # file.read(2) # padding
        
        key = file.read(length)
        
        return key.decode()
    
    def __read_value(self, file: BinaryIO):
        """Read the string from the file. This assumes that the current position in the file object is on the string length. The string is encoded with utf-16, taking 2 bytes per character, with the length being the string length (not the byte length, so byte length = length * 2).

        Args:
            file (BinaryIO): File-like object in binary read mode.

        Returns:
            str: string
        """
        length = struct.unpack(
            'I',
            file.read(4),
        )[0]
        
        value = file.read(length * 2)
        
        return value.decode('utf-16')
