import os
import warnings
from collections import UserDict
from typing import IO, Literal, Any

from lxml import etree

# from ._gameobjects import GameObject
# from ._gameobjects.pony import PonyObject
from .utils import strToBool, strToFloat, strToInt


class GameObject(UserDict):
    def __init__(self, id: str, category: str, data: dict | None = None):
        if data is None:
            super().__init__()
        else:
            super().__init__(data)
        
        self.id = id
        self.category = category
        self['id'] = self.id
        self['category'] = self.category
    
    def __repr__(self):
        return f'<{self.__class__.__name__} id={self.id} category={self.category}>'
    
    def keys(self):
        return self.data.keys()
    
    def items(self):
        return self.data.items()
    
    def values(self):
        return self.data.values()

class ShopItemCategory(UserDict):
    def __init__(self, name: str, info: dict, items: 'dict[str, ShopItem] | None' = None):
        if items is None:
            super().__init__()
        else:
            super().__init__(items)
        
        self.name = name
        self.info = info
    
    def __repr__(self):
        return f'<ShopItemCategory name={self.name}>'
    
    def keys(self):
        return self.data.keys()
    
    def items(self):
        return self.data.items()
    
    def values(self):
        return self.data.values()

class ShopItem(UserDict):
    def __init__(self, id: str, category: str, data: dict | None = None):
        if data is None:
            super().__init__()
        else:
            super().__init__(data)
        
        self.id = id
        self.category = category
    
    def __repr__(self):
        return f'<ShopItem id={self.id} category={self.category}>'
    
    def keys(self):
        return self.data.keys()
    
    def items(self):
        return self.data.items()
    
    def values(self):
        return self.data.values()


class GameObjectData(dict):
    def __init__(
        self,
        file: str | IO,
        shopdata: str | IO | None = None,
        category_manifest: str | IO | None = None,
    ) -> None:
        game_data_xml = etree.parse(file).getroot()
        if category_manifest is None:
            if isinstance(file, str):
                category_manifest = os.path.join(
                    os.path.dirname(file),
                    'gameobjectcategorydata.xml',
                )
            else:
                raise FileNotFoundError('Cannot find category manifest')
        
        
        if shopdata is None:
            if isinstance(file, str):
                shopdata = os.path.join(
                    os.path.dirname(file),
                    'shopdata.xml',
                )
            else:
                raise FileNotFoundError('Cannot find shopdata.xml')
        
        self.shopdata = {}
        
        category_xml = etree.parse(category_manifest).getroot()
        shopdata_xml = etree.parse(shopdata).getroot()
        
        self._parse_category_manifest(category_xml)
        self._parse_game_data(game_data_xml)
        self._parse_shopdata(shopdata_xml)
