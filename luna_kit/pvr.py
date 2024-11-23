from typing import BinaryIO, Annotated

import astc_encoder.pil_codec
import dataclasses_struct as dcs
from PIL import Image

from .file_utils import PathOrBinaryFile, open_binary

@dcs.dataclass()
class Header:
    magic: Annotated[bytes, 4] = b'PVR\x03'
    unknown1: dcs.U32 = 0
    format: dcs.U32 = 0
    unknown2: dcs.U32 = 0
    unknown3: dcs.U32 = 0
    unknown4: dcs.U32 = 0
    width: dcs.U32 = 0
    height: dcs.U32 = 0

class PVR:
    MAGIC: bytes = b'PVR\x03'
    
    def __init__(self, file: PathOrBinaryFile | None = None) -> None:
        self.header = Header()
        self.filename = ''
        
        self.image: Image.Image | None = None

        if file is not None:
            self.read(file)
    
    def read(self, file: PathOrBinaryFile):
        self.header = Header()
        self.filename = ''
        
        self.image = None
        
        with open_binary(file) as open_file:
            if isinstance(file, str):
                self.filename = file
            
            self.header = self._read_header(open_file)

            self.image = self._read_image(open_file)
    
    def _read_header(self, file: BinaryIO):
        header: Header = Header.from_packed(
            file.read(dcs.get_struct_size(Header))
        )
        
        assert header.magic == self.MAGIC, 'this is not a pvr file'
        
        return header
    
    def _read_image(self, file: BinaryIO):
        image = None
        
        if self.header.format == 34:
            file.seek(67)
            image = Image.frombytes(
                "RGBA",
                (self.header.width, self.header.height),
                file.read(),
                "astc",
                (1, 8, 8),
            )
        elif self.header.format == 6:
            raise NotImplemented('ETC format is not implemented yet')
        else:
            raise NotImplemented(f'Format {self.header.format} not implemented')
        
        return image
