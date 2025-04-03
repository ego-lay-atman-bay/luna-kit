from argparse import ArgumentParser, Namespace
from .cli import CLI, CLICommand
from ._actions import GlobFiles

@CLI.register_command
class AtlasCommand(CLICommand):
    COMMAND = 'atlas'
    HELP = 'Extract .texatlas files.'

    @classmethod
    def build_args(cls, parser: ArgumentParser):
        parser.add_argument(
            'files',
            nargs = '+',
            action = GlobFiles,
            help = 'input .texatlas file(s)',
        )
        
        parser.add_argument(
            '-s', '--search-folders',
            dest = 'search_folders',
            nargs = '+',
            help = 'additional folders to look for the atlas images in. This defaults to the current working directory.',
        )
        
        parser.add_argument(
            '-ds', '--disable-smart-search',
            dest = 'smart_search',
            action = 'store_false',
            help = 'Smart search searches the folders that the .texatlas file is located in to find the atlas image. Disabling this will only search the current working directory (or additional search paths).',
        )
        
        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'Output folder to save images to. If omitted, the files will save to their location that they would be in the folder the .texatlas file was in.',
        )
        
        parser.add_argument(
            '-e', '--override-existing',
            dest = 'override_existing',
            action = 'store_true',
            help = "By default, Luna Kit will not override existing files, but this option can turn that off.",
        )
    
    @classmethod
    def run_command(cls, args: Namespace):
        from ..texatlas import TexAtlas
        from glob import glob
        import os
        from ..console import console
        from rich.progress import track
            
        files: list[str] = args.files
        
        
        search_folders: list[str] = args.search_folders
        if search_folders and len(search_folders) == 0:
            search_folders.append('.')
        
        for file in files:
            if not os.path.isfile(file):
                raise FileNotFoundError(f'file "{file}" does not exist or is a directory.')
            

            atlas = TexAtlas(
                file,
                search_folders = search_folders,
                smart_search = args.smart_search,
            )
            
            for image in track(
                atlas.images,
                'saving...',
                console = console,
            ):
                console.print(image.filename)
                if not args.output:
                    dir = image.dir
                else:
                    dir = args.output
                
                filename = os.path.join(dir, image.filename)
                os.makedirs(os.path.dirname(filename), exist_ok = True)
                
                if not args.override_existing and os.path.exists(filename):
                    continue
                image.image.save(filename)
