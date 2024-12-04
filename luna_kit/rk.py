import csv
import os
import struct
from collections.abc import Mapping
import dataclasses
from dataclasses import dataclass
from typing import Annotated, BinaryIO, Literal

import dataclasses_struct as dcs
import numpy

from . import enums
from .file_utils import PathOrBinaryFile, open_binary
from .pvr import PVR
from .utils import strToBool, strToInt, strToFloat

USHORT_MAX = 65535


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

def parse_rkm(filename: str):
    with open(filename, 'r', newline = '') as file:
        data = [row for row in csv.reader(file, delimiter='=') if len(row)]
    
    return RKM(**dict(data))

class RKFormat():
    MAGIC = b'RKFORMAT'
    
    header: Header
    info: Mapping[enums.rk.Info, tuple[int, int, int]]

    
    def __init__(self, file: PathOrBinaryFile = None) -> None:
        self.filename = ''

        self.header = Header()
        self.name = ''
        self.info: Mapping[enums.rk.Info, tuple[int, int, int]] = {}
        self.materials: list[Material] = []
        self.bones: list[Bone] = []
        self.materials: list[Material] = []
        self.attributes: list[tuple[int, int, int]] = []
        self.submeshes: list[Submesh] = []
        self.verts: list[Vert] = []
        self.meshes: list[Mesh] = []
        
        if file is not None:
            self.read(file)
    
    def read(self, file: PathOrBinaryFile):
        self.filename = ''

        self.header = Header()
        self.name = ''
        self.info = {}
        self.materials = []
        self.bones = []
        self.materials = []
        self.attributes = []
        self.submeshes = []
        self.verts = []
        self.meshes = []
        
        with open_binary(file) as open_file:
            if isinstance(file, str):
                self.filename = file
            
            self.header = self._read_header(open_file)
            self.info = self._read_info(open_file)
            self.materials = self._read_materials(open_file)
            self.attributes = self._read_attributes(open_file)
            self.submeshes = self._read_submesh_info(open_file)
            self.verts = self._read_verts(open_file)
            self.bones = self._read_bones(open_file)

            self._read_indexes_and_weights(open_file)
            
            self.meshes = self._read_meshes(open_file)
    
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

    def _read_materials(self, file: BinaryIO):
        texture_info = self.info.get(enums.rk.Info.TEXTURES)
        if texture_info is None:
            return []
        
        file.seek(texture_info[0])

        materials = []
        
        for x in range(texture_info[1]):
            name = read_ascii_string(file)
            rkm = os.path.join(
                os.path.dirname(self.filename),
                name + '.rkm',
            )
            materials.append(Material(
                name = name,
                rkm = rkm,
            ))
        
        return materials

    def _read_attributes(self, file: BinaryIO):
        attributes_info = self.info.get(enums.rk.Info.ATTRIBUTES)
        if attributes_info is None:
            return []
        
        attributes = []
        
        format_str = 'H2B'
        
        self._uv_offset, self._uv_format = 0, 0
        self._uv_scale = 1
        file.seek(attributes_info[0])
        for x in range(attributes_info[1]):
            i = struct.unpack(
                format_str,
                file.read(struct.calcsize(format_str)),
            )
            if i[0] == 1030:
                self._uv_offset, self._uv_format = i[1], 'H'
                self._uv_scale = 2
                
            elif i[0] == 1026:
                self._uv_offset, self._uv_format = i[1], 'f'
                self._uv_scale = 1
            
            attributes.append(i)
        
        return attributes

    def _read_submesh_info(self, file: BinaryIO):
        submesh_names_info = self.info.get(enums.rk.Info.SUBMESH_NAMES)
        if submesh_names_info is None:
            return []
        
        submesh_info_info = self.info.get(enums.rk.Info.SUBMESH_INFO)
        if submesh_info_info is None:
            return []
        
        submeshes = []
        
        file.seek(submesh_names_info[0])
        submesh_names = []
        for x in range(submesh_names_info[1]):
            submesh_names.append(read_ascii_string(file))
        
        
        file.seek(submesh_info_info[0])
        for x in range(submesh_info_info[1]):
            info = struct.unpack(
                '4I',
                file.read(struct.calcsize('4I')),
            )
            submeshes.append(Submesh(
                name = submesh_names[x],
                triangles = info[0],
                offset = info[1],
                material = info[2],
                unknown = info[3],
            ))
        
        return submeshes
    
    def _read_verts(self, file: BinaryIO) -> list[tuple[float,float,float,float]]:
        
        verts_info = self.info.get(enums.rk.Info.VERTS)
        if verts_info is None:
            return []
        
        file.seek(verts_info[0])
        

        stride = verts_info[2] // verts_info[1]
        vbuf = file.read(verts_info[2])
        
        verts = []
        
        vert_format = '3f'

        init_size = struct.calcsize(vert_format)
            
        if self._uv_format:
            if init_size < self._uv_offset:
                vert_format += f'{self._uv_offset - init_size}x'
            vert_format += f'2{self._uv_format}'
        
        init_size = struct.calcsize(vert_format)
        if init_size < stride:
            vert_format += f'{stride - init_size}x'
        
        for vert_info in struct.iter_unpack(
            vert_format,
            vbuf,
        ):
            vert = Vert(
                x = vert_info[0],
                y = vert_info[1],
                z = vert_info[2],
            )

            if self._uv_format == 'H':
                vert.u = (vert_info[3] * self._uv_scale) / USHORT_MAX
                vert.v = (vert_info[4] * self._uv_scale) / USHORT_MAX
            elif self._uv_format == 'f':
                vert.u = vert_info[3]
                vert.v = vert_info[4]
            
            verts.append(vert)
        
        return verts

    def _read_bones(self, file: BinaryIO):
        
        bones_info = self.info.get(enums.rk.Info.BONES)
        if bones_info is None:
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
                    matrix = numpy.frombuffer(matrix, dtype = numpy.float32).reshape((4,4))[:3],
                    name = read_ascii_string(name),
                ))
        
        return bones

    def _read_indexes_and_weights(self, file: BinaryIO):
        weight_info = self.info.get(enums.rk.Info.WEIGHTS)
        if weight_info is None:
            return []
        
        file.seek(weight_info[0])
        
        buffer = file.read(weight_info[2])

        stride = weight_info[2] // weight_info[1]
        
        indexes = []
        
        vert_index = 0
        
        for unpacked in struct.iter_unpack(
            'BB2xHH4x',
            buffer,
        ):
            vert = self.verts[vert_index]
            
            
            vert.index1 = unpacked[0]
            vert.weight1 = unpacked[2] / USHORT_MAX
            vert.index2 = unpacked[1]
            vert.weight2 = unpacked[3] / USHORT_MAX
            
            
            vert_index += 1
    
    def _read_meshes(self, file: BinaryIO):
        mesh_info =  self.info.get(enums.rk.Info.TRIANGLES)
        if mesh_info is None:
            return []

        meshes = []
        
        triangle_format = 'H'
        if self.info.get(enums.rk.Info.VERTS, (0,0,0))[1] > USHORT_MAX:
            triangle_format = 'I'
        
        for submesh in self.submeshes:
            mesh = Mesh(submesh.name)
            meshes.append(mesh)
            mesh.material = self.materials[submesh.material].name
            
            file.seek(mesh_info[0] + submesh.offset)
            for triangle_data in struct.iter_unpack(
                f'3{triangle_format}',
                file.read(submesh.triangles * 3 * struct.calcsize(triangle_format)),
            ):
                mesh.triangles.append(Triangle(
                    index1 = triangle_data[2],
                    index2 = triangle_data[1],
                    index3 = triangle_data[0],
                ))
        
        return meshes


