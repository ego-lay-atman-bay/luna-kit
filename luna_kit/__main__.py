import argparse
import json
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
    
    create_ark_parser(subparsers.add_parser(
        'ark',
        help = 'Extract .ark files',
    ))
    
    # atlas_parser
    
    create_atlas_parser(subparsers.add_parser(
        'atlas',
        help = 'Extract .texatlas files.',
    ))
    
    
    # loc_parser
    create_loc_parser(subparsers.add_parser(
        'loc',
        help = 'Convert .loc localization files to json.',
    ))
    
    # spreadsheet parser
    create_sheet_parser(subparsers.add_parser(
        'sheet',
        help = 'Export spreadsheet(s) for data in the game, such as character info',
    ))
    
    if len(sys.argv[1:]) < 1:
        arg_parser.print_help()
        sys.exit()
    
    args = arg_parser.parse_args()
    
    match args.command:
        case 'ark':
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
                ark_file = ARK(args.files[0], output = output, ignore_errors = args.ignore_errors)
            else:
                for filename in files:
                    filename: str
                    if args.separate_folders:
                        path = os.path.join(output, os.path.splitext(os.path.basename(filename))[0])
                    else:
                        path = output
                    
                    ark_file = ARK(filename, output = path, ignore_errors = args.ignore_errors)

        case 'atlas':
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
        
        case 'loc':
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
        
        case 'sheet':
            handle_sheet(args)

# parsers

def create_ark_parser(ark_parser: argparse.ArgumentParser):
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
    
    ark_parser.add_argument(
        '-i', '--ignore-errors',
        dest = 'ignore_errors',
        action = 'store_true',
        help = 'ignore errors',
    )

def create_atlas_parser(atlas_parser: argparse.ArgumentParser):
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
    
def create_loc_parser(loc_parser: argparse.ArgumentParser):
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

def create_sheet_parser(sheet_parser: argparse.ArgumentParser):
    sheet_parser.add_argument(
        '-o', '--output',
        dest = 'output',
        help = 'Output filename',
        required = True,
    )
    
    sheet_parser.add_argument(
        '-f', '--format',
        dest = 'format',
        choices = ['csv', 'json'],
        default = 'json',
        help = 'Output format',
    )
    
    type = sheet_parser.add_subparsers(
        title = 'type',
        dest = 'type',
    )
    
    # characters
    characters = type.add_parser(
        'characters',
        description = 'Export a spreadsheet with all character info.',
    )
    
    characters.add_argument(
        '-g', '--game-object-data',
        dest = 'game_object_data',
        help = 'Path to gameobjectdata.xml file',
        required = True,
    )
    
    characters.add_argument(
        '-s', '--shop-data',
        dest = 'shop_data',
        help = 'Path to shopdata.xml file',
        required = True,
    )
    
    characters.add_argument(
        '-l', '--loc', '--localization',
        dest = 'loc',
        help = '.loc file to get in-game text.',
    )

def handle_sheet(args: argparse.Namespace):
    match args.type:
        case 'characters':
            from .gameobjectdata import GameObjectData
            from .loc import LocalizationFile
            from .shopdata import ShopData
            from .constants import STAR_REWARDS, SPECIAL_AI
            
            object_data = GameObjectData(args.game_object_data)
            shop_data = ShopData(args.shop_data)
            strings = {}
            
            if args.loc:
                strings = LocalizationFile(args.loc).strings
            
            def translate(string: str):
                return strings.get(string, string)
            
            pony_shop = {pony.id: pony for pony in shop_data.categories['Pony'].items}
            objects = object_data.categories['Pony']

            sheet = []

            for pony in objects:
                pony_data = {}
                
                shop = pony_shop.get(pony.id)
                
                pony_data['id'] = pony.id
                pony_data['name'] = translate(pony.name)
                pony_data['description'] = translate(pony.description)
                pony_data['icon'] = pony.icon
                pony_data['image'] = pony.image
                pony_data['shop'] = {
                    'location': shop.map_zone if shop else None,
                    'cost': shop.cost if shop else None,
                    'currency': shop.currency_type if shop else None,
                    'quest': shop.quest if shop else None,
                    'sort_price': shop.sort_price if shop else None,
                    'task_id': shop.task_token_id if shop else None,
                    'unlock_value': shop.unlock_value if shop else None,
                }
                
                pony_data['arrival_xp'] = pony.arrival_xp
                pony_data['star_rewards'] = [{
                    'reward': STAR_REWARDS.get(reward['reward'], reward['reward']),
                    'amount': reward['amount'],
                } for reward in pony.star_rewards]
                pony_data['house'] = pony.house
                # pony_data['model'] = pony.model
                pony_data['arrival_notification'] = translate(pony.arrival_notification)
                pony_data['tracking_id'] = pony.tracking_id
                pony_data['ai'] = {
                    'special_ai': SPECIAL_AI.get(pony.ai['special_ai'], SPECIAL_AI[0]),
                    'at_max_level': pony.ai['at_max_level'],
                }
                pony_data['minigames'] = pony.minigames
                pony_data['changeling'] = pony.changeling
                pony_data['has_pets'] = pony.has_pets
                pony_data['is_pony'] = pony.is_pony
                pony_data['never_crystallize'] = pony.never_crystallize
                pony_data['never_shapeshift'] = pony.never_shapeshift
                pony_data['friends'] = pony.friends
                
                sheet.append(pony_data)
            
            match args.format:
                case _: # json
                    with open(args.output, 'w') as file:
                        json.dump(sheet, file, indent = 2, ensure_ascii = False)
            

if __name__ == "__main__":
    main()


