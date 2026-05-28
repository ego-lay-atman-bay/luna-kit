import json
import os
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING
import xml.etree.ElementTree as ET

from .pvr import PVR

if TYPE_CHECKING:
    from rich.console import Console

def run_ffdec(command: list[str], ffdec_path: str = 'ffdec', **kwargs):
    if ffdec_path.endswith(".jar"):
        cmd = ["java", "-jar", ffdec_path]
    else:
        cmd = [ffdec_path]
    
    cmd += command
    
    return subprocess.run(cmd, check = True, stdout = subprocess.DEVNULL, **kwargs)

def parse_swf(swf_path: str, ffdec_path: str = 'ffdec'):
    with tempfile.NamedTemporaryFile(delete = False, suffix = '.xml') as temp:
        temp_xml = temp.name
    
    try:
            
        try:
            run_ffdec(["-swf2xml", swf_path, temp_xml], ffdec_path)
        except subprocess.CalledProcessError:
            return None

        if not os.path.exists(temp_xml):
            return None

        tree = ET.parse(temp_xml)
        root = tree.getroot()

        return root
    finally:
        if os.path.exists(temp_xml):
            os.remove(temp_xml)


def get_image_export_mappings(parsed_swf: ET.Element):
    root = parsed_swf
    
    # All variations of image tags used across Flash history
    image_tag_types = {
        "DefineBitsTag", "DefineBitsJPEG2Tag", "DefineBitsJPEG3Tag", "DefineBitsJPEG4Tag",
        "DefineBitsLosslessTag", "DefineBitsLossless2Tag"
    }
    
    image_ids = set()
    export_mappings = {}  # Format: {id: export_name}
    
    # Walk through every tag element in the SWF XML structure
    for tag in root.iter():
        tag_name = tag.get('type')
        
        # Identify image assets and gather their raw IDs
        if tag_name in image_tag_types:
            char_id = tag.attrib.get("characterID") or tag.attrib.get("id")
            if char_id:
                image_ids.add(str(char_id))
                
        # Locate the Export names mapping tables
        elif tag_name in ("ExportAssetsTag",):
            tags = tag.find('tags')
            names = tag.find('names')

            if tags is not None and names is not None:
                for tag_el, name_el in zip(tags, names):
                    sub_id = tag_el.text
                    exp_value = name_el.text
                    export_mappings[str(sub_id)] = exp_value

    # 3. Match image IDs to their corresponding exp values
    final_mapping: dict[str, str] = {}
    
    for img_id in sorted(image_ids, key=int):
        name = export_mappings.get(img_id, "N/A (No exp value assigned)")
        final_mapping[img_id] = name
    
    return final_mapping

def replace_image_tag(
    swf_in: str,
    swf_out: str,
    tag: str,
    image_file: str,
    ffdec_path: str = 'ffdec',
):
    return run_ffdec([
        '-replace', swf_in, swf_out, str(tag), image_file, 'lossless2'
    ], ffdec_path)


def export_swf_frames(swf_path: str, output: str, ffdec_path: str = 'ffdec'):
    return run_ffdec([
        '-format', 'frame:png',
        '-export', 'frame', output, swf_path,
    ], ffdec_path)

def make_webp(frames_dir: str, output_path: str, fps: float):
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-start_number", "1",
        "-i", os.path.join(frames_dir, "%d.png"),
        "-c:v", "libwebp_anim",
        "-lossless", "1",
        "-loop", "0",
        output_path
    ]
    return subprocess.run(ffmpeg_cmd, check=True, capture_output=True)


def swf2webp(swf_path: str, webp_path: str, ffdec_path: str = 'ffdec', *, console: 'Console | None' = None):
    with tempfile.TemporaryDirectory() as tempdir:
        fixed_swf = os.path.join(tempdir, 'fixed.swf')
        frames_dir = os.path.join(tempdir, 'frames')
        os.makedirs(frames_dir, exist_ok = True)

        if console: console.print('Parsing swf')
        parsed_swf = parse_swf(swf_path, ffdec_path)
        if parsed_swf is None:
            raise ValueError('Could not parse swf')
        
        fps = float(parsed_swf.get('frameRate', 24))

        images = get_image_export_mappings(parsed_swf)

        if len(images) > 1:
            if console: console.print('More than 1 images', images)
        
        image_tag = next(iter(images))
        image_name = os.path.splitext(images[image_tag])[0]
        image_path = os.path.join(os.path.dirname(swf_path), image_name)

        used_image_path = image_path + '.png'

        if os.path.exists(image_path + '.pvr'):
            image = PVR(image_path + '.pvr')
            used_image_path = os.path.join(tempdir, image_name + '.png')
            image.save(used_image_path)

        if console: console.print('Replacing image tag')
        replace_image_tag(swf_path, fixed_swf, image_tag, used_image_path, ffdec_path)

        if console: console.print('Exporting swf frames')
        export_swf_frames(fixed_swf, frames_dir, ffdec_path)

        if console: console.print('Creating webp')
        make_webp(frames_dir, webp_path, fps)

        if console: console.print(f'Saved [yellow]{webp_path}[/]')
