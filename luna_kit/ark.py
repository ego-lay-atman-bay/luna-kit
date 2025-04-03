import hashlib
import io
import logging
import os
import struct
import sys
import warnings
import zlib
from collections.abc import Callable, Iterable, Iterator
from copy import deepcopy
from ctypes import *
from dataclasses import dataclass
from datetime import datetime
from typing import IO, Annotated, Any, BinaryIO

try:
    import dataclasses_struct as dcs
    import zstandard
    from lxml import etree
except ImportError as e:
    e.add_note('ark dependencies could not be found')
    raise e

from . import enums, types, xxtea
from .file_utils import (PathOrBinaryFile, get_filesize, is_binary_file,
                         is_text_file, open_binary)
from .utils import posix_path, read_ascii_string, trailing_slash


def metadata_by_file_location(metadata: 'FileMetadata'):
    return metadata.file_location

@dcs.dataclass()
class _v1Header():
    file_count: dcs.U32 = 0
    metadata_offset: dcs.U32 = 0
    version: dcs.U32 = 0

@dcs.dataclass()
class _v3v4Header():
    file_count: dcs.U32 = 0
    metadata_offset: dcs.U32 = 0
    version: dcs.U32 = 0
    metadata_length: dcs.U32 = 0
    unknown: Annotated[bytes, 16] = b'\x00' * 16

@dataclass
class Header:
    version: int = 4
    file_count: int = 0
    metadata_offset: int = 0
    metadata_length: int = 0
    unknown: bytes = b''
    
    @property
    def struct_size(self):
        return dcs.get_struct_size(_HEADER_STRUCTS[self.version])
    
    def pack(self):
        match self.version:
            case 1:
                data = _v1Header(
                    file_count = self.file_count,
                    metadata_offset = self.metadata_offset,
                    version = self.version
                )
            case 3 | 4:
                data = _v3v4Header(
                    file_count = self.file_count,
                    metadata_offset = self.metadata_offset,
                    version = self.version,
                    metadata_length = self.metadata_length,
                    unknown = self.unknown,
                )
            case _:
                raise ValueError(f'Invalid ark version: {self.version}')
        
        return data.pack()
    
_HEADER_STRUCTS = {
    1: _v1Header,
    3: _v3v4Header,
    4: _v3v4Header,
}


HEADER_FORMAT = "3I"


@dcs.dataclass()
class _v1v3FileMetadataStruct:
    filename: Annotated[bytes, 128]
    pathname: Annotated[bytes, 128]
    file_location: dcs.U32
    original_filesize: dcs.U32
    compressed_size: dcs.U32
    encrypted_size: dcs.U32
    timestamp: dcs.U32
    md5sum: Annotated[bytes, 16]
    priority: dcs.U32

@dcs.dataclass()
class _v4FileMetadataStruct:
    filename: Annotated[bytes, 128]
    pathname: Annotated[bytes, 128]
    file_location: dcs.U32
    original_filesize: dcs.U32
    compressed_size: dcs.U32
    encrypted_size: dcs.U32
    timestamp: dcs.U32
    unknown1: dcs.U32
    unknown2: Annotated[bytes, 40]
    md5sum: Annotated[bytes, 16]
    priority: dcs.U32

@dataclass
class FileMetadata:
    filename: str
    pathname: str
    file_location: int
    original_filesize: int
    compressed_size: int
    encrypted_size: int
    timestamp: int
    md5sum: bytes
    unknown1: bytes
    unknown2: bytes
    priority: int
    
    version: int = 4

    @property
    def actual_size(self):
        return self.encrypted_size or self.compressed_size
    
    @property
    def struct_size(self):
        return dcs.get_struct_size(_METADATA_STRUCTS[self.version])
    
    # def __post_init__(self):
    #     
    #     self.__save_original()
    
    timestamp_multiplier = 13508
        
    @property
    def date(self):
        if self.version in [1, 4]:
            return datetime.fromtimestamp(self.timestamp)
        elif self.version == 3:
            return None
        
    def __save_original(self):
        self._filename = self.filename
        self._pathname = self.pathname
        self._file_location = self.file_location
        self._original_filesize = self.original_filesize
        self._compressed_size = self.compressed_size
        self._encrypted_nbytes = self.encrypted_size
        self._timestamp = self.timestamp
        self._md5sum = self.md5sum
        self._priority = self.priority
    
    @property
    def full_path(self):
        return os.path.join(self.pathname, self.filename)
    
    @full_path.setter
    def full_path(self, path: str):
        self.pathname = posix_path(os.path.dirname(path))
        self.filename = posix_path(os.path.basename(path))
    
    def pack(self, version = None):
        self.__save_original()
        if version:
            self.version = version
        match self.version:
            case 1 | 3:
                data = _v1v3FileMetadataStruct(
                    filename = self.filename.encode('ascii', errors = 'ignore'),
                    pathname = self.pathname.encode('ascii', errors = 'ignore'),
                    file_location = self.file_location,
                    original_filesize = self.original_filesize,
                    compressed_size = self.compressed_size,
                    encrypted_size = self.encrypted_size,
                    timestamp = self.timestamp,
                    md5sum = self.md5sum,
                    priority = self.priority,
                )
            case 4:
                data = _v4FileMetadataStruct(
                    filename = self.filename.encode('ascii', errors = 'ignore'),
                    pathname = self.pathname.encode('ascii', errors = 'ignore'),
                    file_location = self.file_location,
                    original_filesize = self.original_filesize,
                    compressed_size = self.compressed_size,
                    encrypted_size = self.encrypted_size,
                    timestamp = self.timestamp,
                    md5sum = self.md5sum,
                    priority = self.priority,
                    unknown1 = self.unknown1,
                    unknown2 = self.unknown2,
                )
            case _:
                raise ValueError(f'Invalid ark version: {self.version}')
        
        return data.pack()
            

