import io
import os
import struct
from dataclasses import dataclass
from typing import Literal

import numpy
import pygltflib
from datauri import DataURI

from ..file_utils import PathOrBinaryFile, open_binary
from .model_common import (USHORT_MAX, Vector3, Vector4, compose_bone_matrix,
                           decompose_bone_matrix, flip_quaternion)
from .mathutils import *
from .rk import RKModel


@dataclass
class Primitive:
    data: bytes
    datatype: int


class GltbfBuilder:
    def __init__(self):
            self.model = pygltflib.GLTF2()
            self.bin = b''
            self.bin_buffer = 0
    
    def finish(self):
        self.model.buffers.append(pygltflib.Buffer(
            byteLength = len(self.bin)
        ))
        self.model.set_binary_blob(self.bin)
        
        glb = b''.join(self.model.save_to_bytes())
        return glb
    
    def push_node(self, node: pygltflib.Node):
        index = len(self.model.nodes)
        self.model.nodes.append(node)
        return index
    
    def push_mesh(self, mesh: pygltflib.Mesh):
        index = len(self.model.meshes)
        self.model.meshes.append(mesh)
        return index
    
    def push_accessor(self, accessor: pygltflib.Accessor):
        index = len(self.model.accessors)
        self.model.accessors.append(accessor)
        return index
    
    def push_view(self, view: pygltflib.BufferView):
        index = len(self.model.bufferViews)
        self.model.bufferViews.append(view)
        return index
    
    def push_scene(self, scene: pygltflib.Scene):
        index = len(self.model.scenes)
        self.model.scenes.append(scene)
        return index
    
    def push_skin(self, skin: pygltflib.Skin):
        index = len(self.model.skins)
        self.model.skins.append(skin)
        return index
    
    def push_animation(self, animation: pygltflib.Animation):
        index = len(self.model.animations)
        self.model.animations.append(animation)
        return index
    
    def push_image(self, image: pygltflib.Image):
        index = len(self.model.images)
        self.model.images.append(image)
        return index
    
    def push_texture(self, texture: pygltflib.Texture):
        index = len(self.model.textures)
        self.model.textures.append(texture)
        return index
    
    def push_material(self, material: pygltflib.Material):
        index = len(self.model.materials)
        self.model.materials.append(material)
        return index
    
    def node(self, index: int):
        return self.model.nodes[index]
    
    def add_extension(self, name: str, required: bool = False):
        if required:
            self.model.extensionsRequired.append(name)
        self.model.extensionsUsed.append(name)
    
    def set_default_scene(self, scene_index: int):
        self.model.scene = scene_index
    
    def push_bin_view(self, data: bytes, target: int):
        offset = len(self.bin)
        self.bin += data
        if len(data) % 4 != 0:
            self.bin += '\x00' * (4 - (len(data) % 4))
        
        self.push_view(pygltflib.BufferView(
            buffer = self.bin_buffer,
            byteLength = len(data),
            byteOffset = offset,
            target = target,
        ))
    
    def push_bin_accessor(
        self,
        array: numpy.ndarray,
        accessor_type: str,
        normalized: bool = False,
        buffer_target: int = None,
    ):
        TYPE_FORMATS = {
            numpy.dtype('int8'): {
                'gltf': pygltflib.BYTE,
                'struct': 'b',
            },
            numpy.dtype('uint8'): {
                'gltf': pygltflib.UNSIGNED_BYTE,
                'struct': 'B',
            },
            numpy.dtype('int16'): {
                'gltf': pygltflib.SHORT,
                'struct': 'h',
            },
            numpy.dtype('uint16'): {
                'gltf': pygltflib.UNSIGNED_SHORT,
                'struct': 'H',
            },
            numpy.dtype('uint32'): {
                'gltf': pygltflib.UNSIGNED_INT,
                'struct': 'I',
            },
            numpy.dtype('float32'): {
                'gltf': pygltflib.FLOAT,
                'struct': 'f',
            },
        }
        
        type_format = TYPE_FORMATS[array.dtype]
        

        offset = len(self.bin)
        minimum = maximum = None
        
        data = array.tobytes()
        
        self.bin += data
        byte_length = len(data)
        
        if len(self.bin) % 4 != 0:
            self.bin += '\x00' * (4 - (len(self.bin) % 4))
        
        view_index = self.push_view(pygltflib.BufferView(
            buffer = self.bin_buffer,
            byteLength = byte_length,
            byteOffset = offset,
            target = buffer_target,
        ))
        
        VEC_TYPES = [
            pygltflib.VEC2,
            pygltflib.VEC3,
            pygltflib.VEC4,
        ]
        
        MAT_TYPES = [
            pygltflib.MAT2,
            pygltflib.MAT3,
            pygltflib.MAT4,
        ]
        
        if accessor_type in VEC_TYPES or accessor_type in MAT_TYPES:
            minimum = [float(v) for v in array.min(axis = 0).flatten().tolist()]
            maximum = [float(v) for v in array.max(axis = 0).flatten().tolist()]
        # elif accessor_type in MAT_TYPES:
        #     minimum = array.flatten
        else:
            minimum = [int(array.min())]
            maximum = [int(array.max())]
        
        return self.push_accessor(pygltflib.Accessor(
            bufferView = view_index,
            count = len(array),
            componentType = type_format['gltf'],
            type = accessor_type,
            min = minimum,
            max = maximum,
            normalized = normalized,
        ))

