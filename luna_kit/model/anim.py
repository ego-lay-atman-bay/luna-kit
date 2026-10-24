import csv
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, BinaryIO

try:
    import dataclasses_struct as dcs
    import numpy
    from numpy.typing import NDArray
except ImportError as e:
    e.add_note('model dependencies not found')
    raise e

from ..file_utils import PathOrBinaryFile, PathOrTextFile, open_binary, open_text_file
from ..utils import read_ascii_string
from .model_common import Vector3
from .mathutils import Quaternion


@dcs.dataclass_struct(size = 'std', byteorder='little')
class Header:
    magic: Annotated[bytes, 8] = b'RKFORMAT'
    version_major: dcs.U32 = 5
    version_minor: dcs.U32 = 2
    name: Annotated[bytes, 64] = b' ' * 64
    bone_count: dcs.U32 = 0
    frame_count: dcs.U32 = 0
    frame_type: dcs.U32 = 4

@dataclass
class Animation:
    name: str
    start: int
    end: int
    fps: float

@dataclass
class AnimationRow:
    """One CSV record, including blank/invalid rows; line is its last source line."""
    line: int
    fields: list[str]
    animation: Animation | None = None
    error: str | None = None


def read_animation_csv(file: PathOrTextFile) -> list[AnimationRow]:
    """Read an explicit path or borrowed text stream without discarding records.

    Frame bounds, positive FPS, duplicate policy and clip selection belong to
    the caller. Strings are paths; use a text stream for inline CSV content.
    """
    source = (open(file, encoding='utf-8-sig', newline='')
              if isinstance(file, (str, Path)) else open_text_file(file))
    rows = []
    with source as handle:
        reader = csv.reader(handle, strict=True)
        for fields in reader:
            row = AnimationRow(reader.line_num, fields)
            if fields:
                try:
                    if len(fields) != 4 or not fields[0]:
                        raise ValueError('expected name,start,end,fps')
                    start, end, fps = int(fields[1]), int(fields[2]), float(fields[3])
                    if not math.isfinite(fps):
                        raise ValueError('non-finite FPS')
                    row.animation = Animation(fields[0], start, end, fps)
                except ValueError as error:
                    row.error = str(error)
            rows.append(row)
    return rows


@dataclass
class BoneTransformation:
    position: Vector3
    quaternion: Quaternion

    POS_FORMAT: str = '3h'
    QUAT_FORMAT: str = '1h3b'


# Packed native records have no alignment padding. Output preserves Python
# float precision; quaternion fields follow the existing WXYZ object API.
_RECORD_DTYPES = {
    0: numpy.dtype([('quaternion', '<f4', 4), ('position', '<f4', 4)]),
    1: numpy.dtype([('position', '<f4', 3), ('w', '<f4'), ('xyz', '<i2', 3)]),
    2: numpy.dtype([('position', '<i2', 3), ('w', '<i2'), ('xyz', '<i2', 3)]),
    3: numpy.dtype([('position', '<f4', 3), ('w', '<f4'), ('xyz', 'i1', 3)]),
    4: numpy.dtype([('position', '<i2', 3), ('w', '<i2'), ('xyz', 'i1', 3)]),
}
_FRAME_DTYPE = numpy.dtype([('position', numpy.float64, 3), ('quaternion', numpy.float64, 4)])
_POSITION_SCALE = 0.031250953674316406


class Anim:
    MAGIC: bytes = b'RKFORMAT'

    def __init__(self, file: PathOrBinaryFile | None = None, *,
                 csv_file: PathOrTextFile | None = None):
        self.filename = ''
        self.header = Header()
        self.name = ''
        self.animations: dict[str, Animation] = {}
        self.animation_rows: list[AnimationRow] = []
        self.raw_frames: NDArray[numpy.void] = numpy.empty((0, 0), dtype=_FRAME_DTYPE)

        if file is not None:
            self.read(file, csv_file=csv_file)
        elif csv_file is not None:
            raise ValueError('csv_file requires an ANIM input')

    def read(self, file: PathOrBinaryFile, *, csv_file: PathOrTextFile | None = None) -> None:
        self.filename = os.path.abspath(file) if isinstance(file, (str, Path)) else ''
        self.animation_rows = []
        self.animations = {}
        with open_binary(file) as open_file:
            self.header = self._read_header(open_file)
            self.raw_frames = self._read_frames(open_file)
        self.animations = self._get_animation_list(csv_file)

    def _read_header(self, file: BinaryIO) -> Header:
        raw = file.read(dcs.get_struct_size(Header))
        if len(raw) != dcs.get_struct_size(Header):
            raise ValueError('Truncated ANIM header')
        header = Header.from_packed(raw)
        if header.magic != self.MAGIC:
            raise ValueError('File is not an ANIM animation')
        if header.frame_type not in _RECORD_DTYPES:
            raise NotImplementedError(f'Unsupported ANIM frame type: {header.frame_type}')

        self.name = read_ascii_string(header.name)
        return header

    def _get_animation_list(self, csv_file: PathOrTextFile | None = None) -> dict[str, Animation]:
        if csv_file is None and self.filename:
            csv_name = Path(self.filename).parent / (self.name + '.csv')
            if csv_name.is_file():
                csv_file = csv_name
            else:
                print(f'could not find {csv_name.name}')
        if csv_file is None:
            return {}
        self.animation_rows = read_animation_csv(csv_file)
        # Convenience view: valid names keep their existing last-value behavior.
        # Consumers needing duplicate/invalid-row policy use animation_rows.
        return {row.animation.name: row.animation for row in self.animation_rows
                if row.animation is not None}

    def _read_frames(self, file: BinaryIO) -> NDArray[numpy.void]:
        kind = self.header.frame_type
        dtype = _RECORD_DTYPES[kind]
        shape = (self.header.frame_count, self.header.bone_count)
        size = shape[0] * shape[1] * dtype.itemsize
        chunks = []
        remaining = size
        while remaining:
            # Bound each read without imposing a limit on the animation size.
            chunk = file.read(min(remaining, 8 * 1024 * 1024))
            if not chunk:
                raise ValueError('Truncated ANIM bone transformation')
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
        records = numpy.frombuffer(raw, dtype=dtype).reshape(shape)
        frames = numpy.empty(shape, dtype=_FRAME_DTYPE)
        position, quaternion = frames['position'], frames['quaternion']
        if kind == 0:
            if not numpy.all(records['position'][..., 3] == 1):
                raise ValueError('Unsupported non-unit type 0 ANIM transform lane')
            position[:] = records['position'][..., :3]
            quaternion[:] = records['quaternion'][..., [3, 0, 1, 2]]
        else:
            position[:] = records['position']
            quaternion[..., 0] = records['w']
            quaternion[..., 1:] = records['xyz']
            if kind in (2, 4):
                position *= _POSITION_SCALE
                quaternion[..., 0] /= 32767
            quaternion[..., 1:] /= 32767 if kind in (1, 2) else 127
        if not numpy.isfinite(position).all() or not numpy.isfinite(quaternion).all():
            raise ValueError('Non-finite ANIM bone transformation')
        return frames

    def get_frames(self) -> list[list[BoneTransformation]]:
        """Build Python transformation objects from the current decoded array."""
        return [[BoneTransformation(Vector3(*position), Quaternion(*quaternion))
                 for position, quaternion in zip(frame['position'].tolist(), frame['quaternion'].tolist())]
                for frame in self.raw_frames]
