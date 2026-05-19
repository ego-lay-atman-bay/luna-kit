from typing import TypedDict, Literal, NotRequired

class DLCItem(TypedDict):
    asset_hash: str
    asset_key: str
    asset_ver: str
    device_calibre: Literal['all', 'low', 'high', 'veryhigh']
    enabled: bool
    filename: str
    hotloadable: bool
    original_hash: NotRequired[str]
    original_size: NotRequired[int]
    platform: str
    required_ver: str
    size: int
    tag: str

class DLCManifest(TypedDict):
    build_version: str
    dlc_items: list[DLCItem]
    file_revision: int
    format_version: int
    last_updated: str
    last_updated_by: str
    timestamp: int
