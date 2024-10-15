import argparse
import os
import sys
from glob import glob

from rich.progress import track

from .console import console

console.quiet = False

def main():
    arg_parser = argparse.ArgumentParser(
        description = 'Decrypt .ark files from My Little Pony Magic Princess (the Gameloft game).',
    )
    
    subparsers = arg_parser.add_subparsers(
        title = 'commands',
        dest = 'command',
    )
    
    # ark_parser
    ark_parser = subparsers.add_parser(
        'ark',
        help = 'Extract .ark files',
    )
    
    ark_parser.add_argument(
        'files',
        nargs = '+',
        help = 'input .ark files',
    )
    
    ark_parser.add_argument(
        '-f', '--separate-folders',
        dest = 'separate_folders',
        help = 'Output each .ark file in separate folders',
        action = 'store_true',
    )
    
    ark_parser.add_argument(
        '-o', '--output',
        dest = 'output',
        help = 'output directory for .ark file(s)',
    )
    
    # atlas_parser
    atlas_parser = subparsers.add_parser(
        'atlas',
        help = 'Extract .texatlas files.',
    )
    
    atlas_parser.add_argument(
        'file',
        help = 'input .texatlas file',
    )
    
    atlas_parser.add_argument(
        '-s', '--search-folders',
        dest = 'search_folders',
        nargs = '+',
        help = 'additional folders to look for the atlas images in. This defaults to the current working directory.',
    )
    
    atlas_parser.add_argument(
        '-ds', '--disable-smart-search',
        dest = 'smart_search',
        action = 'store_false',
        help = 'Smart search searches the folders that the .texatlas file is located in to find the atlas image. Disabling this will only search the current working directory (or additional search paths).',
    )
    
    atlas_parser.add_argument(
        '-o', '--output',
        dest = 'output',
        help = 'Output folder to save images to. If omitted, the files will save to their location that they would be in the folder the .texatlas file was in.',
    )
    
    if len(sys.argv[1:]) < 1:
        arg_parser.print_help()
        sys.exit()
    
    args = arg_parser.parse_args()
    
    if args.command == 'ark':
        from .ark import ARK
        
        output = './'
        
        files = []
        for pattern in args.files:
            files += glob(pattern)
        
        if args.output:
            output = args.output
        elif len(files) == 1:
            output = os.path.splitext(os.path.basename(args.files[0]))[0]
        
        if len(files) == 1:
            ark_file = ARK(args.files[0], output = output)
        else:
            for filename in files:
                filename: str
                if args.separate_folders:
                    path = os.path.join(output, os.path.splitext(os.path.basename(filename))[0])
                else:
                    path = output
                
                ark_file = ARK(filename, output = path)

    elif args.command == 'atlas':
        from .texatlas import TexAtlas
        
        file: str = args.file
        
        if not os.path.isfile(file):
            raise FileNotFoundError(f'file "{file}" does not exist or is a directory.')
        
        search_folders: list[str] = args.search_folders
        if search_folders and len(search_folders) == 0:
            search_folders.append('.')

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
            
            image.image.save(filename)

if __name__ == "__main__":
    main()
