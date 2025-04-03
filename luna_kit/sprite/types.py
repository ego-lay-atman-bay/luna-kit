
from abc import abstractmethod
from collections import UserList, UserString
from textwrap import dedent, indent
from typing import Iterable, TypeAlias

from ..utils import split_into_chunks



class SpriteType:
    type: str
    
    @abstractmethod
    def __init__(self, value) -> None: ...
    @abstractmethod
    def sprite_repr(self) -> str: ...
    
class SpriteStr(UserString, SpriteType):
    def __init__(self, value):
        super().__init__(value)
    
    def sprite_repr(self):
        string = self.data
        string = string.replace('"', r'\"')
        
        return f'"{string}"'

    def __repr__(self):
        return self.sprite_repr()

class SpriteName(UserString, SpriteType):
    def __init__(self, value):
        super().__init__(value)
    
    def sprite_repr(self):
        return str(self.data)
    
    def __repr__(self):
        return self.__str__()

class SpriteHex(list, SpriteType):
    def __init__(self, value: str = '0x00'):
        if value is None:
            super().__init__()
        else:
            value = [''.join(chunk) for chunk in split_into_chunks(value.removeprefix('0x'))]
            
            super().__init__(value)
    
    def sprite_repr(self):
        return f'0x{self.hex()}'
    
    def hex(self):
        return ''.join(self)
    
    def __repr__(self):
        return self.sprite_repr()
    
    def __str__(self):
        return self.sprite_repr()

    def __int__(self):
        return int(self.hex(), 16)
    
    def __getitem__(self, key: int):
        return SpriteHex(super().__getitem__(key))
        


class SpriteBlock(list, SpriteType):
    def __init__(self, data: 'Iterable[SpriteType | SpriteElement | SpriteComment] | None' = None):
        if data is None:
            super().__init__()
        else:
            super().__init__(data)

    def sprite_repr(self):
        text = ''

        for i, element in enumerate(self):
            if i > 0:
                text += '\n'
            text += element.sprite_repr() if isinstance(element, SpriteType) else str(element)

        if text == '':
            return '{}'
        else:
            text = indent(text, ' ' * 4)
            return f"{{\n{text}\n}}"
    
    def __str__(self):
        return self.sprite_repr()

    def __repr__(self):
        return self.__str__()
    
    def __add__(self, value: 'SpriteBlock | list'):
        return SpriteBlock(super().__add__(value))


class SpriteElement(list, SpriteType):
    def __init__(self, data: Iterable[SpriteType | SpriteBlock] | None = None):
        if data is None:
            super().__init__()
        else:
            super().__init__(data)

    def sprite_repr(self):
        text = ''
        for i, param in enumerate(self):
            if isinstance(param, SpriteBlock):
                text += f'\n{param}\n'
            else:
                if i > 0:
                    text += ' '
                text += param.sprite_repr() if isinstance(param, SpriteType) else str(param)
            
        return text
    
    def __str__(self):
        return self.sprite_repr()

    def __repr__(self):
        return self.__str__()
    
    def __add__(self, value: 'SpriteElement | list'):
        return SpriteElement(super().__add__(value))

    def __getitem__(self, key: int | slice) -> 'SpriteElementItem':
        return super().__getitem__(key)


class SpriteComment(UserString, SpriteType):
    def __init__(self, text: str = None, multiline: bool = False):
        if text is None:
            super().__init__()
        else:
            super().__init__(text)
        
        self.multiline = multiline

    def __repr__(self):
        return self.sprite_repr()

    def sprite_repr(self):
        if self.multiline:
            return f'/*{self}*/'
        else:
            return f'//{self}'

class SpriteDocument(list, SpriteType):
    def __init__(self, data: 'Iterable[SpriteType | SpriteBlock | SpriteElement | SpriteComment] | None' = None):
        if data is None:
            super().__init__()
        else:
            super().__init__(data)

    def sprite_repr(self):
        text = ''

        for i, element in enumerate(self):
            if i > 0:
                text += '\n'
            text += element.sprite_repr() if isinstance(element, SpriteType) else str(element)

        if text == '':
            return ''
        else:
            return text
    
    def __str__(self):
        return self.sprite_repr()

    def __repr__(self):
        return self.__str__()
    
    def __add__(self, value: 'SpriteBlock | list'):
        return SpriteDocument(super().__add__(value))


SpriteElementItem: TypeAlias = SpriteType | SpriteComment | SpriteBlock | SpriteStr | SpriteName | SpriteHex | int | float
