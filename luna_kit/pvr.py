import os
import struct
import warnings
from typing import Annotated, BinaryIO

try:
    import dataclasses_struct as dcs
    import texture2ddecoder
    from PIL import Image
except ImportError as e:
    e.add_note('pvr dependencies not found')
    raise e

from .file_utils import PathOrBinaryFile, open_binary
from .utils import put_alpha, image_has_alpha


@dcs.dataclass()
class Header:
    magic: Annotated[bytes, 4] = b'PVR\x03'
    flags: dcs.U32 = 0
    format: Annotated[bytes, 4] = b'\x00' * 4
    channel_bit_rates: Annotated[bytes, 4] = b'\x00' * 4
    color_space: dcs.U32 = 0
    channel_type: dcs.U32 = 0
    height: dcs.U32 = 0
    width: dcs.U32 = 0
    depth: dcs.U32 = 0
    num_surfaces: dcs.U32 = 0
    num_faces: dcs.U32 = 0
    mip_map_count: dcs.U32 = 0
    metadata_size: dcs.U32 = 0

@dcs.dataclass()
class MetadataHeader:
    fourCC: Annotated[bytes, 4] = b'PVR0'
    key: dcs.U32 = 0
    data_size: dcs.U32 = 0

class PVR:
    MAGIC: bytes = b'PVR\x03'
    
    def __init__(
        self,
        file: PathOrBinaryFile | None = None,
        external_alpha: bool = True,
    ) -> None:
        self.header: Header = Header()
        self.external_alpha = external_alpha
        self.filename: str = ''
        self.alpha_filename: str = ''
        self.metadata_header: MetadataHeader = MetadataHeader()
        self.metadata = {}
        self.metadata_block = b''
        
        self.image: Image.Image | None = None

        if file is not None:
            self.read(file)
    
    @property
    def premultiplied(self):
        return self.header.flags == 2
    
    @property
    def width(self):
        if self.image is None:
            return self.header.width
        return self.image.width
    
    @property
    def height(self):
        if self.image is None:
            return self.header.height
        return self.image.height
    
    def read(self, file: PathOrBinaryFile):
        self.header = Header()
        self.filename = ''
        self.alpha_filename: str = ''
        self.metadata_header = MetadataHeader()
        self.metadata = {}
        self.metadata_block = b''
        
        self.image = None
        
        with open_binary(file) as open_file:
            if isinstance(file, str):
                self.filename = file
                if self.external_alpha:
                    split_filename = os.path.splitext(file)
                    alpha_filename = f'{split_filename[0]}.alpha{split_filename[1]}'
                    if os.path.isfile(alpha_filename):
                        self.alpha_filename = alpha_filename
            
            self.header = self._read_header(open_file)
            self._read_metadata(open_file)
            self.image = self._read_image(open_file)
        
        if self.alpha_filename and not image_has_alpha(self.image):
            alpha = PVR(self.alpha_filename)
            if alpha.image.size == self.image.size:
                self.image = put_alpha(self.image, alpha.image)
    
    def _read_header(self, file: BinaryIO):
        header: Header = Header.from_packed(
            file.read(dcs.get_struct_size(Header))
        )
        
        assert header.magic == self.MAGIC, 'this is not a pvr file'
        
        return header
    
    def _read_metadata(self, file: BinaryIO):
        if self.header.metadata_size == 0:
            return
        
        self.metadata_header = MetadataHeader.from_packed(
            file.read(dcs.get_struct_size(MetadataHeader))
        )
        
        self.metadata_block = file.read(self.metadata_header.data_size)
        
        if self.metadata_header.fourCC == b'PVR\x03':
            match self.metadata_header.key:
                case 3:
                    self.metadata = {k:v for k,v in zip(['x', 'y', 'z'], struct.unpack('3?', self.metadata_block))}
                case _:
                    warnings.warn(f'metadata key "{self.metadata_header.key}" not recognized')
        else:
            warnings.warn(f'metadata identifier "{self.metadata_header.fourCC}" not recognized')
        
        
    
    def _read_image(self, file: BinaryIO):
        image = None
        
        file.seek(dcs.get_struct_size(Header) + self.header.metadata_size)
        self.image_data = file.read()

        # texture2ddecoder: https://github.com/K0lb3/texture2ddecoder?tab=readme-ov-file#functions
        # pvr formats: https://docs.imgtec.com/specifications/pvr-file-format-specification/html/topics/pvr-header-format.html#pixel-format-unsigned-64-bit-integer

        channel_bit_rates = struct.unpack('4B', self.header.channel_bit_rates)

        if sum(channel_bit_rates) > 0:
            channel_order = tuple(c.decode() for c in struct.unpack('4c', self.header.format))
            if channel_order == ('r', 'g', 'b', 'a') and channel_bit_rates == (8,8,8,8):
                image = Image.frombytes(
                    'RGBA',
                    (self.header.width, self.header.height),
                    self.image_data,
                    'raw',
                    'RGBA',
                )
            else:
                
                raise NotImplementedError(f'format is not supported {"".join(channel_order)}{"".join([str(c) for c in channel_bit_rates])}')
        else:
            format = struct.unpack('I', self.header.format)[0]
            
            match format:
                case 34:
                    decoded_bytes = texture2ddecoder.decode_astc(
                        self.image_data,
                        self.header.width,
                        self.header.height,
                        8, 8,
                    )
                    image = Image.frombytes(
                        "RGBA",
                        (self.header.width, self.header.height),
                        decoded_bytes,
                        "raw",
                        ('BGRA'),
                    )
                case 6:
                    decoded_bytes = texture2ddecoder.decode_etc1(
                        self.image_data,
                        self.header.width,
                        self.header.height,
                    )
                    image = Image.frombytes(
                        "RGBA",
                        (self.header.width, self.header.height),
                        decoded_bytes,
                        "raw",
                        ('BGRA'),
                    )
                case _:
                    raise NotImplementedError(f'Format {self.header.format} not implemented')
        
        return image
    
    def save(self, *args, **kwargs):
        """Calls `self.image.save`. All arguments are passed into the PIL.Image.Image.save method.
        
        Args:
            All arguments are the same as `PIL.Image.Image.save`
        """
        return self.image.save(*args, **kwargs)
    
    def show(self, title: str | None = None):
        """Shows image using `self.image.show()`

        Displays this image. This method is mainly intended for debugging purposes.

        This method calls PIL.ImageShow.show internally. You can use
        PIL.ImageShow.register to override its default behaviour.

        The image is first saved to a temporary file. By default, it will be in PNG format.

        On Unix, the image is then opened using the **xdg-open**, **display**, **gm**, **eog** or **xv** utility, depending on which one can be found.

        On macOS, the image is opened with the native Preview application.

        On Windows, the image is opened with the standard PNG display utility.

        Args:
            title (str, optional): Optional title to use for the image window, where possible.
        """
        return self.image.show(title)
