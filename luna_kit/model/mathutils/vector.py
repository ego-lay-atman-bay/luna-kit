try:
    import numpy
    import numpy.typing
except ImportError as e:
    e.add_note('model dependencies not found')
    raise e

from typing import Self, overload, Iterable

class Vector3:
    x: float
    y: float
    z: float
    
    @overload
    def __init__(self, x: float, y: float, z: float) -> None: ...
    @overload
    def __init__(self, vector: Iterable): ...
    def __init__(self, *args, **kwargs):
        vector = [0,0,0]
        if len(args) == 1:
            vector = args[0]
        elif len(args) == 0:
            if 'vector' in kwargs:
                vector = kwargs['vector']
            else:
                vector = [
                    kwargs.get('x', 0),
                    kwargs.get('y', 0),
                    kwargs.get('z', 0),
                ]
        else:
            vector = args[:3]
            vector += [0] * (3 - len(vector))
            
        self.x = float(vector[0])
        self.y = float(vector[1])
        self.z = float(vector[2])
    
    def copy(self):
        return self.__class__(
            x = self.x,
            y = self.y,
            z = self.z,
        )
    
    @property
    def array(self):
        return numpy.array([self.x, self.y, self.z], dtype = numpy.float32)
    
    def __repr__(self):
        return f'{self.__class__.__name__}({self.x}, {self.y}, {self.z})'
    
    def __getitem__(self, index: int | slice | str) -> numpy.float32 | numpy.typing.NDArray[numpy.float32]:
        if isinstance(index, str):
            indexes = ['x', 'y', 'z']

            if index.lower() not in indexes:
                raise KeyError(f'Invalid index: {index}')
            
            index = indexes.index(index.lower())
        
        return self.array[index]
    
    def __setitem__(self, index: int | slice | str, value: float):
        if isinstance(index, str):
            indexes = ['x', 'y', 'z']

            if index.lower() not in indexes:
                raise KeyError(f'Invalid index: {index}')
            
            index = indexes.index(index.lower())
        
        self.array[index] = value
    
    def __add__(self, value: 'Vector3 | int | float'):
        if isinstance(value, Vector3):
            value = value.array
        
        return self.__class__(self.array + value)
    
    def __radd__(self, value: 'Vector3 | int | float'):
        return self.__add__(value)
    
    def __pos__(self):
        return self.copy()
    
    def __sub__(self, value: 'Vector3 | int | float'):
        if isinstance(value, Vector3):
            value = value.array

        return self.__class__(self.array - value)
    
    def __rsub__(self, value: 'Vector3 | int | float'):
        if isinstance(value, Vector3):
            value = value.array

        return self.__class__(value -  self.array)
    
    def __neg__(self):
        return self.__rsub__(0)
    
    def __mul__(self, value: 'Vector3 | int | float'):
        if isinstance(value, Vector3):
            value = value.array
            
        return self.__class__(self.array * value)
    
    def __rmul__(self, value: 'Vector3 | int | float'):
        return self.__mul__(value)
    
    def __truediv__(self, value: 'Vector3 | int | float'):
        if isinstance(value, Vector3):
            value = value.array
            
        return self.__class__(self.array / value)

    def __rtruediv__(self, value: 'Vector3 | int | float'):
        if isinstance(value, Vector3):
            value = value.array
            
        return self.__class__(value / self.array)
    
    def __floordiv__(self, value: 'Vector3 | int | float'):
        if isinstance(value, Vector3):
            value = value.array
            
        return self.__class__(self.array // value)
    
    def __rfloordiv__(self, value: 'Vector3 | int | float'):
        if isinstance(value, Vector3):
            value = value.array
            
        return self.__class__(value // self.array)
    
    @property
    def _size(self):
        return self.array.dot(self.array)
    
    @property
    def size(self):
        size = self._size
        if self._size > 1.0e-35:
            size = numpy.sqrt(self._size)
        else:
            size = 0
        
        return size
    
    @property
    def normalized(self):
        return self._normalize(1.0)

    def _normalize(self, unit_length: float):
        # A larger value causes normalize errors in a scaled down models with camera extreme close.
        if (self._size > 1.0e-35):
            size = numpy.sqrt(self._size, dtype = numpy.float32)
            rot = self * (unit_length / size)
        else:
            rot = self.__class__(0, 0, 0)
        
        return rot
