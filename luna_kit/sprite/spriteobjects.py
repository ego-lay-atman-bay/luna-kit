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
    
    def __init__(self, modules: 'list[Module] | None' = None):
        if modules is None:
            super().__init__()
        else:
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
    
    def __init__(
        self,
        desc: SpriteStr,
        frame_id: SpriteHex,
        FMi: 'list[FrameFM]',
        RCi: 'list[FrameRC]',
    ):
        self.desc = desc
        self.frame_id = frame_id
        self.FMi = FMi
        self.RCi = RCi

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
                if isinstance(param, SpriteComment):
                    continue
                elif isinstance(param, SpriteHex):
                    frame_id = param
                    
                elif isinstance(param, SpriteElement):
                    sub_parser = ElementParser(cls._filter_sprite_element(param), initial_index = 0)
                    _frame_id = sub_parser.next_param(SpriteHex)
                    if isinstance(_frame_id, SpriteHex):
                        frame_id = _frame_id
                    else:
                        if FrameFM.check(param):
                            FMi.append(FrameFM.parse_element(param))
                        elif FrameRC.check(param):
                            FMi.append(FrameRC.parse_element(param))
                        else:
                            raise ValueError(f'Cannot parse {param}')
                        
        return cls(
            desc = desc,
            frame_id = frame_id,
            FMi = FMi,
            RCi = RCi,
        )

@register_object
class FrameFM(BaseObject):
    TAG = 'FM'
    
    def __init__(
        self,
        module_or_frame_id: SpriteHex,
        ox: int,
        oy: int,
    ):
        self.module_or_frame_id = module_or_frame_id
        self.ox = ox
        self.oy = oy
    
    @classmethod
    def parse_element(cls, element):
        parser = ElementParser(cls._filter_sprite_element(element))
        
        module_or_frame_id = parser.next_param(SpriteHex)
        ox = parser.next_param(int)
        oy = parser.next_param(int)

        try:
            flags = next(parser)
            if flags is not None:
                print(flags)
        except StopIteration:
            pass
        
        return cls(
            module_or_frame_id = module_or_frame_id,
            ox = ox,
            oy = oy,
        )

@register_object
class FrameRC(BaseObject):
    TAG = 'RC'
    
    def __init__(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
    
    @classmethod
    def parse_element(cls, element):
        parser = ElementParser(cls._filter_sprite_element(element))
        
        return cls(
            x1 = parser.next_param(int),
            y1 = parser.next_param(int),
            x2 = parser.next_param(int),
            y2 = parser.next_param(int),
        )

@register_object
class Animation(BaseObject):
    TAG = "ANIM"
    
    def __init__(
        self,
        desc: SpriteStr,
        animation_id: SpriteHex,
        frames: 'list[AnimationFrame]',
    ):
        self.desc = desc
        self.animation_id = animation_id
        self.frames = frames

    @classmethod
    def parse_element(cls, element):
        parser = ElementParser(cls._filter_sprite_element(element))

        desc = parser.next_param(SpriteStr)
        frames_block = parser.next_param(SpriteBlock)

        animation_id = None
        frames: list[AnimationFrame] = []
        
        if frames_block is not None:
            for frame in frames_block:
                if isinstance(frame, SpriteComment):
                    continue
                elif isinstance(frame, SpriteHex):
                    animation_id = frame
                    
                elif isinstance(frame, SpriteElement):
                    sub_parser = ElementParser(cls._filter_sprite_element(frame), initial_index = 0)
                    _animation_id = sub_parser.next_param(SpriteHex)
                    if isinstance(_animation_id, SpriteHex):
                        animation_id = _animation_id
                    else:
                        frames.append(AnimationFrame.parse_element(frame))
        
        return cls(
            desc = desc,
            animation_id = animation_id,
            frames = frames,
        )

@register_object
class AnimationFrame(BaseObject):
    TAG = "AF"
    
    def __init__(
        self,
        frame_id: SpriteHex,
        time: int,
        ox: int,
        oy: int,
    ):
        self.frame_id = frame_id
        self.time = time
        self.ox = ox
        self.oy = oy
    
    @classmethod
    def parse_element(cls, element):
        parser = ElementParser(cls._filter_sprite_element(element))

        frame_id = parser.next_param(SpriteHex)
        time = parser.next_param(int)
        ox = parser.next_param(int)
        oy = parser.next_param(int)
        
        flags = None
        
        try:
            flags = next(parser)
            if flags is not None:
                print(flags)
        except StopIteration:
            pass

        return cls(
            frame_id = frame_id,
            time = time,
            ox = ox,
            oy = oy,
        )
