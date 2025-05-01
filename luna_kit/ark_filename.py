from dataclasses import dataclass
from typing import overload
import os
import glob
from .utils import strToInt


class ARKFilename:
    priority: int = 0
    tag: str = ''
    encoding: str = ''
    format: str = ''
    calibre: str = ''

    dlc: bool = False
    dlc_tag: str = ''
    
    def __init__(self, filename: str | None = None):
        if filename is not None:
            if isinstance(filename, self.__class__):
                self.priority = filename.priority
                self.tag = filename.tag
                self.encoding = filename.encoding
                self.format = filename.format
                self.calibre = filename.calibre
                self.dlc = filename.dlc
                self.dlc_tag = filename.dlc_tag
            elif isinstance(filename, str):
                self.parse_filename(filename)
            else:
                raise TypeError(f'filename must be str or {self.__class__.__name__}')
    
    CALIBRES = [
        'common',
        'low',
        'veryhigh',
    ]
    ENCODINGS = ['astc']
    FORMATS = ['pvr']
    
    @property
    def device_calibre(self):
        calibres = {
            'common': 'all',
            'low': 'low',
            'veryhigh': 'veryhigh',
            None: 'high',
        }
        return calibres.get(self.calibre, calibres[None])
    
    def parse_filename(self, filename: str):
        # reset
        self.priority: int = 0
        self.tag: str = ''
        self.encoding: str = ''
        self.format: str = ''
        self.calibre: str = ''

        self.dlc: bool = False
        self.dlc_tag: str = ''

        filename = os.path.splitext(filename)[0]
        parts = iter(filename.split('_'))
        
        try:
            self.priority = strToInt(next(parts))
            next(parts) # and
            
            tag = next(parts)
            if tag == 'softdlc':
                self.dlc = True
                tag = next(parts)
                self.dlc_tag = next(parts)
            
            self.tag = tag
            
            for i in range(3):
                part = next(parts)
                if part in self.CALIBRES:
                    self.calibre = part
                elif part in self.FORMATS:
                    self.format = part
                elif part in self.ENCODINGS:
                    self.encoding = part
                else:
                    raise ValueError(f'Unknown part {part}')
            
        except StopIteration:
            pass # Finished
    
    def __eq__(self, value: 'str | ARKFilename'):
        value = ARKFilename(value)
        return (self.priority == value.priority and
                self.tag == value.tag and
                self.encoding == value.encoding and
                self.format == value.format and
                self.calibre == value.calibre and
                self.dlc == value.dlc and
                self.dlc_tag == value.dlc_tag)
    
    CALIBRE_PRIORITY = [
        'all',
        'low',
        'high',
        'veryhigh',
    ]
    
    TAG_PRIORITY = [
        'startup',
        'mlpextragui',
        'mlpextra',
        'mlpextra2',
        'mlpdata',
    ]
    
    def get_priority(self, value: str, priority_list: list[str]):
        if value in priority_list:
            return priority_list.index(value)
        else:
            return -1
    
    def __gt__(self, value: 'str | ARKFilename'):
        value = ARKFilename(value)
        
        dlc = [self.dlc, value.dlc]
        if dlc[0] != dlc[1]:
            return dlc[0] > dlc[1]

        priority = [self.priority, value.priority]
        if priority[0] != priority[1]:
            return priority[0] > priority[1]
        
        tag = [self.get_priority(self.tag, self.TAG_PRIORITY), self.get_priority(value.tag, self.TAG_PRIORITY)]
        if tag[0] != tag[1]:
            return tag[0] > tag[1]
        
        if self.dlc and value.dlc:
            dlc_tag = [self.dlc_tag, value.dlc_tag]
            if dlc_tag[0] != dlc_tag[1]:
                return dlc_tag[0] > dlc_tag[1]
        
        encoding = [self.encoding, value.encoding]
        if encoding[0] != encoding[1]:
            return encoding[0] > encoding[1]
        
        format = [self.format, value.format]
        if format[0] != format[1]:
            return format[0] < format[1]

        calibre = [self.get_priority(self.device_calibre, self.CALIBRE_PRIORITY), self.get_priority(value.device_calibre, self.CALIBRE_PRIORITY)]
        if calibre[0] != calibre[1]:
            return calibre[0] > calibre[1]
        
        return False
    
    def __ge__(self, value: 'str | ARKFilename'):
        return (self == value) or (self > value)
    
    def __lt__(self, value: 'str | ARKFilename'):
        value = ARKFilename(value)
        
        dlc = [self.dlc, value.dlc]
        if dlc[0] != dlc[1]:
            return dlc[0] < dlc[1]

        priority = [self.priority, value.priority]
        if priority[0] != priority[1]:
            return priority[0] < priority[1]
        
        tag = [self.get_priority(self.tag, self.TAG_PRIORITY), self.get_priority(value.tag, self.TAG_PRIORITY)]
        if tag[0] != tag[1]:
            return tag[0] < tag[1]
        
        if self.dlc and value.dlc:
            dlc_tag = [self.dlc_tag, value.dlc_tag]
            if dlc_tag[0] != dlc_tag[1]:
                return dlc_tag[0] < dlc_tag[1]
        
        encoding = [self.encoding, value.encoding]
        if encoding[0] != encoding[1]:
            return encoding[0] < encoding[1]
        
        format = [self.format, value.format]
        if format[0] != format[1]:
            return format[0] > format[1]

        calibre = [self.get_priority(self.device_calibre, self.CALIBRE_PRIORITY), self.get_priority(value.device_calibre, self.CALIBRE_PRIORITY)]
        if calibre[0] != calibre[1]:
            return calibre[0] < calibre[1]
        
        return False
    
    def __le__(self, value: 'str | ARKFilename'):
        return (self == value) or (self < value)

    def __str__(self):
        name = []
        
        name.append(f'{self.priority:0>3}')
        name.append('and')

        if self.dlc:
            name.append('softdlc')
        
        if self.tag:
            name.append(self.tag)
        
        if self.dlc_tag:
            name.append(self.dlc_tag)
        
        if self.encoding:
            name.append(self.encoding)
        
        if self.format:
            name.append(self.format)
        
        if self.calibre:
            name.append(self.calibre)
        
        return '_'.join(name)
    
    def __repr__(self):
        return f'{self.__class__.__name__}(priority={repr(self.priority)} tag={repr(self.tag)} encoding={repr(self.encoding)} format={repr(self.format)} calibre={repr(self.calibre)} dlc={repr(self.dlc)} dlc_tag={repr(self.dlc_tag)})'

def sort_ark_filenames(filenames: list[str]) -> list[str]:
    return sorted(filenames, key = lambda file: ARKFilename(file))
