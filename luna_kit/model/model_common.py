from dataclasses import dataclass

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
