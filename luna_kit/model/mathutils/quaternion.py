import math
from collections.abc import Iterable
from typing import Annotated, overload, Self

import numpy
import numpy.typing


class Quaternion:
    w: float
    x: float
    y: float
    z: float
    
    @overload
    def __init__(self, w: float, x: float, y: float, z: float) -> None: ...
    @overload
    def __init__(self, vector: Iterable): ...
    def __init__(self, *args, **kwargs):
        vector: list[float] = [0,0,0,0]
        if len(args) == 1:
            vector = args[0]
        elif len(args) == 0:
            if 'vector' in kwargs:
                vector = kwargs['vector']
                vector = list(vector)
                if 'scalar' in vector:
                    vector = vector[:3]
                    vector.append(kwargs.get('scalar', 0))
                vector += [0] * (4 - len(vector))

            else:
                vector = [
                    kwargs.get('w', 0),
                    kwargs.get('x', 0),
                    kwargs.get('y', 0),
                    kwargs.get('z', 0),
                ]
        else:
            vector = args[:4]
            vector += (0,) * (4 - len(vector))
        
        self.w = float(vector[0])
        self.x = float(vector[1])
        self.y = float(vector[2])
        self.z = float(vector[3])
    
    @property
    def array(self):
        return numpy.array([self.w, self.x, self.y, self.z], dtype = numpy.float32)
    
    def __repr__(self):
        return f"{self.__class__.__name__}({self.w}, {self.x}, {self.y}, {self.z})"
    
    def __add__(self, value: 'Quaternion | int | float'):
        if isinstance(value, Quaternion):
            value = value.array
        
        return self.__class__(self.array + value)
    
    def __radd__(self, value: 'Quaternion | int | float'):
        return self.__add__(value)
    
    def __pos__(self):
        return self.copy()
    
    def __sub__(self, value: 'Quaternion | int | float'):
        if isinstance(value, Quaternion):
            value = value.array

        return self.__class__(self.array - value)
    
    def __rsub__(self, value: 'Quaternion | int | float'):
        if isinstance(value, Quaternion):
            value = value.array

        return self.__class__(value - self.array)
    
    def __neg__(self):
        return self.__rsub__(0)
    
    def __mul__(self, value: 'Quaternion | int | float'):
        if isinstance(value, Quaternion):
            value = value.array
            
        return self.__class__(self.array * value)
    
    def __rmul__(self, value: 'Quaternion | int | float'):
        return self.__mul__(value)
    
    def __matmul__(self, value: 'Quaternion | int | float'):
        if isinstance(value, Quaternion):
            return Quaternion(
                self.w * value.w - self.x * value.x - self.y * value.y - self.z * value.z,
                self.w * value.x + self.x * value.w + self.y * value.z - self.z * value.y,
                self.w * value.y - self.x * value.z + self.y * value.w + self.z * value.x,
                self.w * value.z + self.x * value.y - self.y * value.x + self.z * value.w,
            )
        
        return Quaternion(self.array @ value)

    def __rmatmul__(self, value: 'Quaternion | int | float'):
        if isinstance(self, Quaternion):
            
            return Quaternion(
                value.w * self.w - value.x * self.x - value.y * self.y - value.z * self.z,
                value.w * self.x + value.x * self.w + value.y * self.z - value.z * self.y,
                value.w * self.y - value.x * self.z + value.y * self.w + value.z * self.x,
                value.w * self.z + value.x * self.y - value.y * self.x + value.z * self.w,
            )
        
        return Quaternion(value @ self.array)
    
    def __truediv__(self, value: 'Quaternion | int | float'):
        if isinstance(value, Quaternion):
            value = value.array
            
        return self.__class__(self.array / value)
    
    def __rtruediv__(self, value: 'Quaternion | int | float'):
        if isinstance(value, Quaternion):
            value = value.array
            
        return self.__class__(value / self.array)
    
    def __floordiv__(self, value: 'Quaternion | int | float'):
        if isinstance(value, Quaternion):
            value = value.array
            
        return self.__class__(self.array // value)
    
    def __rfloordiv__(self, value: 'Quaternion | int | float'):
        if isinstance(value, Quaternion):
            value = value.array
            
        return self.__class__(value // self.array)
    
    
    def __getitem__(self, index: int | slice | str) -> numpy.float32 | numpy.typing.NDArray[numpy.float32]:
        if isinstance(index, str):
            indexes = ['w', 'x', 'y', 'z']

            if index.lower() not in indexes:
                raise KeyError(f'Invalid index: {index}')
            
            index = indexes.index(index.lower())
        
        return self.array[index]
    
    def __setitem__(self, index: int | slice | str, value: float):
        if isinstance(index, str):
            indexes = ['w', 'x', 'y', 'z']

            if index.lower() not in indexes:
                raise KeyError(f'Invalid index: {index}')
            
            index = indexes.index(index.lower())
        
        self.array[index] = value
    
    def copy(self):
        return self.__class__(
            w = self.w,
            x = self.x,
            y = self.y,
            z = self.z,
        )
    
    def flip(self):
        new = self.__class__(
            self.w,
            -self.x,
            self.y,
            -self.z,
        )
        r = Quaternion.from_euler(0, numpy.pi, 0)
        
        return r @ new
    
    def rotate(self, by: 'Quaternion'):
        length = self.length
        tquat = self.normalized
        self_rmat = tquat.rotation_matrix
        other_rmat = by.normalized.rotation_matrix
        rmat = other_rmat @ self_rmat
        quat = rmat.to_quaternion()
        quat = quat * length
        
        return quat
    
    @property
    def length(self):
        return numpy.sqrt(self.array.dot(self.array), dtype = numpy.float32)
    
    @property
    def rotation_matrix(self):
        """Convert quaternion to 3x3 matrix

        Args:
            q (numpy.ndarray): Quaternion as numpy.array([w, x, y, z])
        """
        from .matrix import Matrix3
        
        import scipy.spatial.transform
        
        return Matrix3(scipy.spatial.transform.Rotation.from_quat(self.array, scalar_first = True).as_matrix().swapaxes(1,0))
        
        q0 = q1 = q2 = q3 = qda = qdb = qdc = qaa = qab = qac = qbb = qbc = qcc = 0

        M_SQRT2 = numpy.sqrt(2, dtype = numpy.double)

        q0 = M_SQRT2 * numpy.double(self.w)
        q1 = M_SQRT2 * numpy.double(self.x)
        q2 = M_SQRT2 * numpy.double(self.y)
        q3 = M_SQRT2 * numpy.double(self.z)

        qda = q0 * q1
        qdb = q0 * q2
        qdc = q0 * q3
        qaa = q1 * q1
        qab = q1 * q2
        qac = q1 * q3
        qbb = q2 * q2
        qbc = q2 * q3
        qcc = q3 * q3

        m = numpy.array([[0] * 3] * 3)
        
        m = numpy.array([[(1.0 - qbb - qcc), (qdc + qab)      , (-qdb + qac)     ],
                        [(-qdc + qab)     , (1.0 - qaa - qcc), (qda + qbc)      ],
                        [(qdb + qac)      , (-qda + qbc)     , (1.0 - qaa - qbb)]])
        
    #     m[0,0] = (1.0 - qbb - qcc)
    #     m[0,1] = (qdc + qab)
    #     m[0,2] = (-qdb + qac)
    # 
    #     m[1,0] = (-qdc + qab)
    #     m[1,1] = (1.0 - qaa - qcc)
    #     m[1,2] = (qda + qbc)
    # 
    #     m[2,0] = (qdb + qac)
    #     m[2,1] = (-qda + qbc)
    #     m[2,2] = (1.0 - qaa - qbb)
        
        return Matrix3(m)
    
    @property
    def normalized(self):
        if self.length != 0:
            return Quaternion(*(self.array * (1 / self.length)))
        else:
            return Quaternion(0, 1, 0, 0)

    @classmethod
    def from_euler(cls, roll: float, pitch: float, yaw: float) -> 'Quaternion':
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
        
        sr = numpy.sin(roll * 0.5, dtype = numpy.float64)
        cr = numpy.cos(roll * 0.5, dtype = numpy.float64)
        sp = numpy.sin(pitch * 0.5, dtype = numpy.float64)
        cp = numpy.cos(pitch * 0.5, dtype = numpy.float64)
        sy = numpy.sin(yaw * 0.5, dtype = numpy.float64)
        cy = numpy.cos(yaw * 0.5, dtype = numpy.float64)
        
        return Quaternion(
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        )
        
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
        
        return cls(q)
        
        qx = numpy.sin(roll/2) * numpy.cos(pitch/2) * numpy.cos(yaw/2) - numpy.cos(roll/2) * numpy.sin(pitch/2) * numpy.sin(yaw/2)
        qy = numpy.cos(roll/2) * numpy.sin(pitch/2) * numpy.cos(yaw/2) + numpy.sin(roll/2) * numpy.cos(pitch/2) * numpy.sin(yaw/2)
        qz = numpy.cos(roll/2) * numpy.cos(pitch/2) * numpy.sin(yaw/2) - numpy.sin(roll/2) * numpy.sin(pitch/2) * numpy.cos(yaw/2)
        qw = numpy.cos(roll/2) * numpy.cos(pitch/2) * numpy.cos(yaw/2) + numpy.sin(roll/2) * numpy.sin(pitch/2) * numpy.sin(yaw/2)
        return Quaternion(w = qw, x = qx, y = qy, z = qz)
    