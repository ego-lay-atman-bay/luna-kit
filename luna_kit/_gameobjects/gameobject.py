from collections.abc import Callable, Mapping
from copy import deepcopy, copy
from dataclasses import dataclass
from functools import partial
from itertools import zip_longest
from typing import Any, Literal, TypedDict, Type

from lxml import etree

from ..utils import strToFloat, strToInt

type GameObjectPropertyType = Literal['str', 'int', 'float', 'bool', 'rbool'] | Callable[[etree._Element], Any] | Mapping[str, GameObjectProperty]

@dataclass
class GameObjectProperty():
    type: GameObjectPropertyType = None
    attrib: str = None
    tag: str = None
    default: Any = None
    help: str = ''
    
    def get_value(self, element: etree._Element):
        value = None
        if self.attrib:
            value = element.attrib.get(self.attrib, '')
        
        if callable(self.type):
            value = self.type(element)
        elif isinstance(self.type, dict):
            value = {}
            for key, info in self.type.items():
                value[key] = info.get_value(element)
        else:
            match self.type:
                case 'bool':
                    value = bool(strToInt(value))
                case 'rbool':
                    value = not bool(strToInt(value))
                case 'int':
                    value = strToInt(value)
                case 'float':
                    value = strToFloat(value)
                case _:
                    value = value
        
        if not value:
            value = self.get_default()
        
        return value

    def get_default(self):
        default = deepcopy(self.default)

        if default is None:
            match self.type:
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
        
        return default

class GameObject():
    CATEGORY = ''
    PROPERTIES: Mapping[str, 'GameObjectProperty'] = {
        'id': GameObjectProperty(
            tag = 'GameObject',
            type = 'str',
            attrib = 'ID',
        )
    }
    OBJECTS: 'Mapping[str, GameObject]' = {}

    FROM_MANIFEST: bool = False
    
    id: str

    @classmethod
    def from_category(cls: 'GameObject', xml: etree._Element, category: str = None):
        if category in cls.OBJECTS:
            cls = cls.OBJECTS[category]

        return cls(xml)

    @classmethod
    def register_object(cls, object: 'Type[GameObject]', category: str | None = None):

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

            self.__setattr__(prop, value.get_default())

        self._set_xml_data(xml)

        for element in xml:
            self._set_xml_data(element)

    def _set_xml_data(self, xml: etree._Element):
        props: Mapping[str, GameObjectProperty] = {}
        for key, prop_info in self.PROPERTIES.items():
            if prop_info.tag == xml.tag:
                props[key] = prop_info

        if props == {}:
            return

        for prop, prop_info in props.items():
            value = prop_info.get_value(xml)
            self.__setattr__(prop, value)
    
    @classmethod
    def register_category_manifest(cls, file: str):
        tree = etree.parse(file)
        root = tree.getroot()
        
        
        for category_xml in root:
            if category_xml.tag != 'GameObjectCategory':
                continue
            
            category_name = category_xml.attrib.get('Name')
            
            if category_name in cls.OBJECTS:
                continue
            
            type_conversion: Mapping[str, GameObjectPropertyType] = {
                'string': 'str',
                'stringWithDefault': 'str',
            }
            
            PROPERTIES = {}
            
            for parameter in category_xml:
                if parameter.tag != 'Parameter':
                    continue
                
                property = GameObjectProperty(
                    tag = parameter.attrib.get('Name'),
                    type = {},
                )
                for attribute in parameter:
                    name = attribute.attrib.get('Name', '')
                    array = attribute.attrib.get('Array', None)
                    attribute_type = attribute.attrib.get('Type', 'string')
                    help = attribute.attrib.get('Tag', '')
                    default_value = attribute.attrib.get('DefaultValue', None)

                    attribute_type = type_conversion.get(attribute_type, attribute_type)

                    if array:
                        attr = GameObjectProperty(
                            type = GameObjectArray(
                                tag = name,
                                type = attribute_type,
                            ),
                            help = help,
                            default = [],
                        )
                    else:
                        attr = GameObjectProperty(
                            type = attribute_type,
                            attrib = name,
                            default = default_value,
                            help = help,
                        )
                    
                    property.type[name] = attr
                
                PROPERTIES[property.tag] = property
                    
            
            category_class = type(f'{category_name}Object', (GameObject, object), {
                'CATEGORY': category_name,
                'PROPERTIES': PROPERTIES,
                'FROM_MANIFEST': True,
                **{key: None for key in PROPERTIES.keys()},
            })
            
            cls.register_object(category_class)
    
    @classmethod
    def clear_manifest_categories(cls):
        objects = copy(cls.OBJECTS)
        
        for category, obj in objects.items():
            if obj.FROM_MANIFEST:
                del cls.OBJECTS[category]
        
        
        
        

def game_object_type_to_annotation(type: GameObjectPropertyType):
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


def register_game_object[T](cls: T | Type[GameObject]) -> T:
    GameObject.register_object(cls)

    if not hasattr(cls, 'PROPERTIES') or not isinstance(cls.PROPERTIES, dict):
        cls.PROPERTIES = {}
    else:
        cls.PROPERTIES = deepcopy(cls.PROPERTIES)

    attrs = vars(cls).copy()

    for attr, value in attrs.items():
        if not isinstance(value, GameObjectProperty):
            continue

        cls.PROPERTIES[attr] = value

        setattr(cls, attr, None)

        cls.__annotations__[attr] = game_object_type_to_annotation(value.type)

    return cls
    

def GameObjectArray(
    tag: str,
    type: GameObjectPropertyType = 'str',
    item_tag: str = 'Item',
    value_attrib: str = 'Value',
) -> Callable[[etree._Element], list[GameObjectPropertyType]]:
    def get_xml_list(xml: etree._Element) -> list[GameObjectPropertyType]:
        element = xml.find(tag)
        
        result = []
        if element is not None:
            for child in element:
                if child.tag == item_tag:
                    result.append(
                        GameObjectProperty(
                            attrib = value_attrib,
                            type = type,
                        ).get_value(child)
                    )
        
        return result
    
    return get_xml_list

def zip_game_properties(*properties: GameObjectProperty):
    def zip_properties(xml: etree._Element):
        props = [value if (isinstance(value := p.get_value(xml), (list, tuple, set))) else [value] for p in properties]

        result = []
        
        for values in zip_longest(*props, fillvalue = None):
            result.append([
                properties[index].get_default() if value == None else value for index, value in enumerate(values)
            ])
        
        return result

    return zip_properties
