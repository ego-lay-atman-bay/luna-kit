from typing import TypedDict

class Header(TypedDict):
    file_count: int
    metadata_offset: int
    ark_version: int

class RawFileMetadata(TypedDict):
    filename: bytes
    pathname: bytes
    file_location: bytes
    original_filesize: bytes
    compressed_size: bytes
    encrypted_nbytes: bytes
    timestamp: bytes
    md5sum: bytes
    priority: bytes
    
class FileMetadata(TypedDict):
    filename: str
    pathname: str
    file_location: int
    original_filesize: int
    compressed_size: int
    encrypted_nbytes: int
    timestamp: int
    md5sum: str
    priority: int
