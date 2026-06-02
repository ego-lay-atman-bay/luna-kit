from collections.abc import Iterable
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import io
import os
import pathlib
import shutil
import struct
import sys
import tempfile
from typing import (
    Annotated,
    BinaryIO,
    ClassVar,
    Iterator,
    Literal,
    Self,
    TYPE_CHECKING,
    Type,
    TypeVar,
)
import zlib

from .file_utils import PathOrBinaryFile, open_binary
from .utils import posix_path, read_ascii_string

# Buffer was added in python 3.12 and I'm keeping support for 3.11
if TYPE_CHECKING and sys.version_info >= (3,12):
    from collections.abc import Buffer

try:
    import dataclasses_struct as dcs
    import zstandard
    from . import xxtea
    from .console import console

except ImportError as e:
    e.add_note('ark dependencies could not be found')
    raise e

class BadARKFile(Exception):
    pass

class DataclassStructProtocol:
    """Stub for dataclass struct typechecking"""

    if TYPE_CHECKING:

        __dataclass_struct__: ClassVar[dcs.DataclassStructInternal]

        def pack(self) -> bytes: ...

        @classmethod
        def from_packed(cls, data: 'Buffer') -> Self: ...


@dcs.dataclass_struct(size = 'std', byteorder='little')
class _v1Header(DataclassStructProtocol):
    file_count: dcs.U32 = 0
    metadata_offset: dcs.U32 = 0
    version: dcs.U32 = 0

@dcs.dataclass_struct(size = 'std', byteorder='little')
class _v3v4Header(DataclassStructProtocol):
    file_count: dcs.U32 = 0
    metadata_offset: dcs.U32 = 0
    version: dcs.U32 = 0
    metadata_length: dcs.U32 = 0
    unknown: Annotated[bytes, 16] = b'\x00' * 16

_HEADER_STRUCTS: dict[int, Type[_v1Header | _v3v4Header]] = {
    1: _v1Header,
    3: _v3v4Header,
    4: _v3v4Header,
}

@dataclass
class ARKHeader:
    file_count: int = 0
    version: int = 4
    metadata_offset: int = -1
    metadata_length: int = -1
    unknown: bytes = b''

    @property
    def packed_size(self) -> int:
        """
        Get the packed byte length of the header. The size depends on
        the file version.

        Raises:
            BadARKFile: Unknown file version.

        Returns:
            int: The byte size of the header.
        """
        if self.version not in _HEADER_STRUCTS:
            raise BadARKFile(f'Unknown file version {self.version}')
        
        return _HEADER_STRUCTS[self.version].__dataclass_struct__.size

    def pack(self):
        """
        Pack the header into bytes.

        Raises:
            BadARKFile: Unknown file version

        Returns:
            bytes: The packed header
        """
        version_struct = _HEADER_STRUCTS.get(self.version)
        if not version_struct:
            raise BadARKFile(f'Unknown file version {self.version}')
        if issubclass(version_struct, _v1Header):
            return version_struct(
                file_count = self.file_count,
                metadata_offset = self.metadata_offset,
                version = self.version,
            ).pack()
        elif issubclass(version_struct, _v3v4Header):
            return version_struct(
                file_count = self.file_count,
                metadata_offset = self.metadata_offset,
                version = self.version,
                metadata_length = self.metadata_length,
                unknown = self.unknown,
            ).pack()
        else:
            raise BadARKFile(f'Unknown file version {self.version}')

    @classmethod
    def unpack(cls, file: BinaryIO):
        """
        Read the header from a file

        Args:
            file (BinaryIO): Input binary file-like object

        Raises:
            BadARKFile: Unknown header version

        Returns:
            ARKHeader: The parsed header
        """
        file.seek(8)
        version = struct.unpack('<I', file.read(4))[0]
        file.seek(-1, os.SEEK_END)
        filesize = file.tell()
        file.seek(0)

        if version not in _HEADER_STRUCTS:
            raise BadARKFile(f'Unknown file version {version}')
        
        header: _v1Header | _v3v4Header

        if version == 1:
            header = _v1Header.from_packed(
                file.read(_v1Header.__dataclass_struct__.size)
            )
        elif version == 3 or version == 4:
            header = _v3v4Header.from_packed(
                file.read(_v3v4Header.__dataclass_struct__.size)
            )
        else:
            raise BadARKFile(f"Unknown file version: {version}")
        
        return cls(
            file_count = header.file_count,
            version = header.version,
            metadata_offset = header.metadata_offset,
            metadata_length = header.metadata_length if isinstance(header, _v3v4Header) else filesize - header.metadata_offset,
            unknown = header.unknown if isinstance(header, _v3v4Header) else b'',
        )
    
    def copy(self) -> 'ARKHeader':
        """
        Create a copy of ARKHeader

        Returns:
            ARKHeader
        """
        return ARKHeader(
            self.file_count,
            self.version,
            self.metadata_offset,
            self.metadata_length,
            self.unknown,
        )



@dcs.dataclass_struct(size = 'std', byteorder='little')
class _v1v3MetadataStruct(DataclassStructProtocol):
    filename: Annotated[bytes, 128]
    pathname: Annotated[bytes, 128]
    file_location: dcs.U32
    original_filesize: dcs.U32
    compressed_size: dcs.U32
    encrypted_size: dcs.U32
    timestamp: dcs.U32
    md5sum: Annotated[bytes, 16]
    priority: dcs.U32

@dcs.dataclass_struct(size = 'std', byteorder='little')
class _v4MetadataStruct(DataclassStructProtocol):
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


