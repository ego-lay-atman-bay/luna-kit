import math
from dataclasses import dataclass
from typing import Annotated

import numpy
# import quaternionic
from pyquaternion import Quaternion

USHORT_MAX = 65535

@dataclass
class Vector3:
    x: float = 0
    y: float = 0
    z: float = 0
    
    def flip(self):
        return Vector3(
            -self.x,
            -self.y,
            -self.z,
        )
    
    
@dataclass
class Vector4:
    w: float = 0
    x: float = 0
    y: float = 0
    z: float = 0

def rotate_quaternion(quaternion: Quaternion, by: Quaternion):
    quaternion = quaternion.normalised
    quaternion.rotate

def euler_to_quaternion(yaw: float, pitch: float, roll: float):
    """Convert euler to quaternion.
    
    Code by David K on stackoverflow
    https://math.stackexchange.com/a/2975462/1257368

    Args:
        yaw (float): Yaw in radians
        pitch (float): Pitch in radians
        roll (float): Roll in radians

    Returns:
        Quaternion: The resulting Quaternion object
    """
    
    e = [yaw, pitch, roll]
    
    q = [0,0,0,0]
    i = 0
    j = 1
    k = 2
    
    ti = tj = th = ci = cj = ch = si = sj = sh = cc = cs = sc = ss = 0
    
    a = [0,0,0]

    ti = e[i] * 0.5
    tj = e[j] * 0.5
    th = e[k] * 0.5
    
    ci = math.cos(ti)
    cj = math.cos(tj)
    ch = math.cos(th)
    si = math.sin(ti)
    sj = math.sin(tj)
    sh = math.sin(th)

    cc = ci * ch
    cs = ci * sh
    sc = si * ch
    ss = si * sh

    a[i] = cj * sc - sj * cs
    a[j] = cj * ss + sj * cc
    a[k] = cj * cs - sj * sc

    q[0] = float(cj * cc + sj * ss)
    q[1] = float(a[0])
    q[2] = float(a[1])
    q[3] = float(a[2])
    
    return quaternionic.array(q)
    
    qx = numpy.sin(roll/2) * numpy.cos(pitch/2) * numpy.cos(yaw/2) - numpy.cos(roll/2) * numpy.sin(pitch/2) * numpy.sin(yaw/2)
    qy = numpy.cos(roll/2) * numpy.sin(pitch/2) * numpy.cos(yaw/2) + numpy.sin(roll/2) * numpy.cos(pitch/2) * numpy.sin(yaw/2)
    qz = numpy.cos(roll/2) * numpy.cos(pitch/2) * numpy.sin(yaw/2) - numpy.sin(roll/2) * numpy.sin(pitch/2) * numpy.cos(yaw/2)
    qw = numpy.cos(roll/2) * numpy.cos(pitch/2) * numpy.cos(yaw/2) + numpy.sin(roll/2) * numpy.sin(pitch/2) * numpy.sin(yaw/2)
    return Quaternion(w = qw, x = qx, y = qy, z = qz)

def decompose_bone_matrix(matrix: numpy.ndarray):
    """Decompose bone matrix to individual values.
    
    This was adapted from blender's implementation.
    https://projects.blender.org/blender/blender/src/branch/main/source/blender/python/mathutils/mathutils_Matrix.cc

    Args:
        matrix (numpy.ndarray): 4x4 transformation matrix

    Raises:
        ValueError: Matrix must be 4x4

    Returns:
        tuple[numpy.ndarray, Quaternion, numpy.ndarray]: translation, rotation, scale
    """
    
    if matrix.shape != (4,4):
        raise ValueError('Matrix must be 4x4')
    
    loc, rot, size = _mat4_to_loc_rot_size(matrix)
    
    # quat = Quaternion(matrix = rot)
    # We have to convert to quaternion using a different formula
    # because pyquaternion throws an error
    q = mat3_normalized_to_quat_with_checks(rot)
    # quat = Quaternion(w = q[0], x = q[1], y = q[2], z = q[3])
    quat = quaternionic.array(q)
    
    return loc, quat, size

def _mat4_to_loc_rot_size(wmat: numpy.ndarray):
    mat3 = wmat[:3,:3]
    
    rot, size = _mat3_to_rot_size(mat3)
    
    loc = wmat[3,:3]
    
    return loc, rot, size

