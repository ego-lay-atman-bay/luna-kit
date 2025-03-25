from typing import TYPE_CHECKING, Self, Type

try:
    import numpy
except ImportError as e:
    e.add_note('model dependencies not found')
    raise e

if TYPE_CHECKING:
    from .quaternion import Quaternion
    from .vector import Vector3
    

class Matrix:
    shape: tuple[int, int] = (4, 4)
    
    def __init__(self, matrix: numpy.ndarray | None = None):
        if matrix is None:
            matrix = numpy.array([[0] * self.shape[0]] * self.shape[1])
        
        if isinstance(matrix, Matrix):
            matrix = matrix.matrix
        
        self.matrix = matrix
    
    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.matrix)})'
    
    @property
    def matrix(self):
        matrix = self.__matrix
        return matrix
    @matrix.setter
    def matrix(self, matrix: numpy.ndarray):
        matrix = numpy.array(matrix)
        if matrix.shape != self.shape:
            raise ValueError(f"Inappropriate matrix size {matrix.shape}, must be {self.shape}")
        
        self.__matrix = matrix.copy()
    
    def copy(self):
        return self.__class__(self.matrix)
    
    def __getitem__(self, index: int | slice):
        return self.__matrix[index]
    
    def __setitem__(self, index: int | slice, value: int | float | numpy.ndarray):
        self.__matrix[index] = value
    
    def __add__(self, value: Self | 'Matrix' | int | float):
        if isinstance(value, Matrix):
            value = value.matrix
        
        return self.__class__(self.matrix + value)
    
    def __pos__(self):
        return self.copy()

    def __radd__(self, value: Self | 'Matrix' | int | float):
        return self.__add__(value)
    
    def __sub__(self, value: Self | 'Matrix' | int | float):
        if isinstance(value, Matrix):
            value = value.matrix

        return self.__class__(self.matrix - value)
    
    def __rsub__(self, value: Self | 'Matrix' | int | float):
        if isinstance(value, Matrix):
            value = value.matrix

        return self.__class__(value - self.matrix)
    
    def __neg__(self):
        return self.__rsub__(0)
    
    def __mul__(self, value: 'Self | Matrix | int | float'):
        if isinstance(value, Matrix):
            value = value.matrix
        
        print(type(value))
        return self.__class__(self.matrix * value)

    def __rmul__(self, value: 'Self | Matrix | int | float'):
        return self.__mul__(value)
    
    def __matmul__(self, value: 'Self | Matrix | int | float'):
        if isinstance(value, Matrix):
            value = value.matrix
        
        print(type(value))
        return self.__class__(self.matrix @ value)

    def __rmatmul__(self, value: 'Self | Matrix | int | float'):
        if isinstance(value, Matrix):
            value = value.matrix
        
        print(type(value))
        return self.__class__(value @ self.matrix)
    
    def __truediv__(self, value: 'Self | Matrix | int | float'):
        if isinstance(value, Matrix):
            value = value.matrix
            
        return self.__class__(self.matrix / value)
    
    def __rtruediv__(self, value: 'Self | Matrix | int | float'):
        if isinstance(value, Matrix):
            value = value.matrix
            
        return self.__class__(value / self.matrix)
    
    def __floordiv__(self, value: 'Self | Matrix | int | float'):
        if isinstance(value, Matrix):
            value = value.matrix
            
        return self.__class__(self.matrix // value)
    
    def __floordiv__(self, value: 'Self | Matrix | int | float'):
        if isinstance(value, Matrix):
            value = value.matrix
            
        return self.__class__(value // self.matrix)
    
    def inverse(self):
        print(self.matrix)
        return self.__class__(numpy.linalg.inv(self.matrix))

class Matrix3(Matrix):
    shape = (3,3)

    
    def to_rot_size(self):
        from .vector import Vector3
        
        sizes = []
        rots = []
        
        for index in range(self.shape[0]):
            vector = Vector3(self[index])
            sizes.append(vector.size)
            rots.append(vector.normalized.array)
        
        rot = Matrix3(numpy.array(rots, dtype = numpy.float32))
        size = Vector3(numpy.array(sizes, dtype = numpy.float32))

        if numpy.linalg.det(rot.matrix) < 0:
            rot = -rot
            size = -size
        
        # rot = rot.normalized
        
        return rot, size

    @property
    def normalized(self):
        return self.__class__(self._normalized(self.matrix))
    
    def _normalized(self, matrix: numpy.ndarray):
        from .vector import Vector3
        
        matrix = matrix.copy()
        for index, row in enumerate(matrix):
            matrix[index] = Vector3(row).normalized.array
        
        return matrix
    
    def to_mat4(self):
        matrix = self.matrix
        
        # new_matrix = numpy.eye(4)
        new_matrix = numpy.array([[0] * 4] * 4, dtype = matrix.dtype.__class__)
        new_matrix[:matrix.shape[0],:matrix.shape[1]] = matrix
        # matrix = numpy.pad(matrix, ((0,1),(0,1)), 'constant', constant_values = (0))
        new_matrix[3,3] = 1
        return Matrix4(new_matrix)

    def to_quaternion(self):
        from .quaternion import Quaternion
        
        mat = self.normalized.matrix
        det = numpy.linalg.det(mat)
        
        print(f'det: {det}')
        if (det < 0):
            mat = -mat
        print(f'det: {numpy.linalg.det(mat)}')
        
        return Quaternion(self._mat3_normalized_to_quat(mat))

    def _mat3_normalized_to_quat(self, mat: numpy.ndarray):
        q = [0,0,0,0]
        
        # import scipy.spatial.transform
        # q = scipy.spatial.transform.Rotation.from_matrix(mat).as_quat(scalar_first = True)
        # return q
        
        assert numpy.any(mat >= 0), "can't be negative"
        
        trace = mat[0,0] + mat[1,1] + mat[2,2]
        quarter = 0.25
        
        if trace > 0:
            denom = numpy.sqrt(trace + 1) * 2
            q = [
                quarter * denom,
                (mat[2, 1] - mat[1, 2]) / denom,
                (mat[0, 2] - mat[2, 0]) / denom,
                (mat[1, 0] - mat[0, 1]) / denom,
            ]
        elif mat[0, 0] > (mat[1, 1]) and mat[0, 0] > mat[2, 2]:
            denom = numpy.sqrt(1 + mat[0, 0] - mat[1, 1] - mat[2, 2]) * 2.0
            q = [
                (mat[2, 1] - mat[1, 2]) / denom,
                quarter * denom,
                (mat[0, 1] + mat[1, 0]) / denom,
                (mat[0, 2] + mat[2, 0]) / denom,
            ]
        elif mat[1, 1] > mat[2, 2]:
            denom = numpy.sqrt(1 + mat[1, 1] - mat[0, 0] - mat[2, 2]) * 2.0
            q = [
                (mat[0, 2] - mat[2, 0]) / denom,
                (mat[0, 1] + mat[1, 0]) / denom,
                quarter * denom,
                (mat[1, 2] + mat[2, 1]) / denom,
            ]
        else:
            denom = numpy.sqrt(1 + mat[2, 2] - mat[0, 0] - mat[1, 1]) * 2.0
            q = [
                (mat[1, 0] - mat[0, 1]) / denom,
                (mat[0, 2] + mat[2, 0]) / denom,
                (mat[1, 2] + mat[2, 1]) / denom,
                quarter * denom,
            ]
        
        return q

        if (mat[2][2] < 0.0):
            if (mat[0][0] > mat[1][1]):
                trace = 1.0 + mat[0][0] - mat[1][1] - mat[2][2]
                s = 2.0 * numpy.sqrt(trace, dtype = numpy.float32)
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
                s = 2.0 * numpy.sqrt(trace, dtype = numpy.float32)
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
                s = 2.0 * numpy.sqrt(trace, dtype = numpy.float32)
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
                s = 2.0 * numpy.sqrt(trace, dtype = numpy.float32)
                q[0] = 0.25 * s
                s = 1.0 / s
                q[1] = (mat[1][2] - mat[2][1]) * s
                q[2] = (mat[2][0] - mat[0][2]) * s
                q[3] = (mat[0][1] - mat[1][0]) * s
                if ((trace == 1.0) and (q[1] == 0.0 and q[2] == 0.0 and q[3] == 0.0)):
                    # Avoids the need to normalize the degenerate case.
                    q[0] = 1.0
        
        return q


class Matrix4(Matrix):
    shape = (4,4)
    
    
    def decompose(self, with_rot: bool = False):
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
        
        from .quaternion import Quaternion
        
        matrix = self.matrix
        
        if matrix.shape != (4,4):
            raise ValueError('Matrix must be 4x4')
        
        loc, rot, size = self._mat4_to_loc_rot_size(matrix)
        
        # quat = Quaternion(matrix = rot)
        # We have to convert to quaternion using a different formula
        # because pyquaternion throws an error
        quat = rot.to_quaternion()
        # quat = Quaternion(w = q[0], x = q[1], y = q[2], z = q[3])
        # quat = quaternionic.array(q)
        
        result = loc, quat, size
        
        if with_rot:
            result += (rot,)
        
        return result

    def _mat4_to_loc_rot_size(self, wmat: numpy.ndarray) -> 'tuple[Vector3, Matrix3, Vector3]':
        from .vector import Vector3
        
        mat3 = Matrix3(wmat[:3,:3])
        
        rot, size = mat3.to_rot_size()
        
        loc = wmat[:3,3]
        
        return Vector3(loc), rot, size
    
    @classmethod
    def compose(
        cls,
        translation: 'Vector3',
        rotation: 'Quaternion',
        scale: 'Vector3',
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
        from .quaternion import Quaternion
        from .vector import Vector3
        

        if translation is None:
            translation = Vector3(0,0,0)
        
        mat = cls()
        
        if rotation is None:
            mat = cls(numpy.eye(4, dtype = numpy.float32))
        # elif isinstance(rotation, Quaternion):
        elif isinstance(rotation, Quaternion):
            mat = rotation.rotation_matrix.to_mat4()
        
        # decode scale
        if scale is not None:
            mat[:3,:3] *= scale.array
        
        mat[3,:3] = translation.array
        
        return cls(mat.matrix.swapaxes(1,0))