_METADATA_STRUCTS: dict[int, Type[_v1v3MetadataStruct | _v4MetadataStruct]] = {
    1: _v1v3MetadataStruct,
    3: _v1v3MetadataStruct,
    4: _v4MetadataStruct,
}


@dataclass
class ARKMetadata:
    filename: str
    pathname: str = ''
    file_location: int = -1
    original_filesize: int = 0
    compressed_size: int = 0
    encrypted_size: int = 0
    timestamp: int = 0
    unknown1: int = 0
    unknown2: bytes = b''
    md5sum: bytes = b''
    priority: int = 0

    @property
    def full_path(self) -> str:
        """The full path joining the pathname and filename"""
        return pathlib.PurePath(self.pathname, self.filename).as_posix()

    @classmethod
    def unpack(cls, file: BinaryIO, version: int) -> Self:
        """
        Read metadata from a file

        Args:
            file (BinaryIO): Input binary file-like object
            version (int): Ark file version

        Raises:
            BadARKFile: Unknown file version

        Returns:
            ARKMetadata: Unpacked normalized metadata
        """
        metadata_struct = _METADATA_STRUCTS.get(version, None)
        if not metadata_struct:
            raise BadARKFile(f'Unknown file version: {version}')
        
        metadata = metadata_struct.from_packed(
            file.read(metadata_struct.__dataclass_struct__.size)
        )

        return cls(
            filename = read_ascii_string(metadata.filename),
            pathname = read_ascii_string(metadata.pathname),
            file_location = metadata.file_location,
            original_filesize = metadata.original_filesize,
            compressed_size = metadata.compressed_size,
            encrypted_size = metadata.encrypted_size,
            timestamp = metadata.timestamp,
            unknown1 = metadata.unknown1 if isinstance(metadata, _v4MetadataStruct) else 0,
            unknown2 = metadata.unknown2 if isinstance(metadata, _v4MetadataStruct) else b'',
            md5sum = metadata.md5sum,
            priority = metadata.priority,
        )
    
    def pack(self, version: int) -> bytes:
        """
        Pack metadata into bytes

        Args:
            version (int): Ark file version

        Raises:
            BadARKFile: Unknown file version

        Returns:
            bytes: Packed metadata
        """
        metadata_struct = _METADATA_STRUCTS.get(version, None)
        if not metadata_struct:
            raise BadARKFile(f'Unknown file version: {version}')
        
        if issubclass(metadata_struct, _v1v3MetadataStruct):
            return metadata_struct(
                filename = self.filename.encode(),
                pathname = self.pathname.encode(),
                file_location = self.file_location,
                original_filesize = self.original_filesize,
                compressed_size = self.compressed_size,
                encrypted_size = self.encrypted_size,
                md5sum = self.md5sum,
                timestamp = self.timestamp,
                priority = self.priority,
            ).pack()
        elif issubclass(metadata_struct, _v4MetadataStruct):
            return metadata_struct(
                filename = self.filename.encode(),
                pathname = self.pathname.encode(),
                file_location = self.file_location,
                original_filesize = self.original_filesize,
                compressed_size = self.compressed_size,
                encrypted_size = self.encrypted_size,
                md5sum = self.md5sum,
                timestamp = self.timestamp,
                unknown1 = self.unknown1,
                unknown2 = self.unknown2,
                priority = self.priority,
            ).pack()
        else:
            raise BadARKFile(f'Unknown file version: {version}')

    
    def packed_size(self, version: int) -> int:
        """
        Get the packed size

        Args:
            version (int): Ark file version

        Raises:
            BadARKFile: Unknown file version

        Returns:
            int: Packed size
        """
        if version not in _METADATA_STRUCTS:
            raise BadARKFile(f'Unknown file version: {version}')
        
        return _METADATA_STRUCTS[version].__dataclass_struct__.size
    
    def copy(self) -> 'ARKMetadata':
        """
        Return a copy of the ARKMetadata instance

        Returns:
            ARKMetadata
        """
        return ARKMetadata(
            self.filename,
            self.pathname,
            self.file_location,
            self.original_filesize,
            self.compressed_size,
            self.encrypted_size,
            self.timestamp,
            self.unknown1,
            self.unknown2,
            self.md5sum,
            self.priority,
        )

@dataclass
class ARKInfo:
    _filename: str
    _timestamp: datetime | None = field(default_factory = datetime.now)
    _compressed: bool = True
    _encrypted: bool = False
    _size: int = 0
    _md5sum: bytes = b''
    _priority: int = 0
    _unknown1: int = 0
    _unknown2: bytes = b''

    _dirty: bool = False

    @property
    def filename(self) -> str:
        return self._filename
    @property
    def timestamp(self) -> datetime | None:
        return self._timestamp
    @property
    def compressed(self) -> bool:
        return self._compressed
    @property
    def encrypted(self) -> bool:
        return self._encrypted
    @property
    def size(self) -> int:
        return self._size
    @property
    def md5sum(self) -> str:
        return self._md5sum.hex()
    @property
    def priority(self) -> int:
        return self._priority
    @property
    def unknown1(self) -> int:
        return self._unknown1
    @property
    def unknown2(self) -> bytes:
        return self._unknown2
    @property
    def dirty(self) -> bool:
        """
        This signifies if this file has been edited

        Returns:
            bool
        """
        return self._dirty
    
    
    def __repr__(self) -> str:
        result = self.__class__.__name__ + '('
        length = len(self.__dataclass_fields__) - 1
        for i, fieldname in enumerate(self.__dataclass_fields__):
            attr = fieldname.removeprefix('_')
            result += f'{attr}={repr(getattr(self, attr))}'
            if i == length:
                result += ', '
        result += ')'
        return result

