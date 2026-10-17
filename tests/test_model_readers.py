"""Synthetic RK/ANIM regressions; no game assets are required.

Run with: python -m unittest discover -s tests
Also run with python -O to check validation without assertions.
"""
import io
from pathlib import Path
import struct
import tempfile
import unittest

from luna_kit.model import Anim, RKModel


def name(value: str, size: int = 64) -> bytes:
    return value.encode('ascii').ljust(size, b'\0')


def model_parts(face_width: int = 2) -> dict[int, tuple[int, bytes]]:
    return {
        1: (2, struct.pack('<8I', 1, 0, 0, 0, 1, 3, 0, 0)),
        2: (1, name('material', 32)),
        3: (3, b''.join(struct.pack('<5f', x, 0, 0, .25, .75) for x in (0, 1, 2))),
        4: (6, struct.pack('<6' + ('H' if face_width == 2 else 'I'), 0, 1, 2, 2, 1, 0)),
        13: (1, struct.pack('<HBB', 1026, 12, 0)),
        16: (2, name('mesh') * 2),
        17: (3, struct.pack('<4B4H', 0, 0, 0, 0, 0, 0, 0, 0) * 3),
    }


def model_bytes(parts: dict[int, tuple[int, bytes]] | None = None) -> bytes:
    parts = model_parts() if parts is None else parts
    headers, bodies, offset = [], [], 464
    for tag, (count, body) in parts.items():
        headers.append(struct.pack('<4I', tag, offset, count, len(body)))
        bodies.append(body)
        offset += len(body)
    return (struct.pack('<8sII64s', b'RKFORMAT', 5, 2, name('Synthetic'))
            + b''.join(headers).ljust(384, b'\0') + b''.join(bodies))


def animation_bytes(kind: int = 4, bones: int = 1, frames: int = 1,
                    records: bytes | None = None) -> bytes:
    header = struct.pack('<8sII64sIII', b'RKFORMAT', 5, 2, name('Synthetic'), bones, frames, kind)
    if records is None:
        record = {0: struct.pack('<8f', 0, 0, 0, 1, 1, -2, 3, 1),
                  1: struct.pack('<4f3h', 1, -2, 3, 1, 0, 0, 0),
                  4: struct.pack('<4h3b', 32, -64, 96, 32767, 0, 0, 0)}
        records = record.get(kind, record[4]) * bones * frames
    return header + records


