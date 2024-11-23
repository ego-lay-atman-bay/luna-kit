from itertools import zip_longest
from typing import Literal

from lxml import etree

from ..utils import strToInt
from .gameobject import (GameObject, GameObjectArray, GameObjectProperty,
                         register_game_object, zip_game_properties)


@register_game_object
class PonyObject(GameObject):
    CATEGORY = 'Pony'
    
    @staticmethod
    def _star_rewards(xml: etree._Element) -> list[dict[Literal['reward', 'amount'], str | int]]:
        star_rewards = []
        
        ids = xml.find('ID') if xml.find('ID') is not None else etree.Element('ID')
        amounts = xml.find('Amount') if xml.find('Amount') is not None else etree.Element('Amount')

        for id, amount in zip_longest(
            ids, amounts,
            fillvalue = etree.Element('Item', value = ''),
        ):
            
            reward = {
                'reward': id.get('Value'),
                'amount': strToInt(amount.get('Value')),
            }
            
            star_rewards.append(reward)
        
        return star_rewards
    
    name: str = GameObjectProperty(
        tag = 'Name',
        type = 'str',
        attrib = 'Unlocal',
    )
    description: str = GameObjectProperty(
        tag = 'Description',
        type = 'str',
        attrib = 'Unlocal',
    )
    minigames: dict[Literal[
        'EXP_Rank',
        'can_play_minecart',
        'no_wings',
        'skip_cost',
        'locked_games',
        'time_between_play_actions',
    ], int | bool | str] = GameObjectProperty(
        tag = 'Minigames',
        type = {
            'EXP_Rank': GameObjectProperty(
                type = 'int',
                attrib = 'EXP_Rank'
            ),
            'can_play_minecart': GameObjectProperty(
                type = 'bool',
                attrib = 'CanPlayMineCart',
            ),
            'no_wings': GameObjectProperty(
                type = 'bool',
                attrib = 'NoWings',
            ),
            'skip_cost': GameObjectProperty(
                type = 'int',
                attrib = 'PlayActionSkipAgainCost',
            ),
            'locked_games': GameObjectProperty(
                type = lambda xml: [game for game in xml.get('LockedGames', '').split(',') if game],
                attrib = 'LockedGames',
            ),
            'time_between_play_actions': GameObjectProperty(
                type = 'int',
                attrib = 'TimeBetweenPlayActions',
            ),
        },
    )
    icon: str = GameObjectProperty(
        tag = 'Icon',
        type = lambda xml: xml.get('Url', '') + '.png',
    )
    house: dict[Literal['type', 'zone'], str | int] = GameObjectProperty(
        tag = 'House',
        type = {
            'type': GameObjectProperty(
                attrib = 'Type',
                type = 'str',
            ),
            'zone': GameObjectProperty(
                attrib = 'HomeMapZone',
                type = 'int',
            ),
        },
    )
    
    image: dict[Literal[
        'image',
        'offset_x',
        'offset_y',
        'scale',
    ], str | float | bool] = GameObjectProperty(
        tag = 'Shop',
        type = {
            'image': GameObjectProperty(
                attrib = 'Icon',
                type = 'str',
            ),
            'offset_x': GameObjectProperty(
                attrib = 'OffsetX',
                type = 'int',
            ),
            'offset_y': GameObjectProperty(
                attrib = 'OffsetY',
                type = 'int',
            ),
            'scale': GameObjectProperty(
                attrib = 'Scale',
                type = 'float',
            ),
        },
    )
    
    can_be_assigned_to_shop: bool = GameObjectProperty(
        tag = 'Shop',
        type = 'bool',
        attrib = 'CanBeAssign',
    )
    
    ai: dict[Literal['special_ai', 'at_max_level'], int | str] = GameObjectProperty(
        tag = 'AI',
        type = {
            'special_ai': GameObjectProperty(
                attrib = 'Special_AI',
                type = 'int',
            ),
            'at_max_level': GameObjectProperty(
                attrib = 'Max_Level',
                type = 'bool',
            ),
        }
    )
    
    tracking_id: dict[Literal['id', 'arrival_message'], int | str] = GameObjectProperty(
        tag = 'Tracking',
        attrib = 'TrackingID',
        type = 'int',
    )
    
    arrival_notification = GameObjectProperty(
        attrib = 'ArrivalPush',
        type = 'str',
        tag = 'Tracking',
    )
    
    arrival_xp: int = GameObjectProperty(
        tag = 'OnArrive',
        type = 'int',
        attrib = 'EarnXP',
    )
    
    star_rewards: list[dict[Literal['reward', 'amount'], str | int]] = GameObjectProperty(
        tag = 'StarRewards',
        # type = _star_rewards,
        type = zip_game_properties(
            GameObjectProperty(
                GameObjectArray(
                    'ID',
                    'str',
                )
            ),
            GameObjectProperty(
                GameObjectArray(
                    'Amount',
                    'int',
                )
            ),
        ),
        default = [],
    )


    model: dict = GameObjectProperty(
        tag = 'Model',
        type = {
            'scale': GameObjectProperty(
                type = 'float',
                attrib = 'Scale',
            ),
            'low_LOD': GameObjectProperty(
                type = 'str',
                attrib = 'LowLOD',
            ),
            'medium_LOD': GameObjectProperty(
                type = 'str',
                attrib = 'MediumLOD',
            ),
            'high_LOD': GameObjectProperty(
                type = 'str',
                attrib = 'HighLOD',
            ),
            'root_bone': GameObjectProperty(
                type = 'str',
                attrib = 'RootBone',
            ),
            'shadow_bone': GameObjectProperty(
                type = 'str',
                attrib = 'ShadowBone',
            ),
        }
    )
    
    changeling: str = GameObjectProperty(
        tag = 'IsChangelingWithSet',
        type = 'str',
        attrib = 'AltPony',
    )
    
    @staticmethod
    def _friends(xml: etree._Element):
        friends = []
        for child in xml:
            if child.tag == 'Friend':
                for friend in child:
                    id = friend.get('Value')
                    if id:
                        friends.append(id)
        
        return friends

    friends: list[str] = GameObjectProperty(
        tag = 'Friends',
        type = _friends,
        default = [],
    )
    
    never_shapeshift: bool = GameObjectProperty(
        tag = 'Misc',
        type = 'bool',
        attrib = 'NeverShapeshift',
    )
    
    never_crystallize: bool = GameObjectProperty(
        tag = 'Misc',
        type = 'bool',
        attrib = 'NeverCrystallize',
    )
    
    is_pony: bool = GameObjectProperty(
        tag = 'Misc',
        type = 'rbool',
        attrib = 'IsNotPony',
    )
    
    has_pets: bool = GameObjectProperty(
        tag = 'PetsAvailability',
        type = 'rbool',
        attrib = 'BanPets',
    )

