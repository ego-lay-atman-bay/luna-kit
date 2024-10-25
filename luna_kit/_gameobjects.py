from collections.abc import Callable, Mapping
from copy import copy, deepcopy
from itertools import zip_longest
from typing import Any, Literal, TypedDict
from dataclasses import dataclass
import functools

from lxml import etree

from .utils import strToFloat, strToInt

# class GameObjectProperty(TypedDict, total = False):
#     tag: str
#     type: "Literal['str', 'int', 'float', 'bool'] | Callable | Mapping[str, GameObjectProperty]"
#     attrib: str


type GameObjectType = Literal['str', 'int', 'float', 'bool', 'rbool'] | Callable | Mapping[str, GameObjectProperty]

def game_object_type_to_annotation(type: GameObjectType):
    result = Any
    
    if callable(type):
        result = type.__annotations__.get('return')
    elif isinstance(type, dict):
        result = {}
        for key, info in type.items():
            if isinstance(info, GameObjectProperty):
                result[key] = game_object_type_to_annotation(info.type)
        
        result = TypedDict('GameObjectProperties', result)
    else:
        match type:
            case 'bool':
                result = bool
            case 'rbool':
                result = bool
            case 'int':
                result = int
            case 'float':
                result = float
            case 'str':
                result = str
            case _:
                result = Any
    
    return result
    

class GameObject():
    CATEGORY = ''
    PROPERTIES: Mapping[str, 'GameObjectProperty'] = {}
    OBJECTS: 'Mapping[str, GameObject]' = {}
    
    @classmethod
    def from_category(cls: 'GameObject', xml: etree._Element, category: str = None):
        if category in cls.OBJECTS:
            cls = cls.OBJECTS[category]
        
        return cls(xml)
    
    @classmethod
    def register_object(cls, object: 'GameObject', category: str | None = None):
        
        if not issubclass(object, GameObject):
            e = TypeError('game object must inherit from GameObject')
            e.add_note(str(object))
            raise e
        
        if not category:
            category = object.CATEGORY
        
        cls.OBJECTS[category] = object
    
    def __init__(self, xml: etree._Element) -> None:
        for prop, value in self.PROPERTIES.items():
            if not isinstance(value, GameObjectProperty):
                continue
            
            default = deepcopy(value.default)
            
            if default is None:
                match value.type:
                    case 'bool':
                        default = False
                    case 'rbool':
                        default = True
                    case 'float':
                        default = 0.0
                    case 'int':
                        default = 0
                    case 'str':
                        default = ''
            
            self.__setattr__(prop, default)
        
        self._set_xml_data(xml)
        
        for element in xml:
            self._set_xml_data(element)
    
    def _set_xml_data(self, xml: etree._Element):
        props = {}
        for key, prop_info in self.PROPERTIES.items():
            if prop_info.tag == xml.tag:
                props[key] = prop_info
        
        if props == {}:
            return
        
        for prop, prop_info in props.items():
            value = self._get_element_value(xml, prop_info)
            self.__setattr__(prop, value)
    
    def _get_element_value(self, element: etree._Element, prop_info: 'GameObjectProperty'):
        value = None
        if prop_info.attrib:
            value = element.attrib.get(prop_info.attrib, '')
        
        if callable(prop_info.type):
            value = prop_info.type(element)
        elif isinstance(prop_info.type, dict):
            value = {}
            for key, info in prop_info.type.items():
                value[key] = self._get_element_value(element, info)
        else:
            match prop_info.type:
                case 'bool':
                    value = bool(strToInt(value or 0))
                case 'rbool':
                    value = not bool(strToInt(value or 0))
                case 'int':
                    value = strToInt(value or 0)
                case 'float':
                    value = strToFloat(value or 0.0)
                case _:
                    value = value
        
        return value

def make_type(cls):
    return cls()

@dataclass
class GameObjectProperty():
    type: GameObjectType = None
    attrib: str = None
    tag: str = None
    default: Any = None

def register_game_object[T](cls: T) -> T:
    GameObject.register_object(cls)
    
    cls.PROPERTIES = {}
    
    attrs = vars(cls).copy()
    
    for attr, value in attrs.items():
        if not isinstance(value, GameObjectProperty):
            continue
        
        cls.PROPERTIES[attr] = value
        
        setattr(cls, attr, None)
        
        cls.__annotations__[attr] = game_object_type_to_annotation(value.type)
    
    
    return cls

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
    
    

    id: str = GameObjectProperty(
        tag = 'GameObject',
        type = 'str',
        attrib = 'ID',
    )
    
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
        type = _star_rewards,
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