_METADATA_STRUCTS: dict[int, _v1v3FileMetadataStruct | _v4FileMetadataStruct] = {
    1: _v1v3FileMetadataStruct,
    3: _v1v3FileMetadataStruct,
    4: _v4FileMetadataStruct,
}


FILE_METADATA_FORMAT = "128s128s5I16sI"

class ARK():
    KEY = [0x3d5b2a34, 0x923fff10, 0x00e346a4, 0x0c74902b]
    
    header: Header
    unknown_header_data: bytes
    _files: 'ARKMetadataCollection[FileMetadata]'
    
    _decompresser = zstandard.ZstdDecompressor()
    
    __files_block: io.BytesIO
    
    def __init__(
        self,
        file: str | bytes | bytearray | BinaryIO | None = None,
    ) -> None:
        """Extract `.ark` files.
        
        If you are going to be passing in a file-like object, there are a few things you need to consider.
        
        If you're planning on writing to the file, make sure the file is in read and write mode binary, so `r+b` or `w+b`. This is because I need to read the data in the ark file in order to add to it.

        Args:
            file (str | bytes | bytearray | BinaryIO | None, optional): Input file. Defaults to None.
            output (str | None, optional): Optional output folder to extract files to. Defaults to None.
        """
        self.__open_file: BinaryIO = None
        self.__close_file: bool = False
        self._files = ARKMetadataCollection()
        self.__files_block = io.BytesIO()
        self.header = Header()
        
        self.file = file
    
    @property
    def files(self):
        return deepcopy(self._files)
    
    @property
    def data_version(self):
        if 'data_ver.xml' not in self._files:
            return
        
        file = self.read_file(self._files['data_ver.xml'])

        tree = etree.parse(io.BytesIO(file.data))
        if tree is None:
            return
        root = tree.getroot()
        return root.attrib.get('Value')
    
    def __enter__(self):
        self.load()
        return self
    
    def load(self):
        self.open()
        self.read(self.__open_file)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def open(self):
        self.close()
        self.__close_file = True
        if isinstance(self.file, str):
            self.__open_file = open(self.file, 'r+b')
        elif isinstance(self.file, (bytes, bytearray)):
            self.__open_file = io.BytesIO(self.file)
        elif is_binary_file(self.file):
            self.__close_file = False
            self.__open_file = self.file
        elif is_text_file(self.file):
            self.__close_file = False
            raise TypeError('file must be open in binary mode')
        else:
            self.__close_file = False
            raise TypeError('cannot open file')
    
    def close(self):
        try:
            logging.debug('closing file')
        except:
            # Apparently logging.debug is None when you exit the repl
            pass
        if self.__close_file:
            if not self.__open_file.closed:
                self.__open_file.close()
        self.__close_file = False
    
    def __del__(self):
        self.close()
    
    def read(self, file: BinaryIO):
        """Extract `.ark` files.

        Args:
            file (str | bytes | bytearray | BinaryIO | None, optional): Input file.
            output (str | None, optional): Optional output folder to extract files to. Defaults to None.

        Raises:
            TypeError: file must be open in binary mode
            TypeError: cannot open file
        """
        if not is_binary_file(file):
            raise TypeError('file must be file-like object open in binary read mode')
        
        self._files = []
        
        file.seek(0)
        
        self.header = self._read_header(file)
        self._files = self._read_metadata(file)
    

    def write(self, file: BinaryIO):
        if not is_binary_file(file):
            raise TypeError('file must be file-like object open in binary write mode')
        
        file.seek(0)
        file.truncate()
        
        metadata_block = self._write_metadata(file)
        self.header.metadata_offset = self.header.struct_size + len(self.__files_block.getvalue())
        self.header.metadata_length = len(metadata_block)
        
        file.write(self._write_header(file))
        file.write(self.__files_block.getvalue())
        file.write(metadata_block)
        self.__files_block.seek(0)
        self.__files_block.truncate()
    
    def _get_file_block(self, file: BinaryIO):
        self._files.sort(key = metadata_by_file_location)
        first_file = self._files[0]
        self.__files_block.seek(0)
        self.__files_block.truncate()
        
        file.seek(first_file.file_location)
        self.__files_block.write(file.read(self.header.metadata_offset))
    
    def read_file(self, file: FileMetadata):
        return self._get_file_data(file, self.__open_file)

    def add_file(self, file: 'ARKFile'):
        data, metadata = file.pack()
        self._write_file(data, metadata, self.__open_file)
    
    def _read_header(self, file: IO) -> _v3v4Header:
        """Read the header of a `.ark` file.

        Args:
            file (IO): File-like object.

        Returns:
            dict: Header.
        """
        
        header_start = file.tell()
        file.seek(8)
        version = struct.unpack('<I', file.read(4))[0]
        file.seek(-1, os.SEEK_END)
        filesize = file.tell()
        file.seek(0)
        
        if version not in _HEADER_STRUCTS:
            raise ValueError(f'Unknown file version {header.ark_version}')
        
        raw_header: _v1Header | _v3v4Header = _HEADER_STRUCTS[version].from_packed(
            file.read(dcs.get_struct_size(_HEADER_STRUCTS[version]))
        )
        
        header = Header(
            version = raw_header.version,
            file_count = raw_header.file_count,
            metadata_offset = raw_header.metadata_offset,
            metadata_length = raw_header.metadata_length if hasattr(raw_header, 'metadata_length') else filesize - raw_header.metadata_offset,
            unknown = raw_header.unknown if hasattr(raw_header, 'unknown') else b'',
        )
        
        return header
    
    
    def _write_header(self, file: IO):
        self.header.file_count = len(self._files)
        
        return self.header.pack()


    def _read_metadata(self, file: IO) -> None | list[_v1v3FileMetadataStruct]:
        filesize: int = None
        
        file.seek(0, os.SEEK_END)
        
        filesize = file.tell()
        # print(filesize)
        
        if filesize < 0:
            raise TypeError('file size is negative, somehow...')
        
        metadata_size = xxtea.get_phdr_size(filesize - self.header.metadata_offset)
        # print(f'metadata size: {metadata_size}')
        
        raw_metadata_size = self.header.file_count * dcs.get_struct_size(_v1v3FileMetadataStruct)
        # print(f'raw metadata size: {raw_metadata_size}')
        
        
        file.seek(self.header.metadata_offset, os.SEEK_SET)
        
        
        metadata = file.read(metadata_size)
        
        # print(f'metadata: {int.from_bytes(metadata, 'little')}')
        metadata = xxtea.decrypt(metadata, metadata_size // 4, self.KEY)

        self.decrypted_metadata = metadata
        
        if self.header.version == 1:
            raw_metadata = metadata
        elif self.header.version in [3, 4]:
            raw_metadata = self._decompresser.decompress(metadata, raw_metadata_size)
        else:
            raise ValueError(f'Unknown file version {self.header.version}')
            
            
        self.raw_metadata = raw_metadata

        metadata_struct = _METADATA_STRUCTS[self.header.version]

        metadata_size = dcs.get_struct_size(metadata_struct)
        result = ARKMetadataCollection()
        for file_index in range(self.header.file_count):
            offset = file_index * metadata_size
            
            file_result: _v1v3FileMetadataStruct | _v4FileMetadataStruct = metadata_struct.from_packed(
                raw_metadata[offset : offset + metadata_size]
            )
            
            
            result.append(FileMetadata(
                filename = read_ascii_string(file_result.filename),
                pathname = read_ascii_string(file_result.pathname),
                file_location = file_result.file_location,
                original_filesize = file_result.original_filesize,
                compressed_size = file_result.compressed_size,
                encrypted_size = file_result.encrypted_size,
                timestamp = file_result.timestamp,
                md5sum = bytes.fromhex(file_result.md5sum.hex()) if hasattr(file_result, 'md5sum') else None,
                unknown1 = file_result.unknown1 if hasattr(file_result, 'unknown1') else None,
                unknown2 = file_result.unknown2 if hasattr(file_result, 'unknown2') else None,
                priority = file_result.priority,
                
                version = self.header.version,
            ))

        return result

    def _get_file_data(self, metadata: FileMetadata, file: BinaryIO):
        file.seek(metadata.file_location, os.SEEK_SET)
        
        file_data = file.read(metadata.encrypted_size if metadata.encrypted_size else metadata.compressed_size)
        
        compressed = False
        encrypted = False

        if (metadata.encrypted_size) != 0:
            encrypted = True
            file_data = xxtea.decrypt(file_data, metadata.encrypted_size // 4, self.KEY)
        
        if (metadata.compressed_size != metadata.original_filesize):
            compressed = True
            if self.header.version == 1:
                file_data = zlib.decompress(file_data)
            elif self.header.version >= 3:
                file_data = self._decompresser.decompress(file_data, metadata.original_filesize)
        
        file_data = file_data[:metadata.original_filesize]
        
        if metadata.md5sum is not None:
            if hashlib.md5(file_data).hexdigest() != metadata.md5sum.hex():
                warnings.warn(f'file "{posix_path(os.path.join(metadata.pathname, metadata.filename))}" hash does not match "{metadata.md5sum.hex()}"')
        
        return ARKFile(
            os.path.join(metadata.pathname, metadata.filename),
            file_data,
            encrypted = encrypted,
            compressed = compressed,
            priority = metadata.priority,
            date = metadata.date,
        )
    
    def _write_file(self, data: bytes, metadata: FileMetadata, file: BinaryIO):
        self._files.sort(key = metadata_by_file_location)
        
        self._get_file_block(file)
        
        header_offset = self.header.struct_size
        
        if metadata.file_location < 0:
            if len(self._files):
                metadata.file_location = self._files[-1].file_location + self._files[-1].actual_size
            else:
                metadata.file_location = self.header.struct_size
        if metadata.full_path not in self._files:
            metadata.file_location = self._files[-1].file_location + self._files[-1].actual_size
            self._files.append(metadata)
            self.__files_block.seek(metadata.file_location - header_offset)
            self.__files_block.truncate()
            self.__files_block.write(data)
            self.header.metadata_offset = metadata.file_location + metadata.actual_size
        else:
            found = self._files[metadata.full_path]
            current_index = self._files.index(found)
            rest_start = found.file_location + found.actual_size
            self.__files_block.seek(rest_start - header_offset)
            rest = file.read()

            metadata.file_location = found.file_location
            found.compressed_size = metadata.compressed_size
            found.encrypted_size = metadata.encrypted_size
            found.original_filesize = metadata.original_filesize
            found.md5sum = metadata.md5sum
            found.priority = metadata.priority
            found.timestamp = metadata.timestamp
            found.unknown1 = metadata.unknown1
            found.unknown2 = metadata.unknown2
            
            self.__files_block.seek(metadata.file_location - header_offset)
            file.truncate()
            file.write(data)
            offset = file.tell() - rest_start
            file.write(rest)

            for i in range(current_index + 1, len(self._files)):
                self._files[i].file_location += offset
        
        self.write(file)
        

    def _pack_files(self) -> list[tuple[bytes, _v1v3FileMetadataStruct]]:
        packed = []
        
        for file in self._files:
            if not isinstance(file, ARKFile):
                raise TypeError('file must be instance of ARKFile')
            
            data, meta = file.pack()
            
            packed.append((data, meta))
        
        return packed
    
    def _write_metadata(self, file: BinaryIO):
        self._files.sort(key = metadata_by_file_location)
        print('filesize', get_filesize(file))
        print('metadata_offset', self.header.metadata_offset)

        expected_size = self.header.file_count * dcs.get_struct_size(_METADATA_STRUCTS[self.header.version])
        
        metadata_block = b''
        for metadata in self._files:
            metadata_block += metadata.pack(self.header.version)
        
        print('expected size:', expected_size)
        print('actual size:', len(metadata_block))
        
        if self.header.version == 1:
            pass
        elif self.header.version in [3, 4]:
            metadata_block = zstandard.compress(metadata_block, 9)
        
        print('compressed size', len(metadata_block))
        metadata_block = xxtea.encrypt(metadata_block, self.KEY)
        print('encrypted size', len(metadata_block))

        return metadata_block
    
        
class ARKFile():
    def __init__(
        self,
        filename: str,
        data: bytes,
        compressed: bool = True,
        encrypted: bool = False,
        priority: int = 0,
        date: datetime | None = None,
    ) -> None:
        """File inside `.ark` file.

        Args:
            filename (str): The filename to be used inside the `.ark` file.
            data (bytes): File data.
        """
        self.fullpath = str(filename)
        self.data: bytes = bytes(data)
        
        self.compressed = compressed
        self.encrypted = encrypted
        
        self.priority = priority
        if isinstance(date, (int, float)):
            date = datetime.fromtimestamp(date)
        if date is None:
            date = datetime.now()
        self.timestamp = date
    
    @property
    def filename(self) -> str:
        """The base filename, such as `bar.txt`.

        Returns:
            str: filename
        """
        return os.path.basename(self.fullpath)
    @filename.setter
    def filename(self, name: str):
        self.fullpath = os.path.join(self.pathname, name)
    
    @property
    def pathname(self) -> str:
        """The directory path of the file, such as `foo/`. Outputs in posix format.

        Returns:
            str: directory
        """
        return trailing_slash(posix_path(os.path.dirname(self.fullpath)))
    @pathname.setter
    def pathname(self, name: str):
        self.fullpath = os.path.join(name, self.filename)
    
    @property
    def fullpath(self) -> str:
        """The full path of the file, such as `foo/bar.txt`. Output is in posix format.

        Returns:
            str: full path
        """
        self.fullpath = self._fullpath
        return self._fullpath

    @fullpath.setter
    def fullpath(self, path: str):
        self._fullpath = posix_path(path)
    
    def save(self, path: str | None = None):
        """Save this file to disk.

        Args:
            path (str | None, optional): Output filepath. Defaults to `fullpath`.
        """
        if path == None:
            path = self.fullpath
        
        path = os.path.abspath(path)
        
        os.makedirs(os.path.dirname(path), exist_ok = True)
        
        with open(path, 'wb') as file:
            file.write(self.data)
        
        
        if self.timestamp > datetime.now():
            logging.debug(f'{self.fullpath} date {self.timestamp} is after today {datetime.now()}')
        
        # os.utime(path, (self.date.timestamp(),))
    
    def pack(self) -> tuple[bytes, FileMetadata]:
        result = self.data
        metadata = FileMetadata(
            filename = self.filename,
            pathname = self.pathname,
            file_location = -1,
            original_filesize = len(result),
            compressed_size = 0,
            encrypted_size = 0,
            timestamp = self.timestamp.timestamp(),
            md5sum = bytes.fromhex(hashlib.md5(result).hexdigest()),
            priority = self.priority,
        )
        if self.compressed:
            result = zstandard.compress(result, 9)
            metadata.compressed_size = len(result)

        if self.encrypted:
            result = xxtea.encrypt(result, ARK.KEY)
            metadata.encrypted_size = len(result)
        
        return result, metadata


class ARKMetadataCollection(list):
    def __init__(self, metadatas: Iterable[FileMetadata] | None = None):
        if metadatas is None:
            super().__init__()
        else:
            super().__init__(metadatas)
    
    def get(self, key: str | int, default: Any = None) -> FileMetadata | Any:
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
    
    def setdefault(self, key: str | int, default: FileMetadata) -> FileMetadata:
        try:
            return self.__getitem__(key)
        except KeyError:
            self.__setitem__(key, default)
            return default
    
    def sort(self, *, key: Callable[[FileMetadata], Any] | None = lambda m: m.file_location, reverse: bool = False):
        return super().sort(key = key, reverse = reverse)
        
    def __getitem__(self, key: str | int) -> FileMetadata:
        if isinstance(key, str):
            for index, value in enumerate(self):
                if value.full_path == key:
                    key = index
                    break
        
        return super().__getitem__(key)

    def __setitem__(self, key: str | int, value: FileMetadata):
        if isinstance(key, str):
            for index, value in enumerate(self):
                if value.full_path == key:
                    key = index
                    break
        
        if isinstance(key, str):
            value.full_path = key
            self.append(value)
            return
        
        return super().__setitem__(key, value)
    
    def index(self, value: str | FileMetadata, start: int = 0, stop: int = sys.maxsize):
        if isinstance(value, str):
            for index in range(start, min(stop, len(self))):
                if self[index].full_path == value:
                    return index
        return super().index(value, start, stop)
    
    def copy(self):
        return ARKMetadataCollection(self)
    
    def __contains__(self, value: FileMetadata | str):
        if isinstance(value, str):
            for metadata in self:
                if metadata.full_path == value:
                    return True
        return super().__contains__(value)
    
    def __iter__(self) -> Iterator[FileMetadata]:
        return super().__iter__()