def _mat3_to_rot_size(mat3: numpy.ndarray):
    rot_size = []
    
    rot_size.append(_normalize_v3_v3(mat3[0]))
    rot_size.append(_normalize_v3_v3(mat3[1]))
    rot_size.append(_normalize_v3_v3(mat3[2]))

    rot, size = tuple(zip(*rot_size))
    
    rot: numpy.ndarray = numpy.array(rot).swapaxes(1,0)
    size: numpy.ndarray = numpy.array(size)

    if numpy.linalg.det(rot) < 0:
        rot = -rot
        size = -size
    
    rot = _normalize_mat3(rot)
    
    return rot, size

def _normalize_mat3(matrix: numpy.ndarray):
    matrix = matrix.copy()
    for index, row in enumerate(matrix):
        matrix[index] = _normalize_v3_v3(row)[0]
    
    return matrix

def _normalize_v3_v3(a: numpy.ndarray):
    return _normalize_v3_v3_length(a, 1.0)

def _normalize_v3_v3_length(a: numpy.ndarray, unit_length: float):
    size = a.dot(a)
    
    # A larger value causes normalize errors in a scaled down models with camera extreme close.
    
    if (size > 1.0e-35):
        size = math.sqrt(size)
        rot = a * (unit_length / size)
    else:
        rot = numpy.array([0, 0, 0])
        size = 0.0
    
    return rot, size

def compose_bone_matrix(
    translation: numpy.ndarray,
    rotation: numpy.ndarray,
    scale: numpy.ndarray,
    *,
    dtype: numpy.dtype = numpy.float32,
):
    """Compose transformation matrix.
    
    This code was adapted from blender's mathutils.
    https://projects.blender.org/blender/blender/src/branch/main/source/blender/python/mathutils/mathutils_Matrix.cc

    Args:
        translation (numpy.ndarray): Translation as a 3 item array
        rotation (Quaternion): Rotation as a quaternion
        scale (numpy.ndarray): Scale as a 3 item array

    Returns:
        numpy.ndarray: 4x4 transformation matrix
    """
    mat = numpy.array([], dtype = dtype)

    if translation is None:
        translation = numpy.ndarray([0,0,0], dtype = dtype)
    else:
        translation = numpy.array(translation, dtype = dtype)
    
    if rotation is None:
        mat = numpy.eye(4, dtype = dtype)
    # elif isinstance(rotation, Quaternion):
    elif isinstance(rotation, numpy.ndarray):
        mat = mat3_to_mat4(quat_to_mat3(rotation))
    
    # decode scale
    if scale is not None:
        mat[:3,:3] *= scale
    
    mat[3,:3] = translation
    
    return mat

def quat_to_mat3(q: numpy.ndarray):
    """Convert quaternion to 3x3 matrix

    Args:
        q (numpy.ndarray): Quaternion as numpy.array([w, x, y, z])
    """
    q = numpy.array(q)
    
    q0 = q1 = q2 = q3 = qda = qdb = qdc = qaa = qab = qac = qbb = qbc = qcc = 0

    M_SQRT2 = numpy.sqrt(2)

    q0 = M_SQRT2 * q[0]
    q1 = M_SQRT2 * q[1]
    q2 = M_SQRT2 * q[2]
    q3 = M_SQRT2 * q[3]

    qda = q0 * q1
    qdb = q0 * q2
    qdc = q0 * q3
    qaa = q1 * q1
    qab = q1 * q2
    qac = q1 * q3
    qbb = q2 * q2
    qbc = q2 * q3
    qcc = q3 * q3

    m = numpy.array([[(1.0 - qbb - qcc), (qdc + qab)      , (-qdb + qac)     ],
                     [(-qdc + qab)     , (1.0 - qaa - qcc), (qda + qbc)      ],
                     [(qdb + qac)      , (-qda + qbc)     , (1.0 - qaa - qbb)]])
    
#     m[0][0] = (1.0 - qbb - qcc)
#     m[0][1] = (qdc + qab)
#     m[0][2] = (-qdb + qac)
# 
#     m[1][0] = (-qdc + qab)
#     m[1][1] = (1.0 - qaa - qcc)
#     m[1][2] = (qda + qbc)
# 
#     m[2][0] = (qdb + qac)
#     m[2][1] = (-qda + qbc)
#     m[2][2] = (1.0 - qaa - qbb)
    
    return m

