from itertools import zip_longest
from typing import Literal

from lxml import etree

from ..utils import strToInt
from .gameobject import GameObject, GameObjectProperty, register_game_object, GameObjectArray

@register_game_object
class HouseObject(GameObject):
    CATEGORY = 'Pony_House'
    
    name: str = GameObjectProperty(
        tag = 'Name',
        attrib = 'Unlocal',
        type = 'str',
    )
    
    icon: str = GameObjectProperty(
        tag = 'Icon',
        attrib = 'BookIcon',
        type = 'str',
    )
    
    sprite = GameObjectProperty(
        tag = 'Sprite',
        type = {
            'Ground_Model': GameObjectProperty(
                attrib = 'Ground_Model',
                type = 'str',
            ),
            'Ground_Scale': GameObjectProperty(
                attrib = 'Ground_Scale',
                type = 'float',
            ),
        },
    )
    
    shop = GameObjectProperty(
        tag = 'Shop',
        type = {
            'icon': GameObjectProperty(
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
            'purchase_limit': GameObjectProperty(
                attrib = 'PurchaseLimit',
                type = 'int',
            ),
        }
    )
    
    model = GameObjectProperty(
        tag = 'Model',
        type = {
            'base': GameObjectProperty(
                attrib = 'Base',
                type = 'str',
            ),
            'alpha': GameObjectProperty(
                attrib = 'Alpha',
                type = 'str',
            ),
            'scale': GameObjectProperty(
                attrib = 'Scale',
                type = 'float',
            )
        }
    )
    
    animal_house_model = GameObjectProperty(
        tag = 'AnimalHouseModel',
        attrib = 'AltBase',
        type = 'str',
    )
    
    model_override = GameObjectProperty(
        tag = 'ModelOverride',
        type = {
            'data': GameObjectProperty(
                type = GameObjectArray(
                    'Data',
                    'str',
                ),
            ),
            'count': GameObjectProperty(
                type = GameObjectArray(
                    'Count',
                    'int',
                ),
            ),
        }
    )
    
    vines_season_override = GameObjectProperty(
        tag = 'VinesSeasonOverride',
        type = {
            'RKM_Append': GameObjectProperty(
                attrib = 'RKM_Append',
                type = 'str',
            ),
            'Ground_RKM_Append': GameObjectProperty(
                attrib = 'Ground_RKM_Append',
                type = 'str',
            ),
            'Animation_RKM_Append': GameObjectProperty(
                attrib = 'Animation_RKM_Append',
                type = 'str',
            ),
        }
    )
    
    particles = GameObjectProperty(
        tag = 'Particles',
        type = ''
    )
