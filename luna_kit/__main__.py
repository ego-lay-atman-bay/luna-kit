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
        'files',
        nargs = '+',
        help = 'input .texatlas file(s)',
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
    
    atlas_parser.add_argument(
        '-e', '--override-existing',
        dest = 'override_existing',
        action = 'store_true',
        help = "By default, Luna Kit will not override existing files, but this option can turn that off.",
    )
    
    
    # loc_parser
    loc_parser = subparsers.add_parser(
        'loc',
        help = 'Convert .loc localization files to json.',
    )
    
    loc_parser.add_argument(
        'file',
        help = 'input .loc file',
    )
    
    loc_parser.add_argument(
        '-o', '--output',
        dest = 'output',
        help = 'output filename, such as "english.json"',
    )
    
    loc_parser.add_argument(
        '-y',
        dest = 'override',
        action = 'store_true',
        help = 'Override output file if it already exists without prompt.',
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
            files.extend(glob(pattern))
        
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
        
        files: list[str] = []
        
        for pattern in args.files:
            files.extend(glob(pattern))
        
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
    
    elif args.command == 'loc':
        from .loc import LocalizationFile
        
        if not os.path.isfile(args.file):
            raise FileNotFoundError(f'file "{args.file}" does not exist or is a directory.')
        
        output = os.path.splitext(os.path.basename(args.file))[0] + '.json'
        if args.output:
            output = output
        
        if not args.override and os.path.exists(output):
            if input(f'"{output}" already exists, do you want to override it? (Y/n): ').lower() in ['n', 'no', 'false', '0']:
                exit()
        
        loc_file = LocalizationFile(args.file)
        loc_file.export(output, indent = 2)
        
        console.print(f'saved to {output}')
            

if __name__ == "__main__":
    main()