#         for element in game_xml:
#             if element.tag == 'Category':
#                 category = []
#                 category_name = element.get('ID', '')
#                 self.categories[category_name] = category
# 
#                 for child in element:
#                     if child.tag == 'GameObject':
#                         category.append(GameObject.from_category(child, category_name))

    CATEGORY_DATA: dict[str, dict[str, dict[Literal['optional', 'exclude', 'attributes'], bool | dict[str, dict[Literal['type', 'array_length', 'default', 'help'], str]]]]]

    def __getitem__(self, key: str) -> dict[str, GameObject]:
        return super().__getitem__(key)
    
    def get(self, key: str, default: Any = None) -> dict[str, GameObject]:
        return super().get(key, default)

    def _parse_category_manifest(self, manifest_xml: etree._Element):
        self.CATEGORY_DATA = {}
        
        for category_xml in manifest_xml:
            if category_xml.tag != 'GameObjectCategory':
                continue
            
            category_data = {}
            self.CATEGORY_DATA[category_xml.attrib.get('Name', '')] = category_data
            
            for parameter_xml in category_xml:
                if parameter_xml.tag != 'Parameter':
                    continue
                
                parameter_data = {
                    'optional': strToBool(parameter_xml.attrib.get('Optional', 0)),
                    'exclude': strToBool(parameter_xml.attrib.get('NotSave', 0)),
                    'attributes': {},
                }
                category_data[parameter_xml.attrib.get('Name', '')] = parameter_data
                
                for attribute_xml in parameter_xml:
                    if attribute_xml.tag != 'Attribute':
                        continue
                    
                    attribute_data = {
                        'type': attribute_xml.attrib.get('Type', 'string'),
                        'array_length': strToInt(attribute_xml.attrib.get('Array', 0)),
                        'default': attribute_xml.attrib.get('DefaultValue'),
                        'help': attribute_xml.attrib.get('Tag', ''),
                    }
                    parameter_data['attributes'][attribute_xml.attrib.get('Name', '')] = attribute_data
        
        return self.CATEGORY_DATA

    def _parse_game_data(self, data_xml: etree._Element):
        self.clear()
        
        for category_xml in data_xml:
            if category_xml.tag != 'Category':
                continue
            
            category_data = {}
            category_name = category_xml.attrib['ID']
            category_info = self.CATEGORY_DATA.setdefault(category_name, {})
            
            self[category_name] = category_data
            
            for game_object_xml in category_xml:
                if game_object_xml.tag != 'GameObject':
                    continue

                object_id = game_object_xml.attrib['ID']
                game_object_data = GameObject(
                    id = object_id,
                    category = category_name,
                )
                category_data[object_id] = game_object_data
                
                for parameter_name, parameter_info in category_info.items():
                    parameter_xml = game_object_xml.find(parameter_name)
                    # if parameter_xml is None:
                    #     if not parameter_info['optional'] and not parameter_info['exclude']:
                    #         warnings.warn(f'parameter {parameter_name} on {object_id} in category {category_name} is not optional')
                        
                    parameter_data = {}
                    
                    game_object_data[parameter_name] = parameter_data
                    
                    for attribute_name, attribute_info in parameter_info['attributes'].items():
                        attribute_data = None
                        if attribute_info['array_length'] > 0:
                            attribute_data = []
                            if parameter_xml is not None:
                                attribute_xml = parameter_xml.find(attribute_name)
                                if attribute_xml is not None:
                                    for item in attribute_xml:
                                        attribute_data.append(self._parse_game_value(
                                            item.attrib.get('Value', ''), 
                                            attribute_info['type'],
                                        ))
                                elif attribute_info['default'] is not None:
                                    attribute_data.extend(self._parse_game_value(
                                        attribute_info['default'],
                                        attribute_info['type'],
                                    ) for _ in range(attribute_info['array_length']))
                        else:
                            if parameter_xml is not None:
                                attribute_data = self._parse_game_value(
                                    parameter_xml.attrib.get(attribute_name, ''),
                                    attribute_info['type'],
                                )
                            else:
                                attribute_data = self._parse_game_value(
                                    attribute_info['default'],
                                    attribute_info['type'],
                                )
                        
                        parameter_data[attribute_name] = attribute_data
    
    def _parse_shopdata(self, shopdata: etree._Element):
        self.shopdata.clear()
        
        for category_xml in shopdata:
            if category_xml.tag != 'ShopItemCategory':
                continue
            
            category_name = category_xml.attrib.get('Name')
            category = ShopItemCategory(category_name, category_xml.attrib)
            self.shopdata[category_name] = category

            for item_xml in category_xml:
                if item_xml.tag != 'ShopItem':
                    continue
                
                item_id = item_xml.attrib.get('ID')
                item = ShopItem(item_id, category_name, item_xml.attrib)
                category[item_id] = item
                        
    def _parse_game_value(self, value: str, type: Literal['string', 'stringWithDefault', 'int', 'float', 'bool']):
        if value is None:
            return None
        match type:
            case 'bool':
                return strToBool(value)
            case 'int':
                return strToInt(value)
            case 'float':
                return strToFloat(value)
            case 'string' | 'stringWithDefault':
                return str(value)

    def get_object(self, id: str) -> GameObject | None:
        for objects in self.values():
            if id in objects:
                return objects[id]
    def get_object_shopdata(self, id: str) -> GameObject | None:
        for objects in self.shopdata.values():
            if id in objects:
                return objects[id]
