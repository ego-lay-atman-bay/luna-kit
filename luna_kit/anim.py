import csv
import dataclasses
import os
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated, BinaryIO, Literal
import csv

import dataclasses_struct as dcs
import numpy
import PIL.Image

from . import enums
from .file_utils import PathOrBinaryFile, open_binary
from .pvr import PVR
from .utils import (increment_name_num, read_ascii_string, strToBool,
                    strToFloat, strToInt)

@dcs.dataclass()
class Header:
    magic: Annotated[bytes, 8] = b'RKFORMAT'
    version_major: dcs.U32 = 5
    version_minor: dcs.U32 = 2
    name: Annotated[bytes, 64] = b' ' * 64
    bone_count: dcs.U32 = 0
    frame_count: dcs.U32 = 0
    unknown: dcs.U32 = 4

@dataclass
class Animation:
    name: str
    start: int
    end: int
    fps: float

@dataclass
class BoneTransformation:
    position: tuple[float, float, float]
    scale: int
    rotation: tuple[float, float, float, float]
    
    FORMAT: str = '3h1B4b'

class Anim:
    MAGIC: bytes = b'RKFORMAT'
    
    def __init__(self, file: PathOrBinaryFile | None = None):
        self.filename = ''
        self.header = Header()
        self.name = ''
        self.animations: dict[str, Animation] = {}
        self.frames: list[list[BoneTransformation]] = []
        
        if file is not None:
            self.read(file)
        
    def read(self, file: PathOrBinaryFile):
        self.filename = ''
        if isinstance(file, str) and os.path.exists(file):
            self.filename = os.path.abspath(file)
        with open_binary(file) as open_file:
            self.header = self._read_header(open_file)
            self.frames = self._read_frames(open_file)
            self.animations = self._get_animation_list()
        
    def _read_header(self, file: BinaryIO):
        header: Header = Header.from_packed(
            file.read(dcs.get_struct_size(Header))
        )
        
        assert header.magic == self.MAGIC, 'file is not .anim file'

        self.name = read_ascii_string(header.name)
        
        return header
    
    def _get_animation_list(self):
        if self.filename:
            csv_name = os.path.join(os.path.dirname(self.filename), self.name + '.csv')
            if os.path.isfile(csv_name):
                with open(csv_name, 'r', newline = '') as csvfile:
                    reader = csv.DictReader(csvfile, ['name', 'start', 'end', 'fps'])
                    animation_list = {
                        row['name']: Animation(
                            row['name'],
                            strToInt(row['start']),
                            strToInt(row['end']),
                            strToFloat(row['fps']),
                        ) for row in reader
                    }
                
                return animation_list
            else:
                print(f'could not find {os.path.basename(csv_name)}')
                
        return {}
    
    def _read_frames(self, file: BinaryIO):
        frames = []
        for frame_index in range(self.header.frame_count):
            frames.append([self._read_bone_transformation(file) for _ in range(self.header.bone_count)])
        
        return frames
    
    def _read_bone_transformation(self, file: BinaryIO):
        frame_data = struct.unpack(
            BoneTransformation.FORMAT,
            file.read(struct.calcsize(BoneTransformation.FORMAT)),
        )
        
        return BoneTransformation(
            frame_data[0:3],
            frame_data[3],
            frame_data[4:8],
        )

