import os
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated, BinaryIO

import dataclasses_struct as dcs
import numpy

from . import enums
from .file_utils import PathOrBinaryFile, open_binary
from .pvr import PVR


@dcs.dataclass()
class Header():
    magic: Annotated[bytes, 8] = b'RKFORMAT'
    unknown1: dcs.U32 = 0
    unknown2: dcs.U32 = 0
    name: Annotated[bytes, 64] = b' ' * 64

def read_ascii_string(file: BinaryIO | bytes, length: int = 64) -> str:
    if isinstance(file, (bytes, bytearray)):
        data = file
    else:
        data = file.read(length)
    
    return data.split(b'\x00')[0].decode('ascii', errors='ignore')

class RKFormat():
    MAGIC = b'RKFORMAT'
    
    header: Header
    info: Mapping[enums.rk.Info, tuple[int, int, int]]

    
    def __init__(self, file: PathOrBinaryFile = None) -> None:
        self.filename = ''

        self.header = Header()
        self.name = ''
        self.info = {}
        self.materials = []
        self.bones = []
        self.textures = {}
        self.attributes = []
        self.submesh_info = []
        self.verts = []
        
        if file is not None:
            self.read(file)
    
    def read(self, file: PathOrBinaryFile):
        self.filename = ''

        self.header = Header()
        self.name = ''
        self.info = {}
        self.materials = []
        self.bones = []
        self.textures = {}
        self.attributes = []
        self.submesh_info = []
        self.verts = []
        
        with open_binary(file) as open_file:
            if isinstance(file, str):
                self.filename = file
            
            self.header = self._read_header(open_file)
            self.info = self._read_info(open_file)
            self.textures = self._read_textures(open_file)
            self.attributes = self._read_attributes(open_file)
            self.submesh_info = self._read_submesh_info(open_file)
            self.verts = self._read_verts(open_file)
            self.bones = self._read_bones(open_file)
    
    def _read_header(self, file: BinaryIO):
        header: Header = Header.from_packed(
            file.read(dcs.get_struct_size(Header))
        )
        
        assert header.magic == self.MAGIC, 'file is not .rk file'
        
        return header
    
    def _read_info(self, file: BinaryIO):
        info: Mapping[enums.rk.Info, tuple[int,int,int]] = {}
        size = 24 * 16
        
        for i in struct.iter_unpack(
            '4I',
            file.read(size),
        ):
            if i[0]:
                info[i[0]] = i[1:]
        
        return info

    def _read_textures(self, file: BinaryIO):
        texture_info = self.info.get(enums.rk.Info.TEXTURES)
        if texture_info == None:
            return {}
        
        file.seek(texture_info[0])

        textures = {}
        
        for x in range(texture_info[1]):
            name = read_ascii_string(file)
            textures[name] = PVR(
                os.path.join(
                    os.path.dirname(self.filename),
                    name + '.pvr',
                )
            )
        
        return textures

    def _read_attributes(self, file: BinaryIO):
        attributes_info = self.info.get(enums.rk.Info.ATTRIBUTES)
        if attributes_info == None:
            return []
        
        attributes = []
        
        format_str = 'H2B'
        
        uo, ufmt = -1, -1
        file.seek(attributes_info[0])
        for x in range(attributes_info[1]):
            i = struct.unpack(
                format_str,
                file.read(struct.calcsize(format_str)),
            )
            if i[0] == 1030:
                uo, ufmt = i[1], 'ushort'
                
            elif i[0] == 1026:
                uo, ufmt = i[1], 'float'
            
            attributes.append(i)
        
        return attributes

    def _read_submesh_info(self, file: BinaryIO):
        submesh_names_info = self.info.get(enums.rk.Info.SUBMESH_NAMES)
        if submesh_names_info == None:
            return {}
        
        submesh_info_info = self.info.get(enums.rk.Info.SUBMESH_NAMES)
        if submesh_info_info == None:
            return {}
        
        file.seek(submesh_names_info[0])
        submesh_names = []
        for x in range(submesh_names_info[1]):
            name = read_ascii_string(file)
            submesh_names.append(name)
        
        file.seek(submesh_info_info[0])
        submesh_info = []
        for x in range(submesh_info_info[1]):
            info = struct.unpack(
                '4I',
                file.read(struct.calcsize('4I')),
            )
            submesh_info.append(info)
        
        return {name: info for name, info in zip(submesh_names, submesh_info)}
    
    def _read_verts(self, file: BinaryIO) -> list[tuple[float,float,float,float]]:
        
        verts_info = self.info.get(enums.rk.Info.VERTS)
        if verts_info == None:
            return []
        
        file.seek(verts_info[0])
        

        stride = verts_info[2] // verts_info[1]
        vbuf = file.read(verts_info[2])
        
        verts = []
        
        verts = [vert for vert in struct.iter_unpack(
            '4f',
            vbuf,
        )]
        
        return verts

    def _read_bones(self, file: BinaryIO):
        
        bones_info = self.info.get(enums.rk.Info.BONES)
        if bones_info == None:
            return []
        
        bones = []
        
        bone_format = '3i64s64s'
        
        if bones_info[1]:
            file.seek(bones_info[0])
            for parent, index, child, matrix, name in struct.iter_unpack(
                bone_format,
                file.read(bones_info[1] * struct.calcsize(
                    bone_format
                )),
            ):
                bones.append(Bone(
                    parentIndex = parent,
                    index = index,
                    child = child,
                    matrix = numpy.frombuffer(matrix, dtype = numpy.uint32).reshape((4,4))[:3],
                    name = read_ascii_string(name),
                ))
        
        
        
        return bones
            

@dataclass
class Bone:
    
    index: int
    child: int
    name: str
    matrix: numpy.ndarray
    parentName: str | None = None,
    parentIndex: int = -1