class ModelReaderTests(unittest.TestCase):
    def test_submeshes_use_declared_face_offsets(self):
        for width in (2, 4):
            with self.subTest(width=width):
                parts = model_parts(width)
                parts[1] = (2, struct.pack('<8I', 1, 3, 0, 0, 1, 0, 0, 0))
                model = RKModel(model_bytes(parts))
                self.assertEqual([m.triangles[0].x for m in model.meshes], [2, 0])
                self.assertEqual([m.name for m in model.meshes], ['mesh', 'mesh'])
                self.assertEqual((model.verts[0].u, model.verts[0].v), (.25, .75))

    def test_rejects_bad_headers_section_bounds_and_duplicate_tags(self):
        valid = model_bytes()
        invalid = [valid[:79], valid[:448], b'BROKEN!!' + valid[8:]]
        for offset, size in ((463, 32), (len(valid), 32)):
            data = bytearray(valid)
            struct.pack_into('<4I', data, 80, 1, offset, 2, size)
            invalid.append(data)
        data = bytearray(valid)
        data[448:464] = data[80:96]
        invalid.append(data)
        for data in invalid:
            with self.subTest(header=data[:96]):
                with self.assertRaises(ValueError):
                    RKModel(data)

    def test_rejects_record_sizes_the_readers_cannot_decode(self):
        for tag, count, data in ((1, 2, b'\0' * 31), (2, 2, b'a' * 3),
                                 (3, 3, b'\0' * 33), (4, 6, b'\0' * 6),
                                 (7, 1, b'\0' * 139), (13, 1, b'\0' * 3),
                                 (16, 2, b'\0' * 127), (17, 3, b'\0' * 35)):
            with self.subTest(tag=tag):
                parts = model_parts()
                parts[tag] = (count, data)
                with self.assertRaises(ValueError):
                    RKModel(model_bytes(parts))

    def test_rejects_invalid_mesh_vertex_and_weight_references(self):
        for tag, replacement in (
            (1, (2, struct.pack('<8I', 1, 0, 1, 0, 1, 3, 0, 0))),
            (1, (2, struct.pack('<8I', 1, 6, 0, 0, 1, 3, 0, 0))),
            (4, (6, struct.pack('<6H', 0, 1, 3, 2, 1, 0))),
            (16, (1, name('mesh'))),
            (17, (2, b'\0' * 24)),
        ):
            with self.subTest(tag=tag, replacement=replacement):
                parts = model_parts()
                parts[tag] = replacement
                with self.assertRaises(ValueError):
                    RKModel(model_bytes(parts))

    def test_uvs_stay_within_vertex_records(self):
        for offset in (0, 13):
            with self.subTest(offset=offset):
                parts = model_parts()
                parts[13] = (1, struct.pack('<HBB', 1026, offset, 0))
                with self.assertRaises(ValueError):
                    RKModel(model_bytes(parts))
        parts = model_parts()
        parts[13] = (1, struct.pack('<HBB', 1030, 12, 0))
        parts[3] = (3, struct.pack('<3f2H', 0, 0, 0, 0, 65535) * 3)
        self.assertEqual(RKModel(model_bytes(parts)).verts[0].v, 2)

    def test_optional_attributes_skin_and_opaque_sections(self):
        parts = model_parts()
        for tag in (13, 17):
            del parts[tag]
        parts[3] = (3, struct.pack('<3f', 0, 0, 0) * 3)
        parts[999] = (5, b'opaque')
        model = RKModel(model_bytes())
        model.read(model_bytes(parts))
        self.assertEqual(len(model.meshes), 2)
        self.assertEqual([(v.u, v.v, v.bones) for v in model.verts], [(0, 0, [])] * 3)
        self.assertEqual(RKModel(model_bytes({3: (0, b''), 4: (0, b'')})).verts, [])
        # Empty geometry may retain attribute and submesh metadata.
        parts = {1: (1, struct.pack('<4I', 0, 0, 0, 0)), 2: (1, name('material')),
                 13: (1, struct.pack('<HBB', 1026, 12, 0)), 16: (1, name('mesh'))}
        self.assertEqual(RKModel(model_bytes(parts)).meshes, [])


