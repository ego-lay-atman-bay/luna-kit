import contextlib
import hashlib
import io
import os
import struct
import warnings
import zlib
from collections import namedtuple
from ctypes import *
from dataclasses import dataclass
from typing import IO, Annotated, BinaryIO, Literal, NamedTuple

import dataclasses_struct as dcs
import zstandard

from . import enums

from . import types, xxtea
from .file_utils import is_binary_file, is_text_file, PathOrBinaryFile, open_binary
from .utils import posix_path, trailing_slash, read_ascii_string


@dcs.dataclass()
class Header():
    file_count: dcs.U32 = 0
    
    metadata_offset: dcs.U32 = 0
    ark_version: dcs.U32 = 0
    # unknown: Annotated[bytes, 20] = b''

HEADER_FORMAT = "3I"


@dcs.dataclass()
class _FileMetadataStruct:
    filename: Annotated[bytes, 128]
    pathname: Annotated[bytes, 128]
    file_location: dcs.U32
    original_filesize: dcs.U32
    compressed_size: dcs.U32
    encrypted_nbytes: dcs.U32
    timestamp: dcs.U32
    md5sum: Annotated[bytes, 16]
    priority: dcs.U32

@dataclass
class FileMetadata:
    filename: str
    pathname: str
    file_location: int
    original_filesize: int
    compressed_size: int
    encrypted_nbytes: int
    timestamp: int
    md5sum: bytes
    priority: int
    
    @property
    def full_path(self):
        return os.path.join(self.pathname, self.filename)
    
    @full_path.setter
    def full_path(self, path: str):
        self.pathname = os.path.dirname(path)
        self.filename = os.path.basename(path)


FILE_METADATA_FORMAT = "128s128s5I16sI"