class ARK:
    KEY = b'4*[=\x10\xff?\x92\xa4F\xe3\x00+\x90t\x0c'
    # KEY = [0x3d5b2a34, 0x923fff10, 0x00e346a4, 0x0c74902b]
    _decompressor = zstandard.ZstdDecompressor()

    __file_ctx: nullcontext | BinaryIO | None
    __file_pointer: BinaryIO | None
    mode: Literal['r', 'w', 'a']
    header: ARKHeader
    __metadata_collection: 'ARKMetadataCollection'
    _info_collection: dict[str, ARKInfo]
    __file_buffer: 'dict[str, ARKFile]'
    __removed_files: list[str]

    def __init__(self, file: PathOrBinaryFile, mode: Literal['r', 'w', 'a'] = 'r'):
        """
        This is the main entry interacting with ark files. This class is also
        a context manager, which handles opening and closing.

        ```python
        with ARK('test.ark') as ark:
            print(ark.namelist())
        ```

        A very common operation is extracting, which can be easily be done

        ```python
        with ARK('test.ark') as ark:
            ark.extract('data_ver.xml`, 'extracted/')
        ```

        You are also able to open files as binary file-like objects without
        writing to a file

        ```python
        import xml.etree.ElementTree as ET

        with ARK('test.ark') as ark:
            with ark.open('data_ver.xml') as arkfile:
                tree = ET.parse(arkfile)
                root = tree.getroot()
                print(f'version: {root.get("Value")}')
        ```

        Writing files is also easy

        ```python
        with ARK('test.ark', 'a') as ark:
            with ark.open('test.txt', 'w') as arkfile:
                arkfile.write(b'Hello world!')
        ```

        If the ark file is in write or append mode and you try to open a file
        in the ark file that doesn't exist in write mode, it creates that file
        inside the ark file.

        If you wish to use ark files outside a context manager, it is still possible

        ```python
        ark = ARK('test.ark')
        print(ark.namelist())
        ark.close()
        ```

        It is important to call the `ARK.close()` method, as that closes the
        underlying file. If you are in write mode, the `ARK.close()` will call
        `ARK.save()`, which writes the ark file to disk.

        ```python
        ark = ARK('test.ark', 'a')
        ark.write('test.txt') # Adds this file directly to the ark file
        ark.save() # Unnecessary call because .close() calls this
        ark.close()
        ```

        Modes:
            r: Read-only mode.
            w: Creates a brand new ark file and replaces whatever was in the input file.
            a: Open the ark file in append mode, which keeps the contents of the ark file if it already exists.

        Args:
            file (PathOrBinaryFile): Input binary file. Must match the mode in the `mode` input.
            mode (Literal['r', 'w', 'a'], optional): The mode to open the file in. Defaults to 'r'.

        Raises:
            ValueError: Unknown mode
            BadArkFile: Bad ark file
        """
        if mode not in ['r', 'w', 'a']:
            raise ValueError(f"Unknown mode: '{mode}'")
        
        self.mode = mode
        self.header = ARKHeader()
        self.__metadata_collection = ARKMetadataCollection()
        self._info_collection = {}
        self.__file_buffer = {}
        self.__removed_files = []

        match mode:
            case 'w':
                # Truncates file
                file_mode = 'w+b'
            case 'a':
                # Does not truncate contents
                file_mode = 'r+b'
            case _:
                # Do not allow writing
                file_mode = 'rb'
            
        self.filename = None
        if isinstance(file, str):
            self.filename = file
        
        self.__file_ctx = open_binary(file, file_mode)
        self.__file_pointer = self.__file_ctx.__enter__()
        if mode in ['r', 'a']:
            self._read()
    
    def _read(self):
        self._read_header()
        self._read_metadata_block()


    def _read_header(self):
        if self.__file_pointer:
            self.header = ARKHeader.unpack(self.__file_pointer)

    def _read_metadata_block(self):
        if not self.__file_pointer:
            return
        
        self.__metadata_collection._clear()
        self._info_collection.clear()
        self.__file_buffer.clear()
        self.__removed_files.clear()
        
        if self.header.metadata_offset <= 0 or self.header.metadata_length <= 0:
            # Nothing to read
            return
        
        self.__file_pointer.seek(0, os.SEEK_END)
        filesize = self.__file_pointer.tell()


        if filesize < 0:
            raise BadARKFile('file size is negative, somehow...')
        
        if self.header.metadata_offset > filesize:
            raise BadARKFile('Metadata offset is larger filesize')
        
        if self.header.metadata_offset + self.header.metadata_length > filesize:
            raise BadARKFile("Metadata exceeds filesize")
        
        metadata_struct = _METADATA_STRUCTS[self.header.version]
        metadata_size = dcs.get_struct_size(metadata_struct)
        raw_metadata_size = self.header.file_count * metadata_size
        packed_metadata_size = xxtea.get_phdr_size(self.header.metadata_length)


        self.__file_pointer.seek(self.header.metadata_offset, os.SEEK_SET)

        raw_metadata = self.__file_pointer.read(packed_metadata_size)

        self.encrypted_metadata = raw_metadata

        raw_metadata = xxtea.decrypt(raw_metadata, self.KEY)

        self.compressed_metadata = raw_metadata

        if self.header.version in [3,4]:
            raw_metadata = self._decompressor.decompress(raw_metadata, raw_metadata_size)
        
        if len(raw_metadata) != raw_metadata_size:
            raise BadARKFile(f"Expecting metadata size of {raw_metadata_size} but got {len(raw_metadata)}")
        
        self.raw_metadata = raw_metadata

        for file_index in range(self.header.file_count):
            offset = file_index * metadata_size

            metadata = metadata_struct.from_packed(
                raw_metadata[offset : offset + metadata_size]
            )

            self.__metadata_collection._add_metadata(ARKMetadata(
                filename = read_ascii_string(metadata.filename),
                pathname = read_ascii_string(metadata.pathname),
                file_location = metadata.file_location,
                original_filesize = metadata.original_filesize,
                compressed_size = metadata.compressed_size,
                encrypted_size = metadata.encrypted_size,
                timestamp = metadata.timestamp,
                unknown1 = metadata.unknown1 if isinstance(metadata, _v4MetadataStruct) else 0,
                unknown2 = metadata.unknown2 if isinstance(metadata, _v4MetadataStruct) else b'',
                md5sum = metadata.md5sum,
                priority = metadata.priority,
            ), raw = True)
        
        self.__metadata_collection._sort_collection()

        for metadata in self.__metadata_collection:
            self._info_collection[metadata.full_path] = self.getinfo(metadata)

    def _write_metadata_block(self, metadata_list: list[ARKMetadata]):
        data = b''
        for metadata in metadata_list:
            data += metadata.pack(self.header.version)
        
        self.raw_metadata = data

        # Don't try to compress and encrypt
        if len(metadata_list) == 0:
            return data
        
        if self.header.version in [3,4]:
            data = zstandard.compress(data, 12)
        
        self.compressed_metadata = data

        data = xxtea.encrypt(data, self.KEY)
        self.encrypted_metadata = data

        return data
    
    def _get_file_data(self, metadata: ARKMetadata) -> bytes:
        if not self.__file_pointer:
            raise ValueError('Ark file is closed')
        
        file_info = self.getinfo(metadata)

        packed_size = metadata.original_filesize
        if file_info.compressed:
            packed_size = metadata.compressed_size
        if file_info.encrypted:
            packed_size = metadata.encrypted_size

        self.__file_pointer.seek(metadata.file_location, os.SEEK_SET)
        file_data = self.__file_pointer.read(packed_size)

        if file_info.encrypted:
            file_data = xxtea.decrypt(file_data, self.KEY)
        
        if file_info.compressed:
            if self.header.version == 1:
                file_data = zlib.decompress(file_data)
            elif self.header.version in [3,4]:
                file_data = self._decompressor.decompress(file_data, metadata.original_filesize)
            else:
                raise ValueError(f'Unknown file version: {self.header.version}')
        
        # Trim extra null bytes
        file_data = file_data[:metadata.original_filesize]
        
        return file_data

    
    def _buffer_file(self, file: 'ARKFile'):
        if self.closed:
            raise ValueError('Ark file is closed')
        if not self.writable():
            raise ValueError('Cannot write to readonly ark file')
        
        self.__file_buffer[file._info.filename] = file
        self._info_collection[file.filename] = file._info
        file._info._dirty = True
        if file.filename in self.__removed_files:
            self.__removed_files.remove(file.filename)

    def open(self, file: 'str | ARKInfo | ARKMetadata', mode: Literal['r', 'w', 'a'] = 'r') -> 'ARKFile':
        """
        Opens this file in the ark file in whatever mode is specified (always binary)

        The returning `ARKFile` object is a file-like object that allows for
        standard read/write operations (given you're in a mode that accepts it).
        If you open a file in write/append mode and it doesn't exist, it will be
        created.

        ```python
        with ARK('test.ark') as ark:
            with ark.open('data_ver.xml', 'r') as arkfile:
                print(arkfile.read())
        
        with ARK('test.ark', 'a') as ark:
            with ark.open('data_ver.xml', 'w') as arkfile:
                arkfile.write(b'<Version Value="11.2.0.0"/>')
        ```

        You don't need to use context managers, but you *must* close the `ARKFile`
        before the `ARK` class is closed (or exiting the context manager), especially
        if you are in write mode, otherwise the file will not be written to the ark file.

        ```python
        with ARK('test.ark') as ark:
            arkfile = ark.open('data_ver.xml')
            print(arkfile.read())
            arkfile.close()

        ark = ARK('test.ark', 'a')
        arkfile = ark.open('data_ver.xml', 'w')
        arkfile.write(b'<Version Value="11.2.0.0"/>')
        arkfile.close() # Make sure the file is written to the ark file
        ark.close()
        ```

        Modes:
            r: Read-only mode.
            w: Write mode. Will truncate if the file already exists.
            a: Append mode, opens in edit mode without deleting any data.

        Args:
            file (str | ARKInfo | ARKMetadata): The file to open
            mode (Literal[&#39;r&#39;, &#39;w&#39;, &#39;a&#39;], optional): The mode to open the file in. Defaults to 'r'.

        Raises:
            ValueError: Ark file is closed
            ValueError: Invalid mode
            ValueError: Cannot write to read-only ark file
            ValueError: Filename can't be blank
            FileNotFoundError: File does not exist (only triggers in read mode)

        Returns:
            ARKFile: Underlying file instance allowing for standard file-like object operations.
        """
        if self.closed:
            raise ValueError('Ark file is closed')
        if mode not in ['r', 'w', 'a']:
            raise ValueError('Mode has to be either "r", "w", or "a"')
        if mode in ['w', 'a'] and not self.writable():
            raise ValueError('Cannot write to readonly ark file')

        if isinstance(file, ARKInfo):
            file = posix_path(file.filename)
        elif isinstance(file, ARKMetadata):
            file = file.full_path
        else:
            file = posix_path(file)
        
        if not file:
            raise ValueError("Filename can't be blank")

        if file in self.__file_buffer:
            return self.__file_buffer[file].open(mode)
        
        try:
            file_info = self.getinfo(file)
        except FileNotFoundError:
            file_info = None
        
        if not file_info:
            if mode == 'r':
                raise FileNotFoundError(f'file "{file}" does not exist')
            
            return ARKFile(
                b'',
                ark_instance = self,
                metadata = ARKInfo(file),
                mode = mode,
            )
        
        if mode == 'w':
            data = b''
        else:
            file_metadata = self.__metadata_collection[file_info.filename]
            data = self._get_file_data(file_metadata)
        
        
        return ARKFile(
            data,
            ark_instance = self,
            metadata = file_info,
            mode = mode,
        )
    
    def extract(
        self,
        file: 'str | ARKInfo | ARKMetadata',
        path: str | pathlib.Path | None = None,
        check_hash: bool = True,
        check_timestamp: bool = True,
    ):
        """
        Extract the file to `path`. `path` defaults to the current working
        directory. By default it will also check if there is already an existing
        file, and if there is, then it will check both the timestamp and checksum
        before writing to the file. If the file to extract has a more recent timestamp,
        then it will override the existing file, otherwise it will not do anything.

        Note: this is the fastest way to extract a file.

        Args:
            file (str | ARKInfo | ARKMetadata): File to extract.
            path (str | pathlib.Path | None, optional): Output folder. Defaults to the current working directory (`.`).
            check_hash (bool, optional): Check existing file hash before writing. Defaults to True.
            check_timestamp (bool, optional): Check existing file timestamp. Defaults to True.

        Raises:
            ValueError: Ark file is closed.
        """
        if self.closed:
            raise ValueError('Ark file is closed')
    
        info = self.getinfo(file)
        if isinstance(file, ARKInfo):
            name = file.filename
        elif isinstance(file, ARKMetadata):
            name = file.full_path
        else:
            name = posix_path(file)
        
        if not path:
            path = '.'
        
        path = os.path.abspath(path)
        output = os.path.join(path, name)

        extract = True
        if os.path.exists(output):
            if check_timestamp and info.timestamp:
                existing_timestamp = os.path.getmtime(output)
                if info.timestamp.timestamp() < existing_timestamp:
                    extract = False

            if extract and check_hash:
                if check_hash:
                    with open(output, 'rb') as diskfile:
                        existing_hash = hashlib.md5(diskfile.read()).digest()
                        if existing_hash == info._md5sum:
                            extract = False

        if extract:
            with self.open(file, 'r') as arkfile:
                os.makedirs(os.path.dirname(output), exist_ok = True)
                with open(output, 'wb') as diskfile:
                    # shutil.copyfileobj(arkfile, diskfile)
                    diskfile.write(arkfile.getbuffer())
                
                if info.timestamp is not None:
                    timestamp = int(info.timestamp.timestamp())
                    os.utime(output, times = (timestamp, timestamp))
    
    def read(self, file: 'str | ARKInfo | ARKMetadata') -> bytes:
        """
        Get the bytes for a file.

        Args:
            file (str | ARKInfo | ARKMetadata): File to read.

        Raises:
            ValueError: Ark file is closed

        Returns:
            bytes: File data
        """
        if self.closed:
            raise ValueError('Ark file is closed')
        
        with self.open(file, 'r') as arkfile:
            return arkfile.read()
    
    def write(
        self,
        filename: str,
        arcname: str | None = None,
        use_edit_time: bool = True,
        compressed: bool = True,
        encrypted: bool = False,
    ):
        """
        Write this file to the ark file named `arcname`. `arcname` defaults to
        the base name of `filename` without any directory.

        Args:
            filename (str): Input file to write.
            arcname (str | None, optional): Destination name. Defaults to None.
            use_edit_time (bool, optional): Use the timestamp on the file. If `False`, it will use the current date. Defaults to True.
            compressed (bool, optional): Compress this file. Defaults to True.
            encrypted (bool, optional): Encrypt this file. Defaults to False.

        Raises:
            ValueError: Cannot write to closed file
            ValueError: Cannot write in readonly mode

        """
        if self.closed:
            raise ValueError('Cannot write to closed ark file')
        if not self.writable():
            raise ValueError('Cannot write in readonly mode')
        
        if arcname is None:
            arcname = os.path.basename(filename)
        
        with open(filename, 'rb') as file:
            with self.open(arcname, 'w') as arkfile:
                shutil.copyfileobj(file, arkfile)

                if use_edit_time:
                    arkfile.timestamp = datetime.fromtimestamp(os.path.getmtime(filename))
                
                arkfile.compressed = compressed
                arkfile.encrypted = encrypted
    
    def remove(self, file: 'str | ARKInfo | ARKMetadata'):
        """
        Remove this file from the ark file.

        Args:
            file (str | ARKInfo | ARKMetadata): File to remove

        Raises:
            ValueError: Cannot write to closed file
            ValueError: Cannot write in readonly mode
            FileNotFoundError: File not found
        """
        if self.closed:
            raise ValueError('Cannot write to closed ark file')
        if not self.writable():
            raise ValueError('Cannot write in readonly mode')

        if isinstance(file, ARKInfo):
            file = file.filename
        elif isinstance(file, ARKMetadata):
            file = file.full_path
        else:
            file = posix_path(file)
        
        if file not in self._info_collection:
            raise FileNotFoundError(f'File {file} not found')
        
        self.__removed_files.append(file)
        if file in self.__file_buffer:
            del self.__file_buffer[file]
        del self._info_collection[file]

    def getinfo(self, file: 'str | ARKInfo | ARKMetadata') -> ARKInfo:
        """
        Get the `ARKInfo` object for this file.

        Args:
            file (str | ARKInfo | ARKMetadata): File

        Raises:
            ValueError: Ark file is closed
            FileNotFoundError: File not found

        Returns:
            ARKInfo: File info
        """
        if self.closed:
            raise ValueError('Ark file is closed')
        
        if isinstance(file, ARKInfo):
            return file
        elif isinstance(file, ARKMetadata):
            metadata = file

            timestamp = None

            timestamp = datetime.fromtimestamp(metadata.timestamp)
            
            return ARKInfo(
                _filename = metadata.full_path,
                _timestamp = timestamp,
                _compressed = metadata.compressed_size != metadata.original_filesize,
                _encrypted = metadata.encrypted_size > 0,
                _size = metadata.original_filesize,
                _md5sum = metadata.md5sum,
                _priority = metadata.priority,
                _unknown1 = metadata.unknown1,
                _unknown2 = metadata.unknown2,
            )
        else:
            info = self._info_collection.get(file)
            if not info:
                raise FileNotFoundError(f'File with the name "{file}" does not exist')
            return info
    
    def getmetadata(self, file: 'str | ARKInfo | ARKMetadata') -> 'ARKMetadata':
        """
        Get the `ARKMetadata` instance for this file. Unlike `ARKInfo`, this includes
        the file location, compressed and encrypted sizes.

        Args:
            file (str | ARKInfo | ARKMetadata): File

        Raises:
            ValueError: Ark file is closed
            FileNotFoundError: File not found

        Returns:
            ARKMetadata: File metadata
        """
        if self.closed:
            raise ValueError('Ark file is closed')

        if isinstance(file, ARKMetadata):
            return file
        elif isinstance(file, str):
            if file in self.__metadata_collection:
                return self.__metadata_collection[file]
            elif file in self._info_collection:
                file = self._info_collection[file]
            else:
                raise FileNotFoundError(f'Cannot find file: {file}')
        elif not file.dirty and file.filename in self._info_collection and file.filename in self.__metadata_collection:
            return self.__metadata_collection[file.filename]
        
        timestamp = 0
        if file.timestamp is not None:
            timestamp = int(file.timestamp.timestamp())
        
        return ARKMetadata(
            os.path.basename(file.filename),
            os.path.dirname(file.filename),
            original_filesize = file.size,
            md5sum = file._md5sum,
            priority = file.priority,
            unknown1 = file.unknown1,
            unknown2 = file.unknown2,
            timestamp = timestamp,
        )

    def infolist(self) -> list[ARKInfo]:
        """
        Get a list of `ARKInfo` objects for all files.

        Raises:
            ValueError: Ark file is closed

        Returns:
            list[ARKInfo]: Ark file info.
        """
        if self.closed:
            raise ValueError('Ark file is closed')
        
        return list(self._info_collection.values())
    
    def metadata_list(self) -> 'list[ARKMetadata]':
        """
        Get all the metadata for every file.

        Raises:
            ValueError: Ark file is closed

        Returns:
            list[ARKMetadata]: File metadata
        """
        if self.closed:
            raise ValueError('Ark file is closed')
        
        return [self.getmetadata(info) for info in self._info_collection.values()]

    def namelist(self) -> list[str]:
        if self.closed:
            raise ValueError('Ark file is closed')
        
        return list(self._info_collection.keys())
    
    def testark(self) -> list[str]:
        """
        Read every file and test against the hash. Any files that don't
        match their hash will be returned.

        Raises:
            ValueError: Ark file is closed

        Returns:
            list[str]: Broken files
        """
        if self.closed:
            raise ValueError('Ark file is closed')
        
        errors: list[str] = []
        for info in self.infolist():
            with self.open(info, 'r') as arkfile:
                if info.md5sum != arkfile.md5sum:
                    errors.append(info.filename)
        
        return errors
    
    def test(self) -> bool:
        """
        Test if there are any errors in the ark file, report True if there are none.
        This will open every file and check against its hash.

        Returns:
            bool: Not broken
        """
        return len(self.testark()) == 0
        
    
    def save(self):
        """
        Write the ark file to disk. This starts out by constructing a brand new
        temporary ark file, then it copies it to the original file.

        Raises:
            ValueError: Ark file is closed
            ValueError: Ark file is not writable
        """
        if not self.__file_pointer:
            raise ValueError('File must be open')
        if not self.writable():
            raise ValueError('File is not writable')
        
        filename = os.path.basename(self.filename or '')

        temp_header = self.header.copy()
        temp_header.file_count = len(self._info_collection)
        temp_header.metadata_offset = -1
        temp_header.metadata_length = -1

        new_metadata: list[ARKMetadata] = []
        
        with tempfile.TemporaryFile('w+b', prefix = 'luna-kit-', suffix = f'-{filename}.ark') as temp:
            temp.write(b'\x00' * temp_header.packed_size) # Placeholder bytes
            for info in self._info_collection.values():
                if info.dirty:
                    data, metadata = self.__file_buffer[info.filename].pack()
                    metadata.file_location = temp.tell()
                    temp.write(data)
                else:
                    original_metadata = self.__metadata_collection[info.filename]
                    metadata = original_metadata.copy()
                    metadata.file_location = temp.tell()

                    self.__file_pointer.seek(original_metadata.file_location)
                    size = original_metadata.encrypted_size or original_metadata.compressed_size or original_metadata.original_filesize
                    temp.write(self.__file_pointer.read(size))
                
                new_metadata.append(metadata)
            
            temp_header.metadata_offset = temp.tell()
            packed_metadata = self._write_metadata_block(new_metadata)
            temp_header.metadata_length = len(packed_metadata)
            temp.write(packed_metadata)

            temp.seek(0)

            temp.write(temp_header.pack())

            temp.seek(0)
            self.__file_pointer.seek(0)
            self.__file_pointer.truncate()
            shutil.copyfileobj(temp, self.__file_pointer)
        
        self.header = temp_header
        self.__file_buffer.clear()
        self.__removed_files.clear()
        self._info_collection.clear()
        self.__metadata_collection._clear()
        for metadata in new_metadata:
            self.__metadata_collection._add_metadata(metadata, raw = True)
            self._info_collection[metadata.full_path] = self.getinfo(metadata)


    def close(
        self,
        /,
        exc_type = None,
        exc_val = None,
        exc_traceback = None,
    ):
        """
        Close this ark file, write if in write mode and there are any changes
        """
        if self.__file_ctx:
            if self.writable() and self.dirty:
                self.save()
            
            self.__file_pointer = None
            self.__file_ctx.__exit__(exc_type, exc_val, exc_traceback)
            self.__file_ctx = None

    @property
    def dirty(self) -> bool:
        """
        Check if there are any changes present in this ark file.

        Returns:
            bool: There are changes that need to be written
        """
        return len(self.__file_buffer) > 0 or len(self.__removed_files) > 0

    def writable(self) -> bool:
        """
        Check if this file is writable

        Returns:
            bool
        """
        return self.__file_pointer is not None and self.mode in ['w', 'a']
    
    @property
    def closed(self) -> bool:
        return self.__file_pointer is None or self.__file_pointer.closed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_traceback):
        self.close(
            exc_type = exc_type,
            exc_val = exc_val,
            exc_traceback = exc_traceback,
        )


