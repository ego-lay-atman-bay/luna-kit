from dataclasses import dataclass, replace
from glob import glob
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Self
import weakref
import xml.etree.ElementTree as ET

try:
    from PIL import Image

    from .pvr import PVR
except ImportError as e:
    e.add_note('swf dependencies not found')
    raise e


SHAPE_TAGS = {"DefineShapeTag", "DefineShape2Tag", "DefineShape3Tag", "DefineShape4Tag"}
BITMAP_TAGS = {
    "DefineBitsLosslessTag", "DefineBitsLossless2Tag",
    "DefineBitsTag", "DefineBitsJPEG2Tag", "DefineBitsJPEG3Tag", "DefineBitsJPEG4Tag",
}
_ATLAS_EXTENSIONS = ('.tga', '.pvr', '.png')

# Twips per shape pixel (1/20 of a pixel).
_TWIPS = 20


@dataclass
class BitmapDef:
    character_id: int
    width: int | None
    height: int | None
    export_name: str | None = None


@dataclass
class ShapeFill:
    bitmap_id: int = 0
    sx: float = 0
    sy: float = 0
    tx: float = 0
    ty: float = 0
    rot0: float = 0
    rot1: float = 0
    x0: int = 0
    y0: int = 0
    x1: int = 0
    y1: int = 0


@dataclass
class Shape:
    shape_id: int
    bounds: tuple[int, int, int, int]  # (Xmin, Xmax, Ymin, Ymax) in twips
    fills: list[ShapeFill]


def build_dir_index(dir: str | Path) -> dict[str, Path]:
    index = {}
    for p in Path(dir).iterdir():
        if p.is_file():
            index[p.name.lower()] = p
    return index


