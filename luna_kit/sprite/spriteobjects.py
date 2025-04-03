import logging
from abc import abstractmethod
from typing import Self, Type
from collections import UserList

from .parser import ElementParser
from .types import (SpriteBlock, SpriteComment, SpriteElement, SpriteHex,
                    SpriteName, SpriteStr, SpriteType)

OBJECTS: 'list[Type[BaseObject]]' = []

def register_object(object: 'BaseObject'):
    if not issubclass(object, BaseObject):
        raise TypeError('object must inherit from BaseObject')
    
    OBJECTS.append(object)
    
    return object

def get_object(element: SpriteElement):
    for object in OBJECTS:
        if object.check(element):
            return object.parse_element(element)
    
    return None


class BaseObject:
    TAG = ''
    
    @classmethod
    @abstractmethod
    def parse_element(cls, element: SpriteElement) -> Self: ...
    
    @classmethod
    def check(cls, element: SpriteElement):
        for param in element:
            if not isinstance(param, SpriteComment):
                break
        
        if isinstance(param, SpriteName):
            return param == cls.TAG
        
        return False
    
    @classmethod
    def _filter_sprite_element(self, element: SpriteElement):
        new_element = SpriteElement()

        for param in element:
            if not isinstance(param, SpriteComment):
                new_element.append(param)
        
        return new_element

@register_object
class Version(BaseObject):
    TAG = 'VERSION'
    
    def __init__(self, version: int):
        self.version = version

    @classmethod
    def parse_element(cls, element):
        filtered = cls._filter_sprite_element(element)
        parser = ElementParser(filtered)
        return cls(parser.next_param(int))

@register_object
class Image(BaseObject):
    TAG = 'IMAGE'

    SPEC = 'IMAGE [id] "file" [ALPHA "alpha_file"] [TRANSP transp_color]'

    def __init__(
        self,
        file: str,
        id: SpriteHex | None = None,
        alpha: str | None = None,
        transparent_color: SpriteHex | None = None,
    ):
        self.file = file
        self.id = id
        self.alpha = alpha
        self.transparent_color = transparent_color
    
    @classmethod
    def parse_element(cls, element):
        element = cls._filter_sprite_element(element)
        parser = ElementParser(element)

        id = parser.next_param(
            type = SpriteHex,
        )
        file = parser.next_param(
            type = SpriteStr,
        )
        alpha = parser.next_param(
            type = SpriteName,
            key = 'ALPHA',
            length = 1,
        )
        transparent_color = parser.next_param(
            type = SpriteName,
            key = 'TRANSP',
            length = 1,
        )
        
        return cls(
            id = id,
            file = file,
            alpha = alpha,
            transparent_color = transparent_color,
        )


@register_object
class Modules(UserList, BaseObject):
    TAG = 'MODULES'
    
    def __init__(self, modules: 'list[Module]'):
        super().__init__(modules)
    
    @classmethod
    def parse_element(cls, element):
        filtered = cls._filter_sprite_element(element)
        parser = ElementParser(filtered)

        modules = []

        modules_block = parser.next_param(SpriteBlock)
        if modules_block is not None:
            for module_element in modules_block:
                if isinstance(module_element, SpriteComment):
                    continue
                
                if isinstance(module_element, SpriteElement):
                    modules.append(Module.parse_element(module_element))
        
        return cls(modules)

@register_object
class Module(BaseObject):
    TAG = 'MD'
    
    def __init__(
        self,
        id: SpriteHex,
        type: SpriteName,
        params: dict[str, int],
        desc: str = '',
    ):
        self.id = id
        self.type = type
        self.params = params
        self.desc = desc
    
    @classmethod
    def parse_element(cls, element):
        parser = ElementParser(cls._filter_sprite_element(element))

        id = parser.next_param(SpriteHex)
        type = parser.next_param(SpriteName)

        TYPES = {
            "MD_IMAGE": ["image", "x", "y", "width", "height"],
            "MD_RECT": ["color", "width", "height"],
            "MD_FILL_RECT": ["color", "width", "height"],
            "MD_ARC": ["color", "width", "height", "startAngle", "arcAngle"],
            "MD_FILL_ARC": ["color", "width", "height", "startAngle", "arcAngle"],
            "MD_MARKER": ["color", "width", "height"],
            "MD_TRIANGLE": ["color", "p2X", "p2Y", "p3X", "p3Y"],
            "MD_FILL_TRIANGLE": ["color", "p2X", "p2Y", "p3X", "p3Y"],
            "MD_LINE": ["color", "width", "height"],
            "MD_FILL_RECT_GRAD": ["color01", "color02", "direction", "width", "height"],
            "MD_GRADIENT_TRIANGLE": ["x0", "y0", "color0", "x1", "y1", "color1", "x2", "y2", "color2"],
            "MD_GRADIENT_RECT": ["x0", "y0", "color0", "x1", "y1", "color1", "x2", "y2", "color2", "x3", "y3", "color3"],
        }

        params = TYPES[type]

        if type != 'MD_IMAGE':
            logging.debug(element)

        type_params = {}
        for param in params:
            type_params[param] = parser.next_param(int)
        
        desc = parser.next_param(SpriteStr)
        
        return cls(
            id = id,
            type = type,
            params = type_params,
            desc = desc,
        )

@register_object
class Frame(BaseObject):
    TAG = 'FRAME'

    @classmethod
    def parse_element(cls, element):
        parser = ElementParser(cls._filter_sprite_element(element))
        
        desc = parser.next_param(SpriteStr)
        frame_block = parser.next_param(SpriteBlock)
        frame_id = None

        RCi = []
        FMi = []

        if frame_block is not None:
            for param in frame_block:
                if isinstance(param, SpriteHex):
                    frame_id = param
                
        
        return cls()