# Dataclasses

@dataclass
class RKM:
    filename: str
    
    DiffuseTexture: str = ''
    ClampMode: Literal['RK_REPEAT', 'RK_CLAMP'] = 'RK_REPEAT'
    BlendMode: Literal['alpha', 'add', 'none'] = 'none'
    DepthWrite: bool = 0
    DepthTest: float = 0
    Cull: bool = False
    Shader: str = ''
    NeverDownscale: bool = False
    NoCompress: bool = False
    NormalQualityForceDownscale: bool = False
    UseMipmaps: bool = False
    PixelFormat: Literal['888', ''] = ''
    
    def __post_init__(self):
        for attr, field in self.__dataclass_fields__.items():
            field: dataclasses.Field
            attr: str
            
            if field.type is float:
                setattr(self, attr, strToFloat(getattr(self, attr)))
            elif field.type is int:
                setattr(self, attr, strToInt(getattr(self, attr)))
            elif field.type is bool:
                setattr(self, attr, strToBool(getattr(self, attr)))
    
    @property
    def texture_name(self):
        if self.NoCompress:
            return self.DiffuseTexture + '.png'
        else:
            return self.DiffuseTexture + '.pvr'
    
    @property
    def dir(self):
        return os.path.dirname(self.filename)

@dataclass
class Mesh:
    name: str
    material: str = ''
    triangles: list['Triangle'] = dataclasses.field(default_factory = list)


@dataclass
class Bone:
    index: int
    child: int
    name: str
    matrix: numpy.ndarray
    parentName: str | None = None,
    parentIndex: int = -1

@dataclass
class Submesh:
    name: str
    triangles: int
    offset: int
    material: int
    unknown: int

@dataclass
class Material:
    name: str
    rkm: str
    
    @property
    def info(self) -> 'RKM':
        if not hasattr(self, '_info'):
            self._info = parse_rkm(self.rkm)
        
        return self._info
    
    @info.setter
    def info(self, value: dict[str | int | bool]):
        self._info = value

@dataclass
class Vert:
    x: float
    y: float
    z: float
    u: float = 0
    v: float = 0
    
    index1: int = 0
    weight1: float = 0
    index2: int = 0
    weight2: float = 0

@dataclass
class Triangle:
    index1: int
    index2: int
    index3: int
