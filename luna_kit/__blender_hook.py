"""
+------------------------------------------+
| THIS FILE IS MEANT FOR INTERNAL USE ONLY |
+------------------------------------------+

This file will be ran by blender as if it's just this file. The other files in
this module are not going to be able to be imported.

"""
try:
    import bpy
    
    from mathutils import *
    from math import *
except:
    raise ImportError(f'{__name__} is for internal use only')

import sys
from pathlib import Path
import argparse

def dae_import_mesh(filepath):
    bpy.ops.wm.collada_import(
        filepath = str(Path(filepath).resolve()),
    )

def create_driver(obj: bpy.types.Object):
    driver: bpy.types.FCurve = obj.driver_add('rotation_euler', 2)

    driver.driver.expression = f'frame/{bpy.context.scene.render.fps}'

def scale_obj(obj: bpy.types.Object, factor: float = 0.1):
    obj.scale = Vector([factor, -factor, factor])

def create_args() -> argparse.ArgumentParser:
    argparser = argparse.ArgumentParser()

    argparser.add_argument(
        'file',
    )
    
    argparser.add_argument(
        '--no-scale',
        dest = 'scale',
        action = 'store_false',
    )
    
    argparser.add_argument(
        '--armature',
        dest = 'armature',
        default = 'Armature',
    )
    
    return argparser

def parse_args(args: list[str], argparser: argparse.ArgumentParser):
    parsed = argparser.parse_args(args)

    dae_import_mesh(parsed.file)
    
    armature = parsed.armature
    
    if parsed.scale:
        scale_obj(bpy.data.objects[armature])
    

if __name__ == "__main__":
    # bpy.ops.wm.read_factory_settings(use_empty=True)
    
    if '--' in sys.argv:
        args = sys.argv[sys.argv.index('--'):]
        
        argparser = create_args()
        parse_args(args, argparser)
    else:
        print('This file is meant for internal use only.')
