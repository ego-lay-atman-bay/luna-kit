from typing import Type

from .parser import SpriteParser
from .types import SpriteType, SpriteComment, SpriteElement, SpriteBlock, SpriteName, SpriteHex, SpriteStr, SpriteDocument
from ..file_utils import PathOrTextFile
from .spriteobjects import get_object

class Sprite:
    def __init__(
        self,
        file: PathOrTextFile | None = None,
        *,
        parser_class: Type[SpriteParser] = SpriteParser,
    ):
        self.filename = ''
        self.images = []
        self.modules = []
        self.frames = []
        self.anims = []
        
        if file is not None:
            self.read(file, parser_class = parser_class)
        
    def read(
        self,
        file: PathOrTextFile,
        *,
        parser_class: Type[SpriteParser] = SpriteParser,
    ):
        self.filename = ''
        self.images = []
        self.modules = []
        self.frames = []
        self.anims = []
        
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
                    print(obj)
                    self.objects.append(obj)
    
    
    def _filter_sprite_element(self, element: SpriteElement):
        new_element = SpriteElement()

        for param in element:
            if not isinstance(param, SpriteComment):
                new_element.append(param)
        
        return new_element
        
