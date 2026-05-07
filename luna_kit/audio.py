import json
import os
import subprocess
import tempfile
from subprocess import PIPE
from typing import Type

try:
    import filetype
    from vxn import VXN
    from vxn.formats import MPC
except ImportError as e:
    e.add_note('audio dependencies not found')
    raise e

from .console import console
from .file_utils import PathOrBinaryFile, open_binary

AUDIO_TYPES: 'list[Type[GenericAudio]]' = []

def Audio(file: PathOrBinaryFile) -> 'GenericAudio | list[GenericAudio]':
    with open_binary(file) as file_in:
        data = file_in.read()
    
    guessed_type = filetype.guess(data)
    
    if guessed_type is None:
        return GenericAudio(data)
    
    if guessed_type.mime == VXN.MIME:
        pack = VXN(data)
        return [Audio(a.create_file()) for a in pack.streams]
    
    for AudioType in AUDIO_TYPES:
        if AudioType.check(guessed_type):
            return AudioType(data)
    
    return GenericAudio(data)



class GenericAudio():
    def __init__(self, data: bytes) -> None:
        self.data = bytes(data)
        self.filetype = filetype.guess(data)
    
    @classmethod
    def from_file(cls, file: PathOrBinaryFile):
        with open_binary(file) as open_file:
            return cls(open_file.read())
    
    def save(self, filename: str, format: str | None = None):
        with tempfile.NamedTemporaryFile(
            'wb',
            prefix = 'luna_kit_',
            delete = False,
        ) as in_file:
            in_file.write(self.data)
        
        result = subprocess.run(
            self._output_command(f'{in_file.name}', f'{filename}', format),
            shell = True,
            capture_output = console.quiet,
        )
        
        os.remove(in_file.name)
        
        try:
            result.check_returncode()
        except subprocess.CalledProcessError as e:
            e.add_note(str(result.stdout))
            raise e
    
    def _output_command(
        self,
        in_filename: str,
        out_name: str,
        format: str | None,
    ) -> list[str]:
        command = ['ffmpeg', '-hide_banner', '-y']
        if console.quiet:
            command.extend(['-loglevel', 'quiet'])
        command.extend(['-i', in_filename])
        if format is not None:
            command.extend(['-acodec', format])
        command.extend([out_name])

        return command
    
    @classmethod
    def check(cls, type: filetype.Type):
        return True

class MPCAudio(GenericAudio):
    def _output_command(self, in_filename: str, out_name: str, format: str | None) -> list[str]:
        command = ['mpcdec', in_filename, '-', '|'] + super()._output_command('-', out_name, format)
        
        return command
    
    @classmethod
    def check(cls, type: filetype.Type):
        return type.mime == MPC.MIME

AUDIO_TYPES.append(MPCAudio)