def rk_to_gltf(model: RKModel, output: PathOrBinaryFile):
    gltf = GltbfBuilder()
    gltf.add_extension(
        'KHR_materials_unlit',
        required = True,
    )
    
    DATATYPES_MAP = {
        pygltflib.UNSIGNED_INT: {
            'numpy': numpy.uint32,
            'struct': 'I',
        },
        pygltflib.UNSIGNED_SHORT: {
            'numpy': numpy.uint16,
            'struct': 'H',
        },
        pygltflib.UNSIGNED_BYTE: {
            'numpy': numpy.uint8,
            'struct': 'B',
        },
    }
    
    material_indexes = {}
    
    
    for material_index, material in enumerate(model.materials):
        image_data = io.BytesIO()
        material.properties.image.save(image_data, 'PNG')
        
        uri: DataURI = DataURI.make(
            mimetype = 'image/png',
            base64 = True,
            data = image_data.getvalue(),
            charset = None,
        )
        image_index = gltf.push_image(pygltflib.Image(
            uri = str(uri),
            mimeType = uri.mimetype,
            name = material.properties.DiffuseTexture,
        ))
        
        texture_index = gltf.push_texture(
            pygltflib.Texture(
                source = image_index,
                sampler = None,
                name = material.properties.DiffuseTexture,
                extensions = None,
            )
        )
        
        blend_modes = {
            'alpha': pygltflib.OPAQUE,
            'add': pygltflib.BLEND,
            'none': None,
        }
        
        material_index = gltf.push_material(
            pygltflib.Material(
                pbrMetallicRoughness = pygltflib.PbrMetallicRoughness(
                    baseColorTexture = pygltflib.TextureInfo(
                        index = texture_index,
                        texCoord = 0,
                        extensions = None,
                    ),
                    baseColorFactor = [1, 1, 1, 1],
                    metallicFactor = 0,
                    roughnessFactor = 1,
                    metallicRoughnessTexture = None,
                    extensions = None,
                ),
                alphaCutoff = None,
                alphaMode = blend_modes.get(material.properties.BlendMode, pygltflib.OPAQUE),
                doubleSided = not material.properties.Cull,
                normalTexture = None,
                occlusionTexture = None,
                emissiveTexture = None,
                emissiveFactor = [0, 0, 0],
                name = material.name,
                extensions = {
                    'KHR_materials_unlit': {},
                },
            )
        )
        
        material_indexes[material.name] = material_index
    
    bone_mats: list[Matrix4] = []
    bone_mats_inverse: list[Matrix4] = []
    for bone in model.bones:
        translation, rotation, scale = Matrix4(bone.matrix_4x4).decompose()
        translation = -translation
        rotation = rotation.flip()
        matrix = Matrix4.compose(translation, rotation, scale)
        
        bone_mats.append(matrix)
        bone_mats_inverse.append(matrix.inverse())
    
    all_bone_nodes = []
    inverse_bind_matrices = []
    
    for bone in model.bones:
        local_mat = bone_mats[bone.index]
        if bone.parentIndex >= 0:
            local_mat = bone_mats_inverse[bone.parentIndex] @ bone_mats[bone.index]
        
        inverse_bind_matrices.append(bone_mats_inverse[bone.index].matrix)
        
        translation, rotation, scale = local_mat.decompose()

        normalized_rotation = rotation.normalized

        bone_index = gltf.push_node(
            pygltflib.Node(
                camera = None,
                children = [],
                matrix = None,
                mesh = None,
                rotation = [
                    float(normalized_rotation.x),
                    float(normalized_rotation.y),
                    float(normalized_rotation.z),
                    float(normalized_rotation.w),
                ],
                scale = scale.array.tolist(),
                translation = translation.array.tolist(),
                skin = None,
                name = bone.name,
                extensions = None,
            )
        )
        
        all_bone_nodes.append(bone_index)
    
    # `bone_nodes` contains only the nodes corresponding to bones in the original `Object`.
    # `all_bone_nodes` contains all bones, including additional ones created for model visibility
    # animations.
    bone_nodes = all_bone_nodes.copy()
    
    # set bone parents
    for bone in model.bones:
        if bone.parentIndex >= 0:
            bone_index = bone_nodes[bone.index]
            parent_index = bone_nodes[bone.parentIndex]
            gltf.node(parent_index).children.append(bone_index)
    
    # root bone
    root_bone_index = gltf.push_node(
        pygltflib.Node(
            camera = None,
            children = [bone.index for bone in model.bones if bone.parentIndex == -1],
            matrix = None,
            mesh = None,
            rotation = None,
            scale = None,
            translation = None,
            skin = None,
            name = None,
            extensions = None,
        )
    )
    
    inverse_bind_matrices_acc = gltf.push_bin_accessor(
        numpy.array(inverse_bind_matrices, dtype = numpy.float32),
        accessor_type = pygltflib.MAT4,
    )
    
    skin_index = gltf.push_skin(pygltflib.Skin(
        joints = all_bone_nodes,
        skeleton = root_bone_index,
        inverseBindMatrices = inverse_bind_matrices_acc,
        name = model.name,
    ))
    
    rk_verts = []
    rk_uvs = []
    rk_joints = []
    rk_weights = []
    
    for vert in model.verts:
        rk_verts.append([
            -vert.pos.x,
            -vert.pos.y,
            -vert.pos.z,
        ])
        
        rk_uvs.append([
            vert.u,
            vert.v,
        ])
        
        rk_joints.append([bone.bone for bone in vert.bones])
        rk_weights.append([bone.weight for bone in vert.bones])
    
    verts_index = gltf.push_bin_accessor(
        array = numpy.array(rk_verts, dtype = numpy.float32),
        normalized = False,
        accessor_type = pygltflib.VEC3,
        buffer_target = pygltflib.ARRAY_BUFFER,
    )
    
    uv_index = gltf.push_bin_accessor(
        array = numpy.array(rk_uvs, dtype = numpy.float32),
        normalized = False,
        accessor_type = pygltflib.VEC2,
        buffer_target = pygltflib.ARRAY_BUFFER,
    )
    
    joints_index = gltf.push_bin_accessor(
        array = numpy.array(rk_joints, dtype = numpy.uint16),
        normalized = False,
        accessor_type = pygltflib.VEC4,
        buffer_target = pygltflib.ARRAY_BUFFER,
    )
    
    weights_index = gltf.push_bin_accessor(
        array = numpy.array(rk_weights, dtype = numpy.float32),
        normalized = False,
        accessor_type = pygltflib.VEC4,
        buffer_target = pygltflib.ARRAY_BUFFER,
    )
    
    indices_datatype = pygltflib.UNSIGNED_INT if len(model.verts) >= struct.calcsize('H') else pygltflib.UNSIGNED_SHORT
    
    mesh_nodes = []
    
    for mesh in model.meshes:
        rk_indices = []
        for triangle in mesh.triangles:
            rk_indices.extend((
                triangle.x,
                triangle.y,
                triangle.z,
            ))
    
        indices_index = gltf.push_bin_accessor(
            array = numpy.array(rk_indices, dtype = DATATYPES_MAP[indices_datatype]['numpy']),
            normalized = False,
            accessor_type = pygltflib.SCALAR,
        )
        
        primitive = pygltflib.Primitive(
            attributes = pygltflib.Attributes(
                POSITION = verts_index,
                TEXCOORD_0 = uv_index,
                JOINTS_0 = joints_index,
                WEIGHTS_0 = weights_index,
            ),
            indices = indices_index,
            mode = pygltflib.TRIANGLES,
            material = material_indexes[mesh.material],
        )
        
        mesh_index = gltf.push_mesh(pygltflib.Mesh(
            primitives = [primitive],
        ))
        
        node_index = gltf.push_node(pygltflib.Node(
            mesh = mesh_index,
            name = mesh.name,
            skin = skin_index,
        ))
        
        mesh_nodes.append(node_index)
    
    scene_nodes = mesh_nodes.copy()
    
    scene_index = gltf.push_scene(pygltflib.Scene(
        nodes = scene_nodes,
        name = model.name,
    ))
    
    gltf.set_default_scene(scene_index)
    
    if isinstance(output, str):
        output = os.path.abspath(output)
        os.makedirs(os.path.dirname(output), exist_ok = True)
    
    with open_binary(output, 'w') as file:
        file.write(gltf.finish())
        
    return gltf

