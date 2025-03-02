import csv
import dataclasses
import io
import math
import os
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated, BinaryIO, Literal

import dataclasses_struct as dcs
import numpy
import PIL.Image
# import quaternion
# from pyquaternion import Quaternion

from .. import enums
from ..file_utils import PathOrBinaryFile, open_binary
from ..pvr import PVR
from ..utils import (increment_name_num, read_ascii_string, split_list,
                     strToBool, strToFloat, strToInt)
from .anim import Anim
from .model_common import USHORT_MAX, Vector3, Vector4, decompose_bone_matrix


@dcs.dataclass()
class Header:
    magic: Annotated[bytes, 8] = b'RKFORMAT'
    unknown1: dcs.U32 = 0
    unknown2: dcs.U32 = 0
    name: Annotated[bytes, 64] = b' ' * 64

@dataclass
class SectionHeader:
    tag: enums.rk.Tag
    offset: int
    count: int
    byte_length: int

def parse_rkm(filename: str):
    with open(filename, 'r', newline = '') as file:
        data = [row for row in csv.reader(file, delimiter='=') if len(row)]
    
    return RKM(
        filename = filename,
        **dict(data),
    )

class RKModel:
    MAGIC = b'RKFORMAT'
    
    header: Header
    section_headers: Mapping[enums.rk.Tag, SectionHeader]

    
    def __init__(self, file: PathOrBinaryFile = None) -> None:
        self.filename = ''

        self.header = Header()
        self.name = ''
        self.section_headers = {}
        self.materials: list[Material] = []
        self.bones: list[Bone] = []
        self.materials: list[Material] = []
        self.attributes: list[tuple[int, int, int]] = []
        self.submeshes: list[Submesh] = []
        self.verts: list[Vert] = []
        self.meshes: list[Mesh] = []
        self.animation: Anim | None = None
        
        if file is not None:
            self.read(file)
    
    def read(self, file: PathOrBinaryFile):
        self.filename = ''

        self.header = Header()
        self.name = ''
        self.section_headers = {}
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
            self.section_headers = self._read_sections_header(open_file)
            self.attributes = self._read_attributes(open_file)
            self.materials = self._read_materials(open_file)
            self.submeshes = self._read_submesh_info(open_file)
            self.bones = self._read_bones(open_file)

            self.verts = self._read_verts(open_file)
            self._read_indexes_and_weights(open_file)
            self.meshes = self._read_meshes(open_file)
            
        
    def load_animation(self, file: PathOrBinaryFile):
        self.animation = Anim(file)
    
    def create_dae(self, output: str | None = None):
        import collada
        import collada.source

        # for rk_material in self.materials:
        #     map = collada.material.Map()
        #     effect = collada.material.Effect(
        #         rk_material.name,
        #         [],
        #         "phong",
        #         double_sided = not rk_material.info.Cull,
        #         reflective = (0,0,0,0)
        #         transparency = 
        #     )
        
        meshes = []
        
        verts = []
        uvs = []
        for vert in self.verts:
            verts.extend([vert.x, vert.y, vert.z])
            uvs.extend([vert.u, -vert.v])
        
        mesh = collada.Collada()

        materials = []
        
        for rk_material in self.materials:
            image = collada.material.CImage(f'image-{rk_material.properties.DiffuseTexture}', f'{rk_material.properties.DiffuseTexture}.png')
            surface = collada.material.Surface(f'surface-{rk_material.properties.DiffuseTexture}', image)
            sampler2d = collada.material.Sampler2D(f'sampler-{rk_material.properties.DiffuseTexture}', surface)
            map = collada.material.Map(sampler2d, 'UVSET0')
            effect = collada.material.Effect(
                f"effect-{rk_material.name}",
                [surface, sampler2d],
                "lambert",
                emission = (0.0, 0.0, 0.0, 1),
                ambient=(0.0, 0.0, 0.0, 1),
                diffuse = map,
                transparent = map,
                transparency = map,
                double_sided = not rk_material.properties.Cull,
            )
            mat = collada.material.Material(f"material-{rk_material.name}", rk_material.name, effect)
            mesh.effects.append(effect)
            mesh.materials.append(mat)
            mesh.images.append(image)
            materials.append(mat)
        
        geometry_nodes = []
        
        for rk_mesh in self.meshes:
            vert_src = collada.source.FloatSource(f'verts-array-{rk_mesh.name}', numpy.array(verts), ('X', 'Y', 'Z'))
            uv_src = collada.source.FloatSource(f'uvs-array-{rk_mesh.name}', numpy.array(uvs), ('S', 'T'))
            
            geometry = collada.geometry.Geometry(
                mesh,
                rk_mesh.name,
                rk_mesh.name,
                [vert_src, uv_src],
                double_sided = False,
            )
            
            input_list = collada.source.InputList()
            input_list.addInput(0, 'VERTEX', f'#{vert_src.id}')
            input_list.addInput(0, 'TEXCOORD', f'#{uv_src.id}')
            indices = []
            for tri in rk_mesh.triangles:
                indices.extend([tri.x, tri.y, tri.z])
            triset = geometry.createTriangleSet(numpy.array(indices), input_list, f'materialRef-{rk_mesh.material}')

            geometry.primitives.append(triset)
            mesh.geometries.append(geometry)
            
            matnode = collada.scene.MaterialNode(f"materialref-{rk_mesh.material}", materials[rk_mesh.material_index], inputs=[])

            geometry_nodes.append(collada.scene.GeometryNode(
                geometry,
                [matnode],
            ))
        
        node = collada.scene.Node(f'node-{self.name}', children = geometry_nodes)
            
        
        scene = collada.scene.Scene('scene', [node])

        mesh.scenes.append(scene)
        mesh.scene = scene

        if output == None:
            output = self.name + '.dae'
        
        output_folder = os.path.dirname(output)

        os.makedirs(output_folder, exist_ok = True)

        mesh.write(output)
        for material in self.materials:
            material.properties.image.save(os.path.join(output_folder, material.properties.DiffuseTexture + '.png'))
        
        return
    
    def _read_header(self, file: BinaryIO):
        header: Header = Header.from_packed(
            file.read(dcs.get_struct_size(Header))
        )
        
        assert header.magic == self.MAGIC, 'file is not .rk file'
        
        return header
    
    def _read_sections_header(self, file: BinaryIO):
        sections: Mapping[enums.rk.Tag, SectionHeader] = {}
        size = 24 * 16
        
        for tag in struct.iter_unpack(
            '4I',
            file.read(size),
        ):
            if tag[0]:
                sections[tag[0]] = SectionHeader(*tag)
        
        return sections

    def _read_materials(self, file: BinaryIO):
        texture_info = self.section_headers.get(enums.rk.Tag.MATERIALS)
        if texture_info is None:
            return []
        
        file.seek(texture_info.offset)

        materials: list[Material] = []
        
        for x in range(texture_info.count):
            name = file.read(texture_info.byte_length//texture_info.count)
            if b'\00' in name:
                name = name[:name.index(b'\00')]
            name = name.decode('ascii', errors = 'ignore')
            # if name == '':
            #     if len(materials) >= 2:
            #         if materials[-1].name == materials[-2].name:
            #             name = materials[-1].name
            #         else:
            #             name = increment_name_num(materials[-1].name)
            #     else:
            #         name = increment_name_num(materials[-1].name)
            rkm = os.path.join(
                os.path.dirname(self.filename),
                name + '.rkm',
            )
            if not os.path.exists(rkm):
                name = materials[-1].name
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
        attributes_info = self.section_headers.get(enums.rk.Tag.ATTRIBUTES)
        if attributes_info is None:
            return []
        
        attributes = []
        
        format_str = 'H2B'
        
        self._uv_offset, self._uv_format = 0, 0
        self._uv_scale = 1
        file.seek(attributes_info.offset)
        for x in range(attributes_info.count):
            attribute = struct.unpack(
                format_str,
                file.read(struct.calcsize(format_str)),
            )
            if attribute[0] == 1030:
                self._uv_offset, self._uv_format = attribute[1], 'H'
                self._uv_scale = 2
                
            elif attribute[0] == 1026:
                self._uv_offset, self._uv_format = attribute[1], 'f'
                self._uv_scale = 1
            
            attributes.append(attribute)
        
        return attributes

    def _read_submesh_info(self, file: BinaryIO):
        submesh_names_info = self.section_headers.get(enums.rk.Tag.SUBMESH_NAMES)
        if submesh_names_info is None:
            return []
        
        submesh_info_info = self.section_headers.get(enums.rk.Tag.SUBMESH_INFO)
        if submesh_info_info is None:
            return []
        
        submeshes = []
        
        file.seek(submesh_names_info.offset)
        submesh_names = []
        for x in range(submesh_names_info.count):
            submesh_names.append(read_ascii_string(file, 64))
        
        
        file.seek(submesh_info_info.offset)
        for x in range(submesh_info_info.count):
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
        
        verts_info = self.section_headers.get(enums.rk.Tag.VERTS)
        if verts_info is None:
            return []
        
        file.seek(verts_info.offset)
        

        stride = verts_info.byte_length // verts_info.count
        vbuf = file.read(verts_info.byte_length)
        
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
                pos = Vector3(
                    x = vert_info[0],
                    y = vert_info[1],
                    z = vert_info[2],
                )
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
        bones_info = self.section_headers.get(enums.rk.Tag.BONES)
        if bones_info is None:
            return []
        
        bones = []
        
        bone_format = '3i64s64s'
        
        if bones_info.count:
            file.seek(bones_info.offset)
            for parent, index, children, matrix_buffer, name in struct.iter_unpack(
                bone_format,
                file.read(bones_info.count * struct.calcsize(
                    bone_format
                )),
            ):
                matrix = numpy.frombuffer(
                        matrix_buffer,
                        dtype = numpy.float32,
                    ).reshape((4,4))
                
                bones.append(Bone(
                    parentIndex = parent,
                    index = index,
                    children = children,
                    matrix_3x4 = matrix.swapaxes(1,0)[:,:3],
                    matrix_4x4 = matrix.swapaxes(1,0),
                    matrix_buffer = matrix_buffer,
                    name = read_ascii_string(name),
                ))
        
        return bones

    def _read_indexes_and_weights(self, file: BinaryIO):
        weight_info = self.section_headers.get(enums.rk.Tag.WEIGHTS)
        if weight_info is None:
            return []
        
        file.seek(weight_info.offset)
        
        buffer = file.read(weight_info.byte_length)

        stride = weight_info.byte_length // weight_info.count
        
        indexes = []
        
        # vert_index = 0
        
        for vert_index, unpacked in enumerate(struct.iter_unpack(
            '4B4H',
            buffer,
        )):
            vert = self.verts[vert_index]
            
            for bone_index, weight in zip(*split_list(unpacked, 2)):
                vert.bones.append(VertBone(
                    bone = bone_index,
                    weight = weight / USHORT_MAX,
                ))
            
            # vert.bone_index1 = unpacked[0]
            # vert.weight1 = unpacked[2] / USHORT_MAX
            # vert.bone_index2 = unpacked[1]
            # vert.weight2 = unpacked[3] / USHORT_MAX
            
            
            # vert_index += 1
    
    def _read_meshes(self, file: BinaryIO):
        mesh_info =  self.section_headers.get(enums.rk.Tag.FACES)
        if mesh_info is None:
            return []

        meshes = []
        
        formats: Mapping[int, str] = {
            2: 'H',
            4: 'I',
        }
        
        stride = mesh_info.byte_length // mesh_info.count
        assert stride in formats, f'Bad item size {stride} for face section. Expected 2 or 4 bytes.'

        triangle_format = formats[stride]
        
        file.seek(mesh_info.offset)
        for submesh in self.submeshes:
            mesh = Mesh(submesh.name)
            meshes.append(mesh)
            mesh.material = self.materials[submesh.material].name
            mesh.material_index = submesh.material
            
            # file.seek(mesh_info[0] + submesh.offset)
            for triangle_data in struct.iter_unpack(
                f'3{triangle_format}',
                file.read(submesh.triangles * 3 * struct.calcsize(triangle_format)),
            ):
                mesh.triangles.append(Triangle(
                    x = triangle_data[0],
                    y = triangle_data[1],
                    z = triangle_data[2],
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
    
    @property
    def image(self):
        filename = os.path.join(self.dir, self.texture_name)
        if not self.NoCompress:
            image = PVR(filename).image
        else:
            image = PIL.Image.open(filename)
        
        return image

@dataclass
class Mesh:
    name: str
    material: str = ''
    material_index: int = 0
    triangles: list['Triangle'] = dataclasses.field(default_factory = list)


@dataclass
class Bone:
    index: int
    children: int
    name: str
    matrix_3x4: numpy.ndarray
    matrix_4x4: numpy.ndarray
    matrix_buffer: bytes
    parentName: str | None = None,
    parentIndex: int = -1
    
    def decompose_bone_matrix(self):
        return decompose_bone_matrix(self.matrix_4x4)
        

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
    def properties(self) -> 'RKM':
        if not hasattr(self, '_info'):
            self._info = parse_rkm(self.rkm)
        
        return self._info
    
    @properties.setter
    def properties(self, value: dict[str | int | bool]):
        self._info = value

@dataclass
class VertBone:
    bone: int
    weight: float

@dataclass
class Vert:
    pos: Vector3 = dataclasses.field(default_factory = Vector3)
    u: float = 0
    v: float = 0
    
    bones: list[VertBone] = dataclasses.field(default_factory = list)

@dataclass
class Triangle:
    x: int
    y: int
    z: int
