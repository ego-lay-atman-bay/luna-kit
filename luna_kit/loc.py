from collections import UserDict
import contextlib
import io
import json
import os
from pathlib import Path
import struct
from typing import BinaryIO

from .file_utils import PathOrBinaryFile, is_binary_file, is_text_file, open_binary


class LOC(UserDict):
    data: dict[str, str]
    
    def __init__(self, file: PathOrBinaryFile | None = None) -> None:
        super().__init__()
        
        self._string_count = 0
        self.filename = ''
        self.strings = self.data
        
        if file is not None:
            self.read(file)

    def read(self, file: PathOrBinaryFile):
        self.filename = ''
        if isinstance(file, (str, Path)):
            self.filename = str(file)

        self.data.clear()
        
        with open_binary(file, 'r') as open_file:
            self.__read_header(open_file)

            for x in range(self._string_count):
                key = self.__read_key(open_file)
                value = self.__read_value(open_file)
                self.data[key] = value
    
    def write(self, file: PathOrBinaryFile):
        """
        Write LOC file. The filename should be {language}.loc

        Args:
            file (PathOrBinaryFile): Output .loc file to write to.
        """
        with open_binary(file, 'w') as open_file:
            self.__write_header(open_file)
            for key, value in self.strings.items():
                self.__write_key(open_file, key)
                self.__write_value(open_file, value)
    
    def export(self, filename: str | None = None, **kwargs):
        """Export strings to a json file. Extra keyword arguments are passed into `json.dump()`, so you can do `.export('file.json', indent = 2)`.

        Args:
            filename (str | None, optional): Filename to save to. Defaults to original filename with .json file extension.
        """
        kwargs.setdefault("ensure_ascii", False)
        
        if filename == None:
            filename = os.path.splitext(self.filename)[0] + '.json'
        
        self.filename = filename
        
        with open(filename, 'w', encoding = 'utf-8') as file:
            json.dump(self.strings, file, **kwargs)
    
    def __read_header(self, file: BinaryIO):
        self._string_count = struct.unpack('<I',file.read(4))[0]
    
    def __write_header(self, file: BinaryIO):
        file.write(struct.pack('<I', len(self.strings)))
    
    def __read_key(self, file: BinaryIO):
        """Read the string key from the file. This assumes that the current position in the file object is on the key length.

        Args:
            file (BinaryIO): File-like object in binary read mode.

        Returns:
            str: string key
        """
        length = struct.unpack(
            '<I',
            file.read(4),
        )[0]
        
        # file.read(2) # padding
        
        key = file.read(length)
        
        return key.decode()
    
    def __write_key(self, file: BinaryIO, key: str):
        encoded = key.encode()
        file.write(struct.pack('<I', len(encoded)))
        file.write(encoded)
    
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
    
    def __write_value(self, file: BinaryIO, value: str):
        encoded = value.encode('utf-16')
        file.write(struct.pack('<I', len(encoded) // 2))
        file.write(encoded)

    def translate(self, key: str):
        data = {key.strip(): value for key, value in self.data.items()}
        return data.get(key.strip(), key)
    
    @property
    def language(self):
        return self.data.get('DEV_ID')
    
    @property
    def string_count(self):
        return len(self.data)

    def keys(self):
        return self.data.keys()
    
    def values(self):
        return self.data.values()
    
    def items(self):
        return self.data.items()
    
    def __repr__(self):
        return f'<{self.__class__.__name__} language={repr(self.language)} string_count={repr(self.string_count)}>'