class ARKFile(io.BufferedIOBase):
    _ark: ARK
    _info: ARKInfo
    _mode: Literal['r', 'w', 'a']
    _open: bool
    
    def __init__(
        self,
        initial_data: bytes,
        ark_instance: ARK,
        metadata: ARKInfo,
        mode: Literal['r', 'w', 'a'] = 'r',
    ):
        if mode not in ['r', 'w', 'a']:
            raise ValueError('Mode has to be either "r", "w", "a"')
        
        if mode in ['w', 'a'] and not ark_instance.writable():
            raise ValueError('Cannot write to file in readonly ARK file')

        if mode == 'w':
            initial_data = b''
    
        self._buffer = io.BytesIO(initial_data)
        self._ark = ark_instance
        self._info = metadata
        self._open = False
        self.open(mode = mode)
    
    @property
    def mode(self) -> str:
        if self._mode == 'a':
            mode = 'r+'
        elif self._mode == 'w':
            mode = 'w+'
        else:
            mode = 'r'
        return mode + 'b'
    
    def open(self, mode: Literal['r', 'w', 'a'] = 'r') -> Self:
        if self._open:
            raise ValueError('ARKFile already open')
        
        if mode not in ['r', 'w', 'a']:
            raise ValueError('Mode has to be either "r", "w", "a"')
        
        if mode in ['w', 'a'] and not self._ark.writable():
            raise ValueError('Cannot write to file in readonly ARK file')
        
        self._mode = mode
        
        self._open = True
        if mode == 'w':
            self.seek(0)
            self.truncate()
        elif mode == 'a':
            self.seek(0, os.SEEK_END)
        else:
            self.seek(0)

        return self
    
    def readable(self) -> bool:
        """
        Return whether object was opened for reading.

        If False, read() will raise io.UnsupportedOperation.
        """
        return self._open

    def writable(self) -> bool:
        """
        Return whether object was opened for writing.

        If False, write() will raise io.UnsupportedOperation.
        """
        return self._open and self._ark.writable() and self._mode in ['w', 'a']
    
    def _check_open(self):
        if not self._open:
            raise ValueError('I/O operation on closed file.')

    def _check_readable(self):
        if not self.readable():
            raise io.UnsupportedOperation("Not readable")
    
    def _check_writable(self):
        if not self.writable():
            raise io.UnsupportedOperation("Not writable")
    
    def seek(self, offset: int, whence: int = os.SEEK_SET, /) -> int:
        self._check_open()
        return self._buffer.seek(offset, whence)
    
    def tell(self) -> int:
        self._check_open()
        return self._buffer.tell()

    def read(self, size: int | None = -1, /) -> bytes:
        self._check_open()
        self._check_readable()
        return self._buffer.read(size)
    
    def readline(self, size: int | None = -1, /) -> bytes:
        self._check_open()
        self._check_readable()
        return self._buffer.readline(size)

    def readlines(self, size: int = -1, /) -> list[bytes]:
        self._check_open()
        self._check_readable()
        return self._buffer.readlines(size)
    
    def write(self, buffer: 'Buffer', /) -> int:
        self._check_open()
        self._check_writable()
        return self._buffer.write(buffer)

    def writelines(self, lines: Iterable['Buffer'], /) -> None:
        self._check_open()
        self._check_writable()
        return self._buffer.writelines(lines)
    
    def truncate(self, size: int | None = None, /) -> int:
        self._check_open()
        self._check_writable()
        return self._buffer.truncate(size)
    
    def getbuffer(self):
        self._check_open()
        self._check_readable()
        return self._buffer.getbuffer()
    
    def __next__(self) -> bytes:
        self._check_open()
        self._check_readable()
        return self._buffer.__next__()
    
    def __iter__(self) -> Iterator[bytes]:
        self._check_open()
        self._check_readable()
        return self._buffer.__iter__()
    
    def flush(self) -> None:
        self._check_open()
        if not self.writable():
            return
        
        self._buffer.flush()
        self._info._size = self.size
        self._info._md5sum = hashlib.md5(self._buffer.getvalue()).digest()

        self._ark._buffer_file(self)
    
    def close(self) -> None:
        if not self._open:
            return
        
        if self.writable():
            self.flush()
        self._open = False
    
    def pack(self) -> tuple[bytes, ARKMetadata]:
        """
        Write this file to the bytes to be used inside ark files.
        This returns a tuple with the first value being the
        compressed/encrypted bytes, and the second being the
        `ARKMetadata` instance that includes metadata for the compression/encryption

        Raises:
            BadARKFile: Unknown file version

        Returns:
            tuple[bytes, ARKMetadata]: Final bytes and metadata.
        """
        self.close()
        metadata = self._ark.getmetadata(self._info)
        result = self._buffer.getvalue()
        metadata.original_filesize = len(result)

        if self.compressed:
            if self._ark.header.version == 1:
                result = zlib.compress(result)
            elif self._ark.header.version in [3,4]:
                result = zstandard.compress(result)
            else:
                raise BadARKFile(f'Unknown file version: {self._ark.header.version}')
        
        metadata.compressed_size = len(result)

        if self.encrypted:
            result = xxtea.encrypt(result, self._ark.KEY)
            metadata.encrypted_size = len(result)
        
        return result, metadata

    
    @property
    def closed(self) -> bool:
        return not self._open

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    @property
    def filename(self) -> str:
        """
        The filename of the file

        Returns: str
        """
        self.compressed
        return self._info.filename
    
    @property
    def compressed(self) -> bool:
        """
        Whether or not this file is compressed. Can be modified.

        Returns: bool
        """
        return self._info.compressed
    @compressed.setter
    def compressed(self, value: bool):
        self._check_open()
        self._check_writable()
        self._info._compressed = value
    
    @property
    def encrypted(self) -> bool:
        """
        Whether or not this file is encrypted. Can be modified.

        Returns: bool
        """
        return self._info.encrypted
    @encrypted.setter
    def encrypted(self, value: bool):
        self._check_open()
        self._check_writable()
        self._info._encrypted = value
    
    @property
    def priority(self) -> int:
        """
        The priority of this file. Can be modified.

        Returns: int
        """
        return self._info.priority
    @priority.setter
    def priority(self, value: int):
        self._check_open()
        self._check_writable()
        self._info._priority = value
    
    @property
    def timestamp(self) -> datetime | None:
        """
        The timestamp for this file. Can be modified.

        Returns: datetime | None
        """
        return self._info.timestamp
    @timestamp.setter
    def timestamp(self, value: datetime | None):
        self._check_open()
        self._check_writable()
        self._info._timestamp = value

    @property
    def size(self) -> int:
        """
        Get the filesize

        Returns:
            int: File size
        """
        pos = self._buffer.tell()
        self._buffer.seek(0, os.SEEK_END)
        size = self._buffer.tell()
        self._buffer.seek(pos)
        return size
    
    def __len__(self) -> int:
        """File size"""
        return self.size
    
    @property
    def md5sum(self) -> str:
        """md5 checksum of this file"""
        return hashlib.md5(self._buffer.getvalue()).hexdigest()