def mat3_to_mat4(matrix: numpy.ndarray, *, dtype: numpy.dtype = numpy.float32):
    new_matrix = numpy.eye(4, dtype = dtype)
    new_matrix[:matrix.shape[0],:matrix.shape[1]] = matrix
    # matrix = numpy.pad(matrix, ((0,1),(0,1)), 'constant', constant_values = (0))
    # matrix[3,3] = 1
    return new_matrix

def mat3_normalized_to_quat_with_checks(mat):
    det = numpy.linalg.det(mat)
    
    print(f'det: {det}')
    if (det < 0):
        mat = -mat
    print(f'det: {numpy.linalg.det(mat)}')
    
    return mat3_normalized_to_quat_fast(mat)

def mat3_normalized_to_quat_fast(mat):
    q = [0,0,0,0]
    
    assert numpy.any(mat >= 0), "can't be negative"

    if (mat[2][2] < 0.0):
        if (mat[0][0] > mat[1][1]):
            trace = 1.0 + mat[0][0] - mat[1][1] - mat[2][2]
            s = 2.0 * math.sqrt(trace)
            if (mat[1][2] < mat[2][1]):
                # Ensure W is non-negative for a canonical result.
                s = -s
            q[1] = 0.25 * s
            s = 1.0 / s
            q[0] = (mat[1][2] - mat[2][1]) * s
            q[2] = (mat[0][1] + mat[1][0]) * s
            q[3] = (mat[2][0] + mat[0][2]) * s
            if ((trace == 1.0) and (q[0] == 0.0 and q[2] == 0.0 and q[3] == 0.0)):
                # Avoids the need to normalize the degenerate case.
                q[1] = 1.0
        else:
            trace = 1.0 - mat[0][0] + mat[1][1] - mat[2][2]
            s = 2.0 * math.sqrt(trace)
            if (mat[2][0] < mat[0][2]):
                # Ensure W is non-negative for a canonical result.
                s = -s
            q[2] = 0.25 * s
            s = 1.0 / s
            q[0] = (mat[2][0] - mat[0][2]) * s
            q[1] = (mat[0][1] + mat[1][0]) * s
            q[3] = (mat[1][2] + mat[2][1]) * s
            if ((trace == 1.0) and (q[0] == 0.0 and q[1] == 0.0 and q[3] == 0.0)):
                # Avoids the need to normalize the degenerate case.
                q[2] = 1.0
    else:
        if (mat[0][0] < -mat[1][1]):
            trace = 1.0 - mat[0][0] - mat[1][1] + mat[2][2]
            s = 2.0 * numpy.sqrt(trace)
            if (mat[0][1] < mat[1][0]):
                # Ensure W is non-negative for a canonical result.
                s = -s
            q[3] = 0.25 * s
            s = 1.0 / s
            q[0] = (mat[0][1] - mat[1][0]) * s
            q[1] = (mat[2][0] + mat[0][2]) * s
            q[2] = (mat[1][2] + mat[2][1]) * s
            if ((trace == 1.0) and (q[0] == 0.0 and q[1] == 0.0 and q[2] == 0.0)):
                # Avoids the need to normalize the degenerate case.
                q[3] = 1.0
        else:
            # NOTE(@ideasman42): A zero matrix will fall through to this block,
            # * needed so a zero scaled matrices to return a quaternion without rotation, see: #101848.
            trace = 1.0 + mat[0][0] + mat[1][1] + mat[2][2]
            s = 2.0 * math.sqrt(trace)
            q[0] = 0.25 * s
            s = 1.0 / s
            q[1] = (mat[1][2] - mat[2][1]) * s
            q[2] = (mat[2][0] - mat[0][2]) * s
            q[3] = (mat[0][1] - mat[1][0]) * s
            if ((trace == 1.0) and (q[1] == 0.0 and q[2] == 0.0 and q[3] == 0.0)):
                # Avoids the need to normalize the degenerate case.
                q[0] = 1.0
    
    return q


def flip_quaternion(quaternion: numpy.ndarray):
    quaternion = quaternionic.array(quaternion)

    quaternion = quaternionic.array([
        quaternion.w,
        -quaternion.x,
        quaternion.y,
        -quaternion.z,
    ])
    
    quaternion.ro
    quaternion.conj
    
    Quaternion.rotate
    
    quaternionic.array.from_rotation_matrix()
    quaternion.normalized
    
    quaternion = quaternion.rotate((-4.371138828673793e-08, -0.0, 1.0, -0.0))
    return quaternion
