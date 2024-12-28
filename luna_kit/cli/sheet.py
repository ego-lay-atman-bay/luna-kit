from argparse import ArgumentParser, Namespace
from .cli import CLI, CLICommand
from collections import UserDict


@CLI.register_command
class SheetCommand(CLICommand):
    COMMAND = 'sheet'
    HELP = 'Export spreadsheet(s) for data in the game, such as character info'

    @classmethod
    def build_args(cls, parser: ArgumentParser):
        parser.add_argument(
            '-g', '--game-object-data',
            dest = 'game_object_data',
            help = 'Path to gameobjectdata.xml file',
            required = True,
        )
        
        parser.add_argument(
            '--category',
            help = 'Game object category. You can find all the categories in `gameobjectcategorydata.xml`',
        )
        
        parser.add_argument(
            '-i', '--info',
            dest = 'info',
            nargs = '+',
            help = 'The info to get. Example Name.Unlocal. If `shop:` is before the key, it will get the data from `shopdata.xml` instead of `gameobjectdata.xml`.'
        )
        
        parser.add_argument(
            '-c', '--columns',
            dest = 'columns',
            nargs = '+',
            help = 'The names of each column mapping for data.'
        )
        
        parser.add_argument(
            '-d', '--delimiter',
            dest = 'delimiter',
            default = ', ',
            help = 'Delimiter for lists.',
        )
        
        parser.add_argument(
            '-s', '--shop-data',
            dest = 'shop_data',
            help = 'Path to `shopdata.xml` file',
            default = None,
        )
        
        parser.add_argument(
            '-l', '--loc', '--localization',
            dest = 'loc',
            help = '.loc file to get in-game text.',
        )
        
        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'Output filename. Will print to stdout if not specified.',
        )
        
        parser.add_argument(
            '-f', '--format',
            dest = 'format',
            choices = ['csv', 'json'],
            default = 'json',
            help = 'Output format',
        )
    
    @classmethod
    def run_command(cls, args: Namespace):
        from ..gameobjectdata import GameObjectData
        from ..loc import LOC
        from ..shopdata import ShopData
        from ..constants import STAR_REWARDS, SPECIAL_AI
        import json
        import os
        from itertools import zip_longest
        
        object_data = GameObjectData(
            args.game_object_data,
            shopdata = args.shop_data,
        )
        strings = {}
        
        if args.loc:
            strings = LOC(args.loc).strings
        
        def translate(string: str):
            return strings.get(string, string)
        
        def parse_key(info: str):
            split = info.split(':')
            key = split[-1].split('.')
            extras = []
            if len(split) > 1:
                extras = split[:-1]
            
            return key, extras
        
        def get_items(items: list[str], value: dict | list):
            if len(items) == 0:
                return value
            if isinstance(value, (dict, UserDict)):
                return get_items(items[1:], value.get(items[0]))
            return get_items(items[1:], value[items[0]])
        
        def get_result(name, value):
            result = {}
            
            if isinstance(value, (dict, UserDict)):
                for key, v in value.items():
                    new_name = f'{name}.{key}'
                    result.update(get_result(new_name, v))
                
                return result
            elif isinstance(value, list):
                value = args.delimiter.join([str(i) for i in value])
            elif isinstance(value, str):
                value = translate(value)
            
            result[name] = value
            
            return result
        
        objects = object_data[args.category]
        sheet = []
        

        for object_id, object in objects.items():
            object_info = {}
            
            info = None
            
            if args.info is not None:
                info: list[str] = args.info
                columns: list[str] = args.columns or []
                
                columns = columns[:len(info)]

                for key, column in zip_longest(info, columns, fillvalue = None):
                    keys, extras = parse_key(key)

                    shopdata = None


                    if 'shop' in extras:
                        shopdata = object_data.get_object_shopdata(object_id)
                        if shopdata is None:
                            result = None
                        else:
                            result = get_items(keys, shopdata)
                    else:
                        result = get_items(keys, object)
                    
                    if column is None:
                        column = '.'.join(keys)
                    
                    object_info.update(get_result(column, result))
            else:
                for column, value in object.items():
                    object_info.update(get_result(column, value))
            
            sheet.append(object_info)
                        
            
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok = True)
        
        match args.format:
            case 'csv':
                import csv
                with open(args.output, 'w', newline = '', encoding = 'utf-8') as file:
                    writer = csv.DictWriter(file, sheet[0].keys())
                    writer.writeheader()
                    writer.writerows(sheet)
            case _: # json
                with open(args.output, 'w', encoding = 'utf-8') as file:
                    json.dump(sheet, file, indent = 2, ensure_ascii = False)