class ARKMetadataCollection:
    _metadata_list: list[ARKMetadata]
    _metadata_dict: dict[str, ARKMetadata]
    
    def __init__(self):
        self._metadata_list = []
        self._metadata_dict = {}

    def __getitem__(self, key: int | str) -> ARKMetadata:
        if isinstance(key, str):
            key = posix_path(key)
            return self._metadata_dict[key]
        
        return self._metadata_list[key]
    
    T = TypeVar('T')
    def get(self, key: int | str, default: T = None) -> ARKMetadata | T:
        try:
            return self.__getitem__(key)
        except KeyError:
            return default


    def __iter__(self) -> Iterator[ARKMetadata]:
        return self._metadata_list.__iter__()

    def __len__(self) -> int:
        return self._metadata_list.__len__()

    def __contains__(self, key: str | ARKMetadata) -> bool:
        if isinstance(key, ARKMetadata):
            return key in self._metadata_list
        
        key = posix_path(key)

        return key in self._metadata_dict
    
    def index(
        self,
        value: str | ARKMetadata,
        start: int = 0,
        stop: int = sys.maxsize,
        /
    ) -> int | None:
        if isinstance(value, str):
            value = posix_path(value)
        else:
            value = value.full_path
        
        value = self._metadata_dict[value]
        return self._metadata_list.index(value, start, stop)

    def _add_metadata(self, metadata: ARKMetadata, raw: bool = True):
        if not isinstance(metadata, ARKMetadata):
            raise TypeError(f'Wrong type: {type(metadata).__name__}')

        if raw:
            self._metadata_list.append(metadata)
            self._metadata_dict[metadata.full_path] = metadata
            return
        
        existing_index = self.index(metadata.full_path)

        if existing_index is None:
            self._metadata_list.append(metadata)
        else:
            self._metadata_list[existing_index] = metadata
        
        self._metadata_dict[metadata.full_path] = metadata

        self._sort_collection()


    def _sort_collection(self):
        self._metadata_list.sort(key = lambda item: item.file_location)
    
    def _clear(self):
        self._metadata_list.clear()
