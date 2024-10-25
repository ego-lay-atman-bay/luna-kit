from argparse import ArgumentParser, Namespace
from .cli import CLI, CLICommand

@CLI.register_command
class SheetCommand(CLICommand):
    COMMAND = 'sheet'
    HELP = 'Export spreadsheet(s) for data in the game, such as character info'

    @classmethod
    def build_args(cls, parser: ArgumentParser):
        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'Output filename',
            required = True,
        )
        
        parser.add_argument(
            '-f', '--format',
            dest = 'format',
            choices = ['csv', 'json'],
            default = 'json',
            help = 'Output format',
        )
        
        type = parser.add_subparsers(
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
    
    @classmethod
    def run_command(cls, args: Namespace):
        match args.type:
            case 'characters':
                from ..gameobjectdata import GameObjectData
                from ..loc import LocalizationFile
                from ..shopdata import ShopData
                from ..constants import STAR_REWARDS, SPECIAL_AI
                import json
                
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
