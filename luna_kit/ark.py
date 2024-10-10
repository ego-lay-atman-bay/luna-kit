import contextlib
import hashlib
import io
import os
import warnings
from ctypes import *
from typing import IO, BinaryIO, Literal

from rich.progress import Progress, track
import zstandard

from . import enums, tea, types
from .console import console
from .utils import is_binary_file, is_text_file, posix_path, trailing_slash

FILE_METADATA_MAP = {
    "filename": 128,
    "pathname": 128,
    "file_location": 4,
    "original_filesize": 4,
    "compressed_size": 4,
    "encrypted_nbytes": 4,
    "timestamp": 4,
    "md5sum": 16,
    "priority": 4,
}

def read_bytes(b: bytes | bytearray, order: Literal[enums.ENDIAN.BIG, enums.ENDIAN.LITTLE] = enums.ENDIAN.BIG):
    if order == enums.ENDIAN.LITTLE:
        b = bytearray(b)
        b.reverse()

    return bytes(b)

class ARK():
    KEY = [0x3d5b2a34, 0x923fff10, 0x00e346a4, 0x0c74902b]
    
    HEADER_MAP = {
        "file_count": 4,
        "metadata_offset": 4,
        "ark_version": 4,
    }
    
    header: types.Header
    metadata: list[types.FileMetadata]
    _decompresser = zstandard.ZstdDecompressor()
    
    def __init__(
        self,
        file: str | bytes | bytearray | BinaryIO | None = None,
        output: str | None = None,
    ) -> None:
        """Extract `.ark` files.

        Args:
            file (str | bytes | bytearray | BinaryIO | None, optional): Input file. Defaults to None.
            output (str | None, optional): Optional output folder to extract files to. Defaults to None.
        """
        self.files: list[ARKFile] = []
        self.header = {
            "file_count": 0,
            "metadata_offset": 0,
            "ark_version": 0,
        }
        
        if file != None:
            self.read(file, output)
    
    def read(
        self,
        file: str | bytes | bytearray | BinaryIO,
        output: str | None = None,
    ):
        """Extract `.ark` files.

        Args:
            file (str | bytes | bytearray | BinaryIO | None, optional): Input file.
            output (str | None, optional): Optional output folder to extract files to. Defaults to None.

        Raises:
            TypeError: file must be open in binary mode
            TypeError: cannot open file
        """
        if isinstance(file, str) and os.path.isfile(file):
            context_manager = open(file, 'rb')
        elif isinstance(file, (bytes, bytearray)):
            context_manager = io.BytesIO(file)
        elif is_binary_file(file):
            context_manager = contextlib.nullcontext(file)
        elif is_text_file(file):
            raise TypeError('file must be open in binary mode')
        else:
            raise TypeError('cannot open file')
        
        with context_manager as open_file:
            open_file.seek(0)
            
            self.header = self.read_header(open_file)
            assert self.header['ark_version'] == 3

            self.metadata = self.get_metadata(open_file)
            # print(self.metadata)
            
            for file_metadata in track(
                self.metadata,
                console = console,
                description = 'Extracting...',
            ):
                filename = posix_path(os.path.join(file_metadata['pathname'], file_metadata['filename']))
                console.print(f'extracting [yellow]{filename}[/yellow]')
                ark_file = ARKFile(
                    os.path.join(file_metadata['pathname'], file_metadata['filename']),
                    self.get_file_data(file_metadata, open_file),
                )
                self.files.append(ark_file)
                
                if output:
                    ark_file.save(os.path.join(output, ark_file.fullpath))
    
    def read_header(self, file: IO) -> types.Header:
        """Read the header of a `.ark` file.

        Args:
            file (IO): File-like object.

        Returns:
            dict: Header.
        """
        header = {}
        
        for key, length in self.HEADER_MAP.items():
            header[key] = int.from_bytes(file.read(length), 'little')
        
        return header

    def get_metadata(self, file: IO) -> None | list[types.FileMetadata]:
        filesize: int = None
        
        file.seek(0, os.SEEK_END)
        
        filesize = file.tell()
        # print(filesize)
        
        if filesize < 0:
            raise TypeError('file size is negative, somehow...')
        
        metadata_size = tea.get_phdr_size(filesize - self.header['metadata_offset'])
        # print(f'metadata size: {metadata_size}')
        raw_metadata_size = self.header["file_count"] * sum(FILE_METADATA_MAP.values())
        # print(f'raw metadata size: {raw_metadata_size}')
        
        file.seek(self.header["metadata_offset"], os.SEEK_SET)
        
        metadata = file.read(metadata_size)
        
        # print(f'metadata: {int.from_bytes(metadata, 'little')}')
        metadata = tea.decrypt(metadata, metadata_size // 4, self.KEY)
        
        raw_metadata = self._decompresser.decompress(metadata, raw_metadata_size)

        header_size = sum(FILE_METADATA_MAP.values())
        result = []
        for file_index in range(self.header["file_count"]):
            file_result = {}
            
            offset = file_index * header_size
            
            pos = 0
            
            for key, length in FILE_METADATA_MAP.items():
                file_result[key] = raw_metadata[offset + pos:offset + pos + length]

                pos += length
            
            result.append(file_result)

        return self.fix_metadata(result)
    
    def fix_metadata(self, metadata: list[types.RawFileMetadata]):
        fixed_metadata: list[types.FileMetadata] = []

        for file in metadata:
            fixed_file: types.FileMetadata = {}

            fixed_file['filename'] = file['filename'].decode('ascii').rstrip('\x00')
            fixed_file['pathname'] = file['pathname'].decode('ascii').rstrip('\x00')
            fixed_file["file_location"] = int.from_bytes(file["file_location"], 'little')
            fixed_file['original_filesize'] = int.from_bytes(file['original_filesize'], 'little')
            fixed_file['compressed_size'] = int.from_bytes(file['compressed_size'], 'little')
            fixed_file['encrypted_nbytes'] = int.from_bytes(file['encrypted_nbytes'], 'little')
            fixed_file['timestamp'] = int.from_bytes(file['timestamp'], 'little')
            fixed_file['md5sum'] = file['md5sum'].hex()
            fixed_file['priority'] = int.from_bytes(file['priority'], 'little')

            fixed_metadata.append(fixed_file)
        
        return fixed_metadata
            

    def get_file_data(self, metadata: types.FileMetadata, file: IO):
        file.seek(metadata['file_location'], os.SEEK_SET)
        
        file_data = file.read(metadata['encrypted_nbytes'] if metadata['encrypted_nbytes'] else metadata['compressed_size'])

        if (metadata['encrypted_nbytes']) != 0:
            file_data = tea.decrypt(file_data, metadata['encrypted_nbytes'] // 4, self.KEY)
        
        if (metadata['compressed_size'] != metadata['original_filesize']):
            file_data = self._decompresser.decompress(file_data, metadata['original_filesize'])
        
        if hashlib.md5(file_data).hexdigest() != metadata['md5sum']:
            warnings.warn(f'file "{posix_path(os.path.join(metadata['pathname'], metadata['filename']))}" hash does not match "{metadata['md5sum']}"')
        
        return file_data
        
class ARKFile():
    def __init__(self, filename: str, data: bytes) -> None:
        """File inside `.ark` file.

        Args:
            filename (str): The filename to be used inside the `.ark` file.
            data (bytes): File data.
        """
        self.fullpath = str(filename)
        self.data: bytes = bytes(data)
    
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
