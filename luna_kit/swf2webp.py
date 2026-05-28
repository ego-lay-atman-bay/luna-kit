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

def parse_swf(swf_path: str, *, ffdec_path: str = 'ffdec'):
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
        elif tag_name in ("ExportAssetsTag", "SymbolClassTag"):
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
        name = export_mappings.get(img_id, None)
        final_mapping[img_id] = name
    
    return final_mapping

def replace_image_tag(
    swf_in: str,
    swf_out: str,
    tag: str | int,
    image_file: str,
    *,
    ffdec_path: str = 'ffdec',
):
    return run_ffdec([
        '-replace', swf_in, swf_out, str(tag), image_file, 'lossless2'
    ], ffdec_path)

def replace_image_tags(
    swf_in: str,
    swf_out: str,
    image_map: dict[str | int, str],
    *,
    ffdec_path: str = 'ffdec',
):
    """
    Batch replaces image tags in an swf. The `image_map` is a map of
    character tag to image path. The image path is exactly what is used,
    so it does not automatically convert pvr files or find any files.

    Args:
        swf_in (str): Input swf file
        swf_out (str): Output swf file
        image_map (dict[str  |  int, str]): Character tag to image path
        ffdec_path (str, optional): Path to ffdec.jar or entry script. Defaults to 'ffdec'.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        main_path = os.path.join(tempdir, 'main.swf')
        edit_path = os.path.join(tempdir, 'edit.swf')

        shutil.copyfile(swf_in, main_path)

        for tag, path in image_map.items():
            replace_image_tag(main_path, edit_path, tag, path, ffdec_path = ffdec_path)
            shutil.copyfile(edit_path, main_path)
        
        shutil.copyfile(main_path, swf_out)


def export_swf_frames(swf_path: str, output: str, *, ffdec_path: str = 'ffdec'):
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


def swf2webp(swf_path: str, webp_path: str, *, ffdec_path: str = 'ffdec', console: 'Console | None' = None):
    with tempfile.TemporaryDirectory() as tempdir:
        fixed_swf = os.path.join(tempdir, 'fixed.swf')
        temp_swf = os.path.join(tempdir, 'temp.swf')
        frames_dir = os.path.join(tempdir, 'frames')
        os.makedirs(frames_dir, exist_ok = True)

        shutil.copyfile(swf_path, fixed_swf)

        if console: console.print('Parsing swf')
        parsed_swf = parse_swf(fixed_swf, ffdec_path = ffdec_path)
        if parsed_swf is None:
            raise ValueError('Could not parse swf')
        
        fps = float(parsed_swf.get('frameRate', 24))

        images = get_image_export_mappings(parsed_swf)

        image_map = {}

        for tag, image_name in images.items():
            image_name = os.path.splitext(image_name)[0]
            new_path = os.path.join(tempdir, image_name + '.png')

            original_path = os.path.join(os.path.dirname(swf_path), image_name)
            for extension in ['.tga', '.pvr', '.png']:
                if os.path.exists(original_path + extension):
                    break
            
            if extension == '.pvr':
                image = PVR(original_path + extension)
                image.save(new_path)
            else:
                new_path = os.path.join(tempdir, image_name + extension)
                shutil.copyfile(original_path + extension, new_path)
            
            image_map[tag] = new_path

        if console: console.print('Replacing image tags')
        replace_image_tags(fixed_swf, fixed_swf, image_map, ffdec_path = ffdec_path)

        if console: console.print('Exporting swf frames')
        export_swf_frames(fixed_swf, frames_dir, ffdec_path = ffdec_path)

        if console: console.print('Creating webp')
        make_webp(frames_dir, webp_path, fps)

        if console: console.print(f'Saved [yellow]{webp_path}[/]')