class SWF:
    ffdec_path: str
    swf_path: Path
    _xml: ET.Element | None

    _work_dir: Path

    _MAIN_SWF_NAME: str = 'file.swf'

    def __init__(
        self,
        swf_file: str | Path,
        *,
        ffdec: str | Path = 'ffdec',
    ) -> None:
        """
        This is a class that provides info about swf files, and some
        high level operations on them, such as fixing a swf
        and rendering to a webp.

        Args:
            swf_file (str | Path): Input swf file
            ffdec (str | Path, optional): Path to ffdec, can be jar or executable. Defaults to 'ffdec'.

        Raises:
            FileNotFoundError: The swf file does not exist
            ValueError: The swf file cannot be parsed
        """
        
        if isinstance(ffdec, Path):
            ffdec = str(ffdec)
        
        self.ffdec_path = ffdec
        self.swf_path = Path(swf_file)
        self.export_names: dict[int, str] = {}
        self.bitmaps: dict[int, BitmapDef] = {}
        self.shapes: dict[int, Shape] = {}
        self.sprite_labels: dict[int, dict[str, dict[int, int]]] = {}
        self.sprite_frame0: dict[int, dict[int, int]] = {}
        self.images: dict[str, Image.Image] = {}
        self._atlas_image_cache: dict[str, Image.Image] = {}
        self._portrait_cache: dict[str, Image.Image] = {}


        if not self.swf_path.is_file():
            raise FileNotFoundError(f'Cannot find "{self.swf_path}"')
        
        self._work_dir = Path(tempfile.mkdtemp(prefix = f'luna_kit_swf_{self.swf_path.stem}_'))
        self._finalize = weakref.finalize(self, shutil.rmtree, self._work_dir, ignore_errors=True)
        
        shutil.copyfile(self.swf_path, self._work_dir/self._MAIN_SWF_NAME)
        
        self._xml = self._to_xml(self._work_dir/self._MAIN_SWF_NAME)
        if self._xml is None:
            raise ValueError('Cannot parse swf')
        
        self._read()
        self._load_images()
        
    def cleanup(self):
        self._finalize()
        # shutil.rmtree(self._work_dir, ignore_errors = True)
    
    def __enter__(self) -> Self:
        return self
    
    def __exit__(self, exc_type, exc_val, exc_traceback):
        self.cleanup()
    
    def _ffdec_run(self, command: list[str], **kwargs):
        ffdec_path = str(self.ffdec_path)
        
        if ffdec_path.endswith(".jar"):
            cmd = ["java", "-jar", ffdec_path]
        else:
            cmd = [ffdec_path]
        
        cmd += command
        
        return subprocess.run(cmd, check = True, stdout = subprocess.DEVNULL, **kwargs)
    
    def _to_xml(self, swf_path: str | Path):
        with tempfile.NamedTemporaryFile(delete = False, suffix = '.xml') as temp:
            temp_xml = temp.name
        
        try:
            self._ffdec_run(["-swf2xml", str(swf_path), temp_xml])

            if not os.path.exists(temp_xml):
                return None

            tree = ET.parse(temp_xml)
            root = tree.getroot()

            return root
        except subprocess.CalledProcessError:
            return None
        finally:
            if os.path.exists(temp_xml):
                os.remove(temp_xml)
    
    def _read(self):
        if self._xml is None:
            return
        
        for item in self._xml.iter("item"):
            if item.get("type") in ("ExportAssetsTag", "SymbolClassTag"):
                tags_el, names_el = item.find("tags"), item.find("names")
                if tags_el is None or names_el is None:
                    continue
                for cid_el, name_el in zip(tags_el, names_el):
                    if cid_el.text is None or name_el.text is None:
                        continue
                    self.export_names[int(cid_el.text)] = name_el.text
        

        for item in self._xml.iter("item"):
            char_tag = item.get("type")
            if char_tag in BITMAP_TAGS:
                cid = item.get("characterID") or item.get("characterId")
                if cid is None:
                    continue

                cid = int(cid)
                w, h = item.get("bitmapWidth"), item.get("bitmapHeight")
                self.bitmaps[cid] = BitmapDef(
                    cid, int(w) if w else None, int(h) if h else None,
                    self.export_names.get(cid),
                )

            elif char_tag in SHAPE_TAGS:
                sid = item.get("shapeId")
                if not sid:
                    continue
                sid = int(sid)

                shape = self._parse_shape(item)
                if shape is not None:
                    shape.shape_id = sid
                    self.shapes[sid] = shape
            
            elif char_tag == "DefineSpriteTag":
                sid = item.get("spriteId")
                if not sid:
                    continue
                sid = int(sid)
                
                labels, frame0 = self._parse_sprite(item)
                self.sprite_labels[sid] = labels
                self.sprite_frame0[sid] = frame0
    
    def _parse_fill_styles(self, fills_el: ET.Element | None) -> list[ShapeFill]:
        """
        Parse a FILLSTYLE array into ShapeFill(bitmapId, sx, sy, tx, ty, rot0, rot1).
        Non-bitmap fills get bitmapId 0 and are skipped at render time.
        """
        out: list[ShapeFill] = []
        if fills_el is None:
            return out
        for fs in fills_el.findall('item[@type="FILLSTYLE"]'):
            mtx = fs.find('bitmapMatrix')
            if mtx is None:
                out.append(ShapeFill(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
                continue

            sx = float(mtx.get('scaleX', 1.0)) if mtx.get('hasScale') == 'true' else 1.0
            sy = float(mtx.get('scaleY', 1.0)) if mtx.get('hasScale') == 'true' else 1.0
            rot0 = float(mtx.get('rotateSkew0', 0.0)) if mtx.get('hasRotate') == 'true' else 0.0
            rot1 = float(mtx.get('rotateSkew1', 0.0)) if mtx.get('hasRotate') == 'true' else 0.0
            tx = float(mtx.get('translateX', 0.0))
            ty = float(mtx.get('translateY', 0.0))

            out.append(ShapeFill(int(fs.get('bitmapId', '-1')), sx, sy, tx, ty, rot0, rot1))
        return out

    def _parse_shape(self, item: ET.Element) -> Shape | None:
        """
        Parse a DefineShape tag into a `Shape` with one `ShapeFill` per
        filled path.
        """
        shapes_el = item.find("shapes")
        bounds_el = item.find("shapeBounds")
        if shapes_el is None or bounds_el is None:
            return None

        xmin, xmax = int(bounds_el.get("Xmin", 0)), int(bounds_el.get("Xmax", 0))
        ymin, ymax = int(bounds_el.get("Ymin", 0)), int(bounds_el.get("Ymax", 0))

        cur_fills = self._parse_fill_styles(shapes_el.find("fillStyles/fillStyles"))

        fills: list[ShapeFill] = []
        cx = cy = 0
        cur: ShapeFill | None = None
        for rec in shapes_el.findall('shapeRecords/item'):
            rt = rec.get('type')
            if rt == 'StyleChangeRecord':
                if rec.get('stateNewStyles') == 'true':
                    cur_fills = self._parse_fill_styles(rec.find('fillStyles/fillStyles'))
                if rec.get('stateMoveTo') == 'true':
                    cx = int(rec.get('moveDeltaX') or 0)
                    cy = int(rec.get('moveDeltaY') or 0)
                new_fill = None
                if rec.get('stateFillStyle1') == 'true' and int(rec.get('fillStyle1', 0)) > 0:
                    new_fill = cur_fills[int(rec.attrib['fillStyle1']) - 1]
                elif rec.get('stateFillStyle0') == 'true' and int(rec.get('fillStyle0', 0)) > 0:
                    new_fill = cur_fills[int(rec.attrib['fillStyle0']) - 1]
                if new_fill is not None:
                    if cur is not None:
                        fills.append(cur)
                    cur = ShapeFill(
                        bitmap_id = new_fill.bitmap_id,
                        sx = new_fill.sx,
                        sy = new_fill.sy,
                        tx = new_fill.tx,
                        ty = new_fill.ty,
                        rot0 = new_fill.rot0,
                        rot1 = new_fill.rot1,
                        x0 = cx,
                        y0 = cy,
                        x1 = cx,
                        y1 = cy
                    )
            elif rt == 'StraightEdgeRecord':
                cx += int(rec.get('deltaX') or 0)
                cy += int(rec.get('deltaY') or 0)
                if cur is not None:
                    cur = replace(
                        cur,
                        x0 = min(cur.x0, cx), x1 = max(cur.x1, cx),
                        y0 = min(cur.y0, cy), y1 = max(cur.y1, cy),
                    )
            elif rt == 'CurvedEdgeRecord':
                pcx = cx + int(rec.get('controlDeltaX') or 0)
                pcy = cy + int(rec.get('controlDeltaY') or 0)
                cx += int(rec.get('anchorDeltaX') or 0)
                cy += int(rec.get('anchorDeltaY') or 0)
                if cur is not None:
                    for (px, py) in ((pcx, pcy), (cx, cy)):
                        cur = replace(
                            cur,
                            x0 = min(cur.x0, px), x1 = max(cur.x1, px),
                            y0 = min(cur.y0, py), y1 = max(cur.y1, py),
                        )
            elif rt == 'EndShapeRecord':
                if cur is not None:
                    fills.append(cur)
                    cur = None
        return Shape(0, (xmin, xmax, ymin, ymax), fills)
    
    def _parse_sprite(self, sprite_item: ET.Element) -> tuple[dict[str, dict[int, int]], dict[int, int]]:
        subtags = sprite_item.find("subTags")
        labels: dict[str, dict[int, int]] = {}
        if subtags is None:
            return labels, {}

        depth_state: dict[int, int] = {}
        pending_labels: list[str] = []
        frame0: dict[int, int] | None = None

        for tag in subtags:
            tag_type = tag.get("type")
            if tag_type == "FrameLabelTag":
                if (name := tag.get("name")):
                    pending_labels.append(name)
            elif tag_type == "PlaceObject2Tag":
                if tag.get("placeFlagHasCharacter") == "true":
                    if ((depth := tag.get("depth")) is not None and (cid := tag.get("characterId")) is not None):
                        depth_state[int(depth)] = int(cid)
            elif tag_type == "RemoveObject2Tag":
                if (depth := tag.get("depth")) is not None:
                    depth_state.pop(int(depth), None)
            elif tag_type == "ShowFrameTag":
                if frame0 is None:
                    frame0 = dict(depth_state)
                if pending_labels:
                    snap = dict(depth_state)
                    for lbl in pending_labels:
                        labels[lbl] = snap
                    pending_labels = []

        return labels, (frame0 or {})
    

    def _load_images(self):
        index = build_dir_index(self.swf_path.parent)
        for bitmap in self.bitmaps.values():
            if not bitmap.export_name:
                continue
            
            stem = Path(bitmap.export_name).stem

            image: Image.Image | None = None

            for ext in _ATLAS_EXTENSIONS:
                path = index.get(f'{stem}{ext}'.lower())
                if path:
                    if ext == '.pvr':
                        image = PVR(path).image
                    else:
                        image = Image.open(path)
                
                if image is not None:
                    image.save(self._work_dir/f'{stem}.png')
                    # image.close()
                    # self.images[name] = Image.open(self._work_dir/f'{stem}.png')
                    break
    
    def _atlas_path(self, bitmap_id: int) -> Path | None:
        bmp = self.bitmaps.get(bitmap_id)
        if bmp is None or not bmp.export_name:
            return None
        path = (self._work_dir / bmp.export_name).with_suffix('.png')
        return path if path.is_file() else None
    

    def _get_atlas_image(self, bitmap_id: int) -> Image.Image | None:
        bitmap = self.bitmaps.get(bitmap_id)
        if not bitmap or not bitmap.export_name:
            return
        
        if bitmap.export_name in self._atlas_image_cache:
            return self._atlas_image_cache[bitmap.export_name]

        path = self._atlas_path(bitmap_id)
        if path is None:
            return None

        image = Image.open(path)
        self._atlas_image_cache[bitmap.export_name] = image
        return image

    # label/shape resolution

    def _resolve_shape(self, character_id: int, _seen: set[int] | None = None) -> Shape | None:
        """
        Resolve a characterId to a Shape, descending into nested sprites
        (a placed character can itself be a movie clip that just wraps a
        single image shape, e.g. simple single-frame MovieClip symbols).
        """
        _seen = _seen or set()
        if character_id in _seen:
            return None
        _seen.add(character_id)

        if character_id in self.shapes:
            return self.shapes[character_id]
        if character_id in self.sprite_frame0:
            for depth in sorted(self.sprite_frame0[character_id]):
                shape = self._resolve_shape(self.sprite_frame0[character_id][depth], _seen)
                if shape:
                    return shape
        return None
    
    def _shape_for_label(self, label: str) -> Shape | None:
        for labels in self.sprite_labels.values():
            snap = labels.get(label)
            if not snap:
                continue
            for depth in sorted(snap):
                shape = self._resolve_shape(snap[depth])
                if shape:
                    return shape
        return None

    def all_labels(self) -> list[str]:
        names = set[str]()
        for labels in self.sprite_labels.values():
            names.update(labels.keys())
        return list(names)

    # portrait rendering

    def render_shape(self, shape: Shape) -> Image.Image:
        """
        Render a shape to an RGBA image the size of its bounds (in pixels).
        """
        Xmin, Xmax, Ymin, Ymax = shape.bounds
        out_w = max(1, int(round((Xmax - Xmin) / _TWIPS)))
        out_h = max(1, int(round((Ymax - Ymin) / _TWIPS)))
        canvas = Image.new('RGBA', (out_w, out_h), (0, 0, 0, 0))

        for f in shape.fills:
            if f.bitmap_id in (0, 65535):
                continue
            if abs(f.rot0) > 1e-9 or abs(f.rot1) > 1e-9:
                continue
            if f.sx == 0 or f.sy == 0:
                continue

            atlas = self._get_atlas_image(f.bitmap_id)
            if atlas is None:
                continue

            pw = max(1, round((f.x1 - f.x0) / _TWIPS))
            ph = max(1, round((f.y1 - f.y0) / _TWIPS))

            u0 = (f.x0 - f.tx) / f.sx
            u1 = (f.x1 - f.tx) / f.sx
            v0 = (f.y0 - f.ty) / f.sy
            v1 = (f.y1 - f.ty) / f.sy
            box = (min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1))

            crop = atlas.resize((pw, ph), Image.Resampling.BILINEAR, box=box)
            if f.sx < 0:
                crop = crop.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if f.sy < 0:
                crop = crop.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

            px = round((f.x0 - Xmin) / _TWIPS)
            py = round((f.y0 - Ymin) / _TWIPS)
            canvas.alpha_composite(crop, (px, py))

        return canvas

    def get_portrait(self, label: str) -> Image.Image | None:
        """
        Render the portrait for a frame label (e.g. a PonyID from
        `cinematictable.xml`) straight out of the atlas. Returns None if the
        label doesn't exist in this swf or its atlas image can't be found.
        """
        if label in self._portrait_cache:
            return self._portrait_cache[label]

        shape = self._shape_for_label(label)
        if shape is None:
            return None

        image = self.render_shape(shape)
        self._portrait_cache[label] = image
        return image

    # image tag replacement

    def replace_image_tag(
        self,
        tag: int | str,
        image_file: str | Path,
        swf_in: str | Path | None = None,
        swf_out: str | Path | None = None,
    ):
        if swf_in is None:
            swf_in = self._work_dir/self._MAIN_SWF_NAME
        if swf_out is None:
            swf_out = self._work_dir/self._MAIN_SWF_NAME
        
        same_file = swf_in == swf_out
        
        real_out = self._work_dir/'temp_replace.swf' if same_file else Path(swf_out)
    
        self._ffdec_run([
            '-replace', str(swf_in), str(real_out), str(tag), str(image_file), 'lossless2'
        ])

        if same_file:
            shutil.move(real_out, swf_out)
            if real_out.is_file():
                os.remove(real_out)
    
    def replace_image_tags(
        self,
        image_map: dict[int, str | Path],
        swf_in: str | Path | None = None,
        swf_out: str | Path | None = None,
    ):
        """
        Batch replaces image tags in an swf. The `image_map` is a map of
        character tag to image path. The image path is exactly what is used,
        so it does not automatically convert pvr files or find any files.

        Args:
            image_map (dict[str  |  int, str | pathlib.Path]): Character tag to image path
            ffdec_path (str | pathlib.Path, optional): Path to ffdec.jar or entry script. Defaults to 'ffdec'.
            swf_in (str | pathlib.Path | None): Input swf file. Defaults to temp working swf.
            swf_out (str | pathlib.Path | None): Output swf file. Defaults to temp working swf.
        """
        if swf_in is None:
            swf_in = self._work_dir/self._MAIN_SWF_NAME
        if swf_out is None:
            swf_out = self._work_dir/self._MAIN_SWF_NAME
        
        with tempfile.TemporaryDirectory() as tempdir:
            main_path = Path(tempdir, 'main.swf')
            edit_path = Path(tempdir, 'edit.swf')

            shutil.copyfile(swf_in, main_path)

            for tag, path in image_map.items():
                self.replace_image_tag(tag, path, main_path, edit_path)
                shutil.move(edit_path, main_path)
            
            shutil.copyfile(main_path, swf_out)
    
    def fix(self):
        image_map: dict[int, str | Path] = {}
        for cid in self.bitmaps:
            if (path := self._atlas_path(cid)) is not None:
                image_map[cid] = path
        
        self.replace_image_tags(image_map)
        
    # rendering
    
    def export_frames(
        self,
        output: str | Path,
        swf_path: str | Path | None = None,
    ):
        if swf_path is None:
            swf_path = self._work_dir/self._MAIN_SWF_NAME
        
        return self._ffdec_run([
            '-format', 'frame:png',
            '-ignorebackground',
            '-export', 'frame', str(output), str(swf_path),
        ])
    
    def render_webp(
        self,
        output_path: str | Path,
        fps: float | None = None,
        lossless: bool = True,
        extra_args: list[str] | None = None,
    ):
        """
        Render swf to webp. This expects `.fix()` to be called beforehand,
        otherwise the image will be blank. This function requires `ffmpeg` to
        be installed on the PATH, otherwise it will error.

        Args:
            output_path (str | Path): Output webp path
            fps (float | None, optional): The fps. Defaults to swf fps.
            lossless (bool, optional): Whether it's lossless or lossy. Defaults to True.
            extra_args (list[str] | None, optional): Extra arguments to pass into ffmpeg. Defaults to None.

        Returns:
            CompletedProcess[bytes]: Subprocess result
        """
        with tempfile.TemporaryDirectory() as frames_dir:
            self.export_frames(frames_dir)

            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps or self.fps),
                "-start_number", "1",
                "-i", os.path.join(frames_dir, "%d.png"),
                "-c:v", "libwebp_anim",
                "-lossless", "1" if lossless else "0",
                "-loop", "0",
                str(output_path),
            ]

            if extra_args is not None:
                ffmpeg_cmd += extra_args
            
            return subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

    # persistence

    def save(self, dest: str | Path | None = None):
        """
        Save edited swf

        Args:
            dest (str | Path | None, optional): Destination path. Defaults to original swf file.
        """

        if dest is None:
            dest = self.swf_path
        
        shutil.copyfile(self._work_dir/self._MAIN_SWF_NAME, dest)

    @property
    def xml(self) -> ET.Element | None:
        return self._xml
    
    @property
    def fps(self) -> float:
        if self.xml is None:
            return 0
        return float(self.xml.get('frameRate', 24))
