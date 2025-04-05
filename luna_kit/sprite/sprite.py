import os
from typing import Type

from ..file_utils import PathOrTextFile
from .parser import SpriteParser
from .spriteobjects import (Animation, Frame, Image, Modules, Version,
                            get_object)
from .types import (SpriteBlock, SpriteComment, SpriteDocument, SpriteElement,
                    SpriteHex, SpriteName, SpriteStr, SpriteType)


class Sprite:
    def __init__(
        self,
        file: PathOrTextFile | None = None,
        *,
        parser_class: Type[SpriteParser] = SpriteParser,
    ):
        self.filename = ''
        self.version = 1
        self.images: list[Image] = []
        self.modules: list[Modules] = []
        self.frames: list[Frame] = []
        self.animations: list[Animation] = []
        
        if file is not None:
            self.read(file, parser_class = parser_class)
        
    def read(
        self,
        file: PathOrTextFile,
        *,
        parser_class: Type[SpriteParser] = SpriteParser,
    ):
        self.filename = ''
        self.version = 1
        self.images = []
        self.modules = []
        self.frames = []
        self.animations = []
        
        sprite_doc = parser_class(file).elements
        
        for element in sprite_doc:
            if isinstance(element, SpriteComment):
                continue
            
            if isinstance(element, SpriteBlock):
                self._read_sprite_block(element)
    
    def _read_sprite_block(self, sprite_block: SpriteBlock):
        self.objects = []
        for element in sprite_block:
            if isinstance(element, SpriteComment):
                continue
            
            filtered = self._filter_sprite_element(element)

            
            if isinstance(filtered[0], SpriteName):
                obj = get_object(filtered)
                if obj is not None:
                    match obj.TAG:
                        case Image.TAG:
                            self.images.append(obj)
                        case Modules.TAG:
                            self.modules.append(obj)
                        case Frame.TAG:
                            self.frames.append(obj)
                        case Animation.TAG:
                            self.animations.append(obj)
                        case Version.TAG:
                            self.version = obj.version
                        case _:
                            print(f'unknown tag: {obj.TAG}')
                            self.objects.append(obj)
    
    
    def _filter_sprite_element(self, element: SpriteElement):
        new_element = SpriteElement()

        for param in element:
            if not isinstance(param, SpriteComment):
                new_element.append(param)
        
        return new_element
        