def rk_to_gltf_old(model: RKModel):
    gltf = pygltflib.GLTF2()
    gltf.extensionsUsed.append('KHR_materials_unlit')
    gltf.extensionsRequired.append('KHR_materials_unlit')
    
    for material_index, material in enumerate(model.materials):
        material
        
        image_data = io.BytesIO()
        material.properties.image.save(image_data, 'PNG')
        
        uri: DataURI = DataURI.make(
            mimetype = 'image/png',
            base64 = True,
            data = image_data.getvalue(),
        )
        gltf.images.append(pygltflib.Image(
            uri = str(uri),
            mimeType = uri.mimetype,
            name = material.properties.DiffuseTexture,
        ))
        
        gltf.textures.append(
            pygltflib.Texture(
                source = len(gltf.images) - 1,
                sampler = None,
                name = material.properties.DiffuseTexture,
                extensions = None,
            )
        )
        
        blend_modes = {
            'alpha': pygltflib.OPAQUE,
            'add': pygltflib.BLEND,
            'none': None,
        }
        
        gltf.materials.append(
            pygltflib.Material(
                pbrMetallicRoughness = pygltflib.PbrMetallicRoughness(
                    baseColorTexture = pygltflib.TextureInfo(
                        index = len(gltf.textures) - 1,
                        texCoord = 0,
                        extensions = None,
                    ),
                    baseColorFactor = [1, 1, 1, 1],
                    metallicFactor = 0,
                    roughnessFactor = 1,
                    metallicRoughnessTexture = None,
                    extensions = None,
                ),
                alphaCutoff = None,
                alphaMode = blend_modes.get(material.properties.BlendMode, pygltflib.OPAQUE),
                doubleSided = not material.properties.Cull,
                normalTexture = None,
                occlusionTexture = None,
                emissiveTexture = None,
                emissiveFactor = [0, 0, 0],
                name = material.name,
                extensions = {
                    'unlit': {},
                },
            )
        )
    
    bone_mats = []
    bone_mats_inverse = []
    for bone in model.bones:
        bone_mats.append(bone.matrix_4x4)
        bone_mats_inverse.append(numpy.linalg.inv(bone.matrix_4x4))
    
    all_bone_nodes = []
    inverse_bind_matrices = []
    
    for bone in model.bones:
        local_mat = bone.index
        if bone.parentIndex >= 0:
            local_mat = bone_mats_inverse[bone.parentIndex] * bone_mats[bone.index]
        
        inverse_bind_matrices.append(bone_mats_inverse[bone.index])
        
        
        translation, rotation, scale = bone.decompose_bone_matrix()
        
        
        

        gltf.nodes.append(
            pygltflib.Node(
                camera = None,
                children = [],
                matrix = None,
                mesh = None,
                rotation = [
                    rotation.vector[0],
                    rotation.vector[1],
                    rotation.vector[3],
                    rotation.scalar,
                ],
                scale = scale,
                translation = translation,
                skin = None,
                name = bone.name,
                extensions = None,
            )
        )
        
        all_bone_nodes.append(len(gltf.nodes) - 1)
    
    # `bone_nodes` contains only the nodes corresponding to bones in the original `Object`.
    # `all_bone_nodes` contains all bones, including additional ones created for model visibility
    # animations.
    bone_nodes = all_bone_nodes.copy()
    
    # set bone parents
    for bone in model.bones:
        if bone.parentIndex:
            gltf.nodes[bone.parentIndex].children.append(bone.index)
    
    # root bone
    gltf.nodes.append(
        pygltflib.Node(
            camera = None,
            children = [bone.index for bone in model.bones if bone.parentIndex >= 0],
            matrix = None,
            mesh = None,
            rotation = None,
            scale = None,
            translation = None,
            skin = None,
            name = None,
            extensions = None,
        )
    )
    
    root_bone_index = len(gltf.nodes) - 1
    
    min = numpy.min()
    
    # pygltflib.BufferView(
    #     byteLength=
    # )
    # 
    # gltf.accessors.append(
    #     pygltflib.Accessor(
    #         
    #     )
    # )
    
    model_nodes = []
    
    inverse_bind_matrices
    
    for mesh_index, mesh in model.meshes:
        attributes = {}
