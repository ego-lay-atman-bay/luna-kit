import functools
from collections.abc import Callable, Mapping
from copy import copy
from itertools import zip_longest
from typing import Annotated, Any, Literal, Type, TypedDict

from lxml import etree

from .utils import strToFloat, strToInt

# class GameObjectProperty(TypedDict, total = False):
#     tag: str
#     type: "Literal['str', 'int', 'float', 'bool'] | Callable | Mapping[str, GameObjectProperty]"
#     attrib: str


type GameObjectType = Literal['str', 'int', 'float', 'bool'] | Callable | Mapping[str, GameObjectProperty]

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

    __annotations__: Mapping[str, 'Any | _GameObjectPropertyType']
    
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
        for element in xml:
            self._set_xml_data(element)
    
    def _set_xml_data(self, xml: etree._Element):
        prop = None
        for key, prop_info in self.PROPERTIES.items():
            if prop_info.tag == xml.tag:
                prop = key
                break
        
        if prop == None:
            return
        
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
                case 'int':
                    value = strToInt(value or 0)
                case 'float':
                    value = strToFloat(value or 0.0)
                case _:
                    value = value
        
        return value

def make_type(cls):
    return cls()

class GameObjectProperty():
    def __init__(
        self,
        type: GameObjectType,
        attrib: str = None,
        tag: str = None,
    ) -> None:
        self.type = type
        self.attrib = attrib
        self.tag = tag

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
    minigame: dict[Literal[
        'EXP_Rank',
        'CanPlayMineCart',
        'NoWings',
        'PlayActionSkipAgainCost',
        'LockedGames',
        'TimeBetweenPlayActions',
    ], int | bool | str] = GameObjectProperty(
        tag = 'Minigames',
        type = {
            'EXP_Rank': GameObjectProperty(
                type = 'int',
                attrib = 'EXP_Rank'
            ),
            'CanPlayMineCart': GameObjectProperty(
                type = 'bool',
                attrib = 'CanPlayMineCart',
            ),
            'NoWings': GameObjectProperty(
                type = 'bool',
                attrib = 'NoWings',
            ),
            'PlayActionSkipAgainCost': GameObjectProperty(
                type = 'int',
                attrib = 'PlayActionSkipAgainCost',
            ),
            'LockedGames': GameObjectProperty(
                type = 'str',
                attrib = 'LockedGames',
            ),
            'TimeBetweenPlayActions': GameObjectProperty(
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
    
    model: dict[Literal['EffectColour_B', 'Collision_Y', 'Base_Growing', 'ShadowBone', 'EffectColour_R', 'BaseFG', 'ShadowScale', 'PivotY', 'Collision_W', 'BaseBG', 'FixedZOffset', 'AutoScale', 'ScrollSpeed', 'ZOffset', 'VineID', 'EffectColour_G', 'Alpha', 'Base_Ready', 'PivotX', 'Scale', 'Scrolling', 'DefaultIsLeft', 'Rotation', 'MediumLOD', 'GridSize', 'Model', 'Foreground', 'RootBone', 'Base', 'Collision_X', 'LowLOD', 'HighLOD', 'Camera', 'Collision_Z'], str] = GameObjectProperty(
        tag = 'Model',
        type = {
            'EffectColour_B': GameObjectProperty(
                attrib = 'EffectColour_B',
                type = 'str',
            ),
            'Collision_Y': GameObjectProperty(
                attrib = 'Collision_Y',
                type = 'str',
            ),
            'Base_Growing': GameObjectProperty(
                attrib = 'Base_Growing',
                type = 'str',
            ),
            'ShadowBone': GameObjectProperty(
                attrib = 'ShadowBone',
                type = 'str',
            ),
            'EffectColour_R': GameObjectProperty(
                attrib = 'EffectColour_R',
                type = 'str',
            ),
            'BaseFG': GameObjectProperty(
                attrib = 'BaseFG',
                type = 'str',
            ),
            'ShadowScale': GameObjectProperty(
                attrib = 'ShadowScale',
                type = 'str',
            ),
            'PivotY': GameObjectProperty(
                attrib = 'PivotY',
                type = 'str',
            ),
            'Collision_W': GameObjectProperty(
                attrib = 'Collision_W',
                type = 'str',
            ),
            'BaseBG': GameObjectProperty(
                attrib = 'BaseBG',
                type = 'str',
            ),
            'FixedZOffset': GameObjectProperty(
                attrib = 'FixedZOffset',
                type = 'str',
            ),
            'AutoScale': GameObjectProperty(
                attrib = 'AutoScale',
                type = 'str',
            ),
            'ScrollSpeed': GameObjectProperty(
                attrib = 'ScrollSpeed',
                type = 'str',
            ),
            'ZOffset': GameObjectProperty(
                attrib = 'ZOffset',
                type = 'str',
            ),
            'VineID': GameObjectProperty(
                attrib = 'VineID',
                type = 'str',
            ),
            'EffectColour_G': GameObjectProperty(
                attrib = 'EffectColour_G',
                type = 'str',
            ),
            'Alpha': GameObjectProperty(
                attrib = 'Alpha',
                type = 'str',
            ),
            'Base_Ready': GameObjectProperty(
                attrib = 'Base_Ready',
                type = 'str',
            ),
            'PivotX': GameObjectProperty(
                attrib = 'PivotX',
                type = 'str',
            ),
            'Scale': GameObjectProperty(
                attrib = 'Scale',
                type = 'str',
            ),
            'Scrolling': GameObjectProperty(
                attrib = 'Scrolling',
                type = 'str',
            ),
            'DefaultIsLeft': GameObjectProperty(
                attrib = 'DefaultIsLeft',
                type = 'str',
            ),
            'Rotation': GameObjectProperty(
                attrib = 'Rotation',
                type = 'str',
            ),
            'MediumLOD': GameObjectProperty(
                attrib = 'MediumLOD',
                type = 'str',
            ),
            'GridSize': GameObjectProperty(
                attrib = 'GridSize',
                type = 'str',
            ),
            'Model': GameObjectProperty(
                attrib = 'Model',
                type = 'str',
            ),
            'Foreground': GameObjectProperty(
                attrib = 'Foreground',
                type = 'str',
            ),
            'RootBone': GameObjectProperty(
                attrib = 'RootBone',
                type = 'str',
            ),
            'Base': GameObjectProperty(
                attrib = 'Base',
                type = 'str',
            ),
            'Collision_X': GameObjectProperty(
                attrib = 'Collision_X',
                type = 'str',
            ),
            'LowLOD': GameObjectProperty(
                attrib = 'LowLOD',
                type = 'str',
            ),
            'HighLOD': GameObjectProperty(
                attrib = 'HighLOD',
                type = 'str',
            ),
            'Camera': GameObjectProperty(
                attrib = 'Camera',
                type = 'str',
            ),
            'Collision_Z': GameObjectProperty(
                attrib = 'Collision_Z',
                type = 'str',
            ),
        }
    )
    

    shop: dict[Literal[
        'Icon',
        'OffsetX',
        'OffsetY',
        'Scale',
        'CanBeAssign',
    ], str | float | bool] = GameObjectProperty(
            tag = 'Shop',
            type = {
                'Icon': GameObjectProperty(
                    attrib = 'Icon',
                    type = 'str',
                ),
                'OffsetX': GameObjectProperty(
                    attrib = 'OffsetX',
                    type = 'float',
                ),
                'OffsetY': GameObjectProperty(
                    attrib = 'OffsetY',
                    type = 'float',
                ),
                'Scale': GameObjectProperty(
                    attrib = 'Scale',
                    type = 'float',
                ),
                'CanBeAssign': GameObjectProperty(
                    attrib = 'CanBeAssign',
                    type = 'bool',
                ),
            },
        )
    
    ai: dict[Literal['special_ai', 'max_level'], int | str] = GameObjectProperty(
        tag = 'AI',
        type = {
            'special_ai': GameObjectProperty(
                attrib = 'Special_AI',
                type = 'int',
            ),
            'max_level': GameObjectProperty(
                attrib = 'Max_Level',
                type = 'str',
            ),
        }
    )
    
    tracking: dict[Literal['id', 'arrival_message'], int | str] = GameObjectProperty(
        tag = 'Tracking',
        type = {
            'id': GameObjectProperty(
                attrib = 'TrackingID',
                type = 'int',
            ),
            'arrival_message': GameObjectProperty(
                attrib = 'ArrivalPush',
                type = 'str',
            )
        }
    )
    
    arrival_xp: int = GameObjectProperty(
        tag = 'OnArrive',
        type = 'int',
        attrib = 'EarnXP',
    )
    
    star_rewards: list[dict[Literal['reward', 'amount'], str | int]] = GameObjectProperty(
        tag = 'StarRewards',
        type = _star_rewards,
    )