class AnimationReaderTests(unittest.TestCase):
    def test_type4_values_are_preserved(self):
        pose = Anim(animation_bytes()).frames[0][0]
        self.assertEqual((pose.position.x, pose.position.y, pose.position.z), (1, -2, 3))
        self.assertEqual((pose.quaternion.w, pose.quaternion.x, pose.quaternion.y, pose.quaternion.z), (1, 0, 0, 0))

    def test_float_types_preserve_values_and_frame_bone_order(self):
        for kind in (0, 1):
            with self.subTest(kind=kind):
                if kind == 0:
                    first = struct.pack('<8f', .25, -.5, .75, -1, -32.75, .5, 1200.125, 1)
                    second = struct.pack('<8f', 0, 1, 0, 0, 5, -9, 1, 1)
                    first_quaternion = (-1, .25, -.5, .75)
                else:
                    first = struct.pack('<4f3h', -32.75, .5, 1200.125, -.25, 32767, -32768, 16384)
                    second = struct.pack('<4f3h', 5, -9, 1, 0, 0, 32767, 0)
                    first_quaternion = (-.25, 1, -32768 / 32767, 16384 / 32767)
                animation = Anim(animation_bytes(kind, bones=2, frames=2,
                                                 records=first + second + second + first))
                self.assertEqual([len(frame) for frame in animation.frames], [2, 2])
                for frame, bone in ((0, 0), (1, 1)):
                    pose = animation.frames[frame][bone]
                    self.assertEqual((pose.position.x, pose.position.y, pose.position.z), (-32.75, .5, 1200.125))
                    self.assertEqual((pose.quaternion.w, pose.quaternion.x, pose.quaternion.y, pose.quaternion.z), first_quaternion)
                for frame, bone in ((0, 1), (1, 0)):
                    pose = animation.frames[frame][bone]
                    self.assertEqual((pose.position.x, pose.position.y, pose.position.z), (5, -9, 1))
                    self.assertEqual((pose.quaternion.w, pose.quaternion.x, pose.quaternion.y, pose.quaternion.z), (0, 0, 1, 0))

    def test_empty_dimensions_are_preserved(self):
        for kind in (0, 1, 4):
            for bones, frames in ((0, 1), (1, 0)):
                with self.subTest(kind=kind, bones=bones, frames=frames):
                    self.assertEqual(Anim(animation_bytes(kind, bones, frames)).frames,
                                     [[]] if frames else [])

    def test_other_frame_types_are_not_decoded_as_type4(self):
        for kind in (2, 3, 99):
            with self.subTest(kind=kind):
                with self.assertRaises(NotImplementedError):
                    Anim(animation_bytes(kind))

    def test_rejects_bad_magic_and_truncated_header_or_pose(self):
        valid = animation_bytes()
        for data in (valid[:91], b'BROKEN!!' + valid[8:], valid[:97], valid[:-1]):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    Anim(data)

    def test_rejects_truncated_float_records_and_nonunit_type0_lane(self):
        for kind in (0, 1):
            valid = animation_bytes(kind, frames=2)
            for end in (100, len(valid) - 1):
                with self.subTest(kind=kind, end=end):
                    with self.assertRaises(ValueError):
                        Anim(valid[:end])
        for lane in (0, 2, float('nan')):
            with self.subTest(lane=lane):
                record = struct.pack('<8f', 0, 0, 0, 1, 1, 2, 3, lane)
                with self.assertRaises(ValueError):
                    Anim(animation_bytes(0, records=record))

    def test_rejects_nonfinite_float_transforms(self):
        layouts = (
            (0, '<8f', [0, 0, 0, 1, 1, -2, 3, 1], range(7)),
            (1, '<4f3h', [1, -2, 3, 1, 0, 0, 0], range(4)),
        )
        for kind, record_format, values, float_lanes in layouts:
            for lane in float_lanes:
                for value in (float('nan'), float('inf'), -float('inf')):
                    with self.subTest(kind=kind, lane=lane, value=value):
                        invalid = values.copy()
                        invalid[lane] = value
                        record = struct.pack(record_format, *invalid)
                        with self.assertRaises(ValueError):
                            Anim(animation_bytes(kind, records=record))

    def test_stream_position_trailing_bytes_and_nonseekable_input(self):
        class NonSeekable(io.BytesIO):
            def seek(self, *args):
                raise io.UnsupportedOperation('not seekable')

        for kind in (0, 1, 4):
            with self.subTest(kind=kind):
                source = io.BytesIO(b'prefix' + animation_bytes(kind) + b'trailer')
                source.seek(6)
                self.assertEqual(len(Anim(source).frames), 1)
                self.assertEqual(source.read(), b'trailer')
                self.assertFalse(source.closed)
                source = NonSeekable(animation_bytes(kind) + b'trailer')
                self.assertEqual(len(Anim(source).frames), 1)
                self.assertEqual(source.read(), b'trailer')
                with self.assertRaises(ValueError):
                    Anim(NonSeekable(animation_bytes(kind)[:-1]))

    def test_csv_ranges_and_fps_stay_independent_of_frame_type(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'different-filename.anim'
            (Path(folder) / 'Synthetic.csv').write_text('idle,0,0,12.5\nmove,1,1,30\n')
            for kind in (0, 1, 4):
                with self.subTest(kind=kind):
                    path.write_bytes(animation_bytes(kind, frames=2))
                    animation = Anim(str(path))
                    self.assertEqual([(a.name, a.start, a.end, a.fps)
                                      for a in animation.animations.values()],
                                     [('idle', 0, 0, 12.5), ('move', 1, 1, 30)])
                    animation.read(path.read_bytes())
                    self.assertEqual(animation.animations, {})


if __name__ == '__main__':
    unittest.main()
