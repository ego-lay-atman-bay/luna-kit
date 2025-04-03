import os
from typing import Literal, TextIO

from ..file_utils import PathOrTextFile, is_eof, open_text_file, peek
from .types import (SpriteDocument, SpriteBlock, SpriteComment, SpriteElement, SpriteHex,
                    SpriteName, SpriteStr, SpriteType)


class SpriteParser:
    def __init__(self, file: PathOrTextFile):
        self.filename = ''
        self.elements = SpriteDocument()
        self.read(file)
    
    def read(self, file: PathOrTextFile):
        self.filename = ''
        self.elements = SpriteDocument()
        
        if os.path.isfile(file):
            self.filename = os.path.abspath(file)
        
        with open_text_file(file) as open_file:
            self.elements = self.parse(open_file)
    
    def parse(self, file: TextIO):
        return self._parse_block(file)

    def _parse_block(self, file: TextIO, level: int = 0):
        if level == 0:
            elements = SpriteDocument()
        else:
            elements = SpriteBlock()

        
        while not is_eof(file):
            comment = self._check_comment(file)
            if comment:
                elements.append(comment)
                if not comment.multiline:
                    continue
            
            char = file.read(1)
            if char == '\\':
                file.read(1)
            elif char == '{':
                block = self._parse_block(file, level + 1)
                if len(elements) and isinstance(elements[-1], SpriteElement):
                    elements[-1].append(block)
                else:
                    elements.append(block)
            elif char == '}':
                break
            elif char == ' ' or char == '\t':
                continue
            else:
                file.seek(file.tell()-1)
                element = self._parse_element(file, level)
                if len(element):
                    elements.append(element)
        
        return elements
    
    def _parse_element(self, file: TextIO, level = 0):
        element = SpriteElement()
        part = ''
        in_quote = False
        last_quote = ''
        
        while not is_eof(file):
            comment = self._check_comment(file)
            if comment:
                element.append(comment)
                break
            
            char = file.read(1)
            if in_quote:
                if char == last_quote:
                    in_quote = False
                    element.append(SpriteStr(part))
                    part = ''
                else:
                    part += char
            elif char in ['"', "'"]:
                in_quote = True
                last_quote = char
            elif char == ' ' or char == '\t':
                if part:
                    element.append(self._convert_type(part))
                    part = ''
            elif char == '{':
                if part:
                    element.append(self._convert_type(part))
                    part = ''
                element.append(self._parse_block(file, level + 1))
            elif char == '}':
                file.seek(file.tell() - 1)
                break
            elif char == '\n':
                break
            else:
                part += char
        
        if part:
            element.append(self._convert_type(part))
        
        return element
    
    def _check_comment(self, file: TextIO):
        comment = ''
        multiline = False
        if peek(file, 2) == '//':
            file.read(2)
            comment = self._read_line_comment(file)
        elif peek(file, 2) == '/*':
            file.read(2)
            comment = self._read_multiline_comment(file)
            multiline = True
        return SpriteComment(comment, multiline)
    
    def _read_line_comment(self, file: TextIO):
        comment = file.readline()
        return comment.splitlines()[0]
    
    def _read_multiline_comment(self, file: TextIO):
        comment = ''
        while not is_eof(file):
            char = file.read(1)
            if char == '\\':
                comment += char
                comment += file.read(1)
            elif char == '*' and peek(file, 1) == '/':
                file.read(1)
                break
            else:
                comment += char
        
        return comment

    def _convert_type(self, value: str):
        if value.startswith('0x'):
            return SpriteHex(value)
        
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return SpriteName(value)

class ElementParser:
    def __init__(
        self,
        element: SpriteElement,
        initial_index: int = 1,
    ):
        self.element: SpriteElement = element
        self.index = initial_index
    
    def next_param(
        self,
        type: str | SpriteType | SpriteStr | SpriteHex,
        key: SpriteName | str | None = None,
        length: int = 1,
    ):
        item = self.element[self.index]
        if isinstance(item, type):
            if key is not None:
                if item == key:
                    self.index += 1
                    items = self.element[self.index:self.index + length]
                    self.index +=  length
                    if length == 1:
                        items = items[0]
                    return items
            else:
                if length > 1:
                    item = self.element[self.index:self.index + length]
                self.index += length
                return item

    def __iter__(self):
        self.index = 0
        return self
    
    def __next__(self):
        self.index += 1
        if self.index >= len(self.element):
            self.index -= 1
            raise StopIteration
        return self.element[self.index]
    
    def __len__(self):
        return len(self.element)
    
    def __getitem__(self, key: int):
        return self.element[key]