class ARK():
    KEY = [0x3d5b2a34, 0x923fff10, 0x00e346a4, 0x0c74902b]
    
    header: Header
    files: list[FileMetadata]
    
    
    _decompresser = zstandard.ZstdDecompressor()
    
    def __init__(
        self,
        file: str | bytes | bytearray | BinaryIO | None = None,
        output: str | None = None,
        ignore_errors: bool = False,
    ) -> None:
        """Extract `.ark` files.

        Args:
            file (str | bytes | bytearray | BinaryIO | None, optional): Input file. Defaults to None.
            output (str | None, optional): Optional output folder to extract files to. Defaults to None.
        """
        self.__open_file: BinaryIO = None
        self.files: list[FileMetadata] = []
        self.header = Header()
        
        self.file = file
    
    def __enter__(self):
        self.open()
        self.read(self.__open_file)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def open(self):
        self.__close_file = True
        if isinstance(self.file, str):
            self.__open_file = open(self.file, 'rb')
        elif isinstance(self.file, (bytes, bytearray)):
            self.__open_file = io.BytesIO(self.file)
        elif is_binary_file(self.file):
            self.__close_file = False
            self.__open_file = self.file
        elif is_text_file(self.file):
            raise TypeError('file must be open in binary mode')
        else:
            raise TypeError('cannot open file')
    
    def close(self):
        if self.__close_file:
            self.__open_file.close()
        self.__close_file = False
    
    def read(
        self,
        file: BinaryIO,
    ):
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
        
        self.files = []
        
        self.__open_file.seek(0)
        
        self.header = self._read_header(self.__open_file)
        self.files = self._get_metadata(self.__open_file)
    

    def write(self, file: BinaryIO):
        if not is_binary_file(file):
            raise TypeError('file must be file-like object open in binary write mode')
        
        self.__open_file.seek(0)
        packed_files = self._pack_files()
        self.header.metadata_offset = dcs.get_struct_size(Header)
        for data, meta in packed_files:
            
            
            meta.file_location = self.header.metadata_offset
            self.header.metadata_offset += len(data)
        
        self._write_header(self.__open_file)
        self._write_files_and_metadata(self.__open_file, packed_files)
    
    def read_file(self, file: FileMetadata):
    
        return self._get_file_data(file, self.__open_file)
    def _read_header(self, file: IO) -> Header:
        """Read the header of a `.ark` file.

        Args:
            file (IO): File-like object.

        Returns:
            dict: Header.
        """
        
        header = Header.from_packed(
            file.read(dcs.get_struct_size(Header))
        )
        
        return header
    
    
    def _write_header(self, file: IO):
        self.header.file_count = len(self.files)
        
        self.header.metadata_offset
        
        file.write(self.header.pack())
        


    def _get_metadata(self, file: IO) -> None | list[_FileMetadataStruct]:
        filesize: int = None
        
        file.seek(0, os.SEEK_END)
        
        filesize = file.tell()
        # print(filesize)
        
        if filesize < 0:
            raise TypeError('file size is negative, somehow...')
        
        metadata_size = xxtea.get_phdr_size(filesize - self.header.metadata_offset)
        # print(f'metadata size: {metadata_size}')
        
        raw_metadata_size = self.header.file_count * dcs.get_struct_size(_FileMetadataStruct)
        # print(f'raw metadata size: {raw_metadata_size}')
        
        
        file.seek(self.header.metadata_offset, os.SEEK_SET)
        
        
        metadata = file.read(metadata_size)
        
        # print(f'metadata: {int.from_bytes(metadata, 'little')}')
        metadata = xxtea.decrypt(metadata, metadata_size // 4, self.KEY)
        
        if self.header.ark_version == 1:
            raw_metadata = metadata
        elif self.header.ark_version == 3:
            raw_metadata = self._decompresser.decompress(metadata, raw_metadata_size)
            
            

        metadata_size = dcs.get_struct_size(_FileMetadataStruct)
        result = []
        for file_index in range(self.header.file_count):
            offset = file_index * metadata_size
            
            
            file_result: _FileMetadataStruct = _FileMetadataStruct.from_packed(
                raw_metadata[offset : offset + metadata_size]
            )
            
            result.append(FileMetadata(
                filename = read_ascii_string(file_result.filename),
                pathname = read_ascii_string(file_result.pathname),
                file_location = file_result.file_location,
                original_filesize = file_result.original_filesize,
                compressed_size = file_result.compressed_size,
                encrypted_nbytes = file_result.encrypted_nbytes,
                timestamp = file_result.timestamp,
                md5sum = file_result.md5sum.hex(),
                priority = file_result.priority,
            ))

        return result
    
    def _fix_metadata(self, metadata: list[FileMetadata]):
        for file in metadata:

            file.filename = file.filename.decode('ascii').rstrip('\x00')
            file.pathname = file.pathname.decode('ascii').rstrip('\x00')
            file.md5sum = file.md5sum.hex()
        
        return metadata
            

    def _get_file_data(self, metadata: FileMetadata, file: IO):
        file.seek(metadata.file_location, os.SEEK_SET)
        
        file_data = file.read(metadata.encrypted_nbytes if metadata.encrypted_nbytes else metadata.compressed_size)

        compressed = False
        encrypted = False

        if (metadata.encrypted_nbytes) != 0:
            encrypted = True
            file_data = xxtea.decrypt(file_data, metadata.encrypted_nbytes // 4, self.KEY)
        
        if (metadata.compressed_size != metadata.original_filesize):
            compressed = True
            if self.header.ark_version == 1:
                file_data = zlib.decompress(file_data)
            elif self.header.ark_version == 3:
                file_data = self._decompresser.decompress(file_data, metadata.original_filesize)
        
        if hashlib.md5(file_data).hexdigest() != metadata.md5sum:
            warnings.warn(f'file "{posix_path(os.path.join(metadata.pathname, metadata.filename))}" hash does not match "{metadata.md5sum}"')
        
        return ARKFile(
            os.path.join(metadata.pathname, metadata.filename),
            file_data,
            encrypted = encrypted,
            compressed = compressed,
            priority = metadata.priority,
        )

    def _pack_files(self) -> list[tuple[bytes, _FileMetadataStruct]]:
        packed = []
        
        for file in self.files:
            if not isinstance(file, ARKFile):
                raise TypeError('file must be instance of ARKFile')
            
            data, meta = file.pack()
            
            packed.append((data, meta))
        
        return packed

    def _write_files_and_metadata(self, file: IO, packed_files: list[tuple[bytes, _FileMetadataStruct]]):
        metadata_block: bytes = b''
        for data, meta in packed_files:
            file.seek(meta.file_location)
            file.write(data)
            metadata_block += meta.pack()
        
        file.seek(self.header.metadata_offset)
        metadata_block = zstandard.compress(metadata_block)
        
        metadata_block = xxtea.encrypt(metadata_block, len(metadata_block) // 4, self.KEY)
        file.write(metadata_block)
        
class ARKFile():
    def __init__(
        self,
        filename: str,
        data: bytes,
        compressed: bool = True,
        encrypted: bool = False,
        priority: int = 0,
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
        
        os.makedirs(os.path.dirname(path), exist_ok = True)
        
        with open(path, 'wb') as file:
            file.write(self.data)
    
    def pack(self) -> bytes | _FileMetadataStruct:
        result = self.data
        metadata = _FileMetadataStruct(
            self.filename.encode('ascii'),
            self.pathname.encode('ascii'),
            0,
            len(result),
            len(result),
            0,
            0,
            bytes.fromhex(hashlib.md5(result).hexdigest()),
            self.priority,
        )
        if self.compressed:
            result = zstandard.compress(result, 9)
            metadata.compressed_size = len(result)

        if self.encrypted:
            result = xxtea.encrypt(result, len(result) // 4, ARK.KEY)
            metadata.encrypted_nbytes = len(result)
        
        return result, metadata
