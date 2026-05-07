from argparse import ArgumentParser, Namespace
from .cli import CLI, CLICommand
from ._actions import GlobFiles
from ..console import console

@CLI.register_command
class AudioCommand(CLICommand):
    COMMAND = 'audio'
    HELP = 'Extract audio files found in the game.'

    @classmethod
    def build_args(cls, parser: ArgumentParser):
        parser.epilog = 'You must have ffmpeg and mpcdec installed to the PATH for this to work.\n\nYou can find mpcdec on https://musepack.net'
        
        parser.add_argument(
            'files',
            help = 'Input audio file(s)',
            action = GlobFiles,
            nargs = '+',
        )
        
        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'Output folder',
            required = True,
        )
        
        parser.add_argument(
            '-f', '--format',
            dest = 'format',
            help = 'Output format',
            default = 'wav',
        )
    
    @classmethod
    def run_command(cls, args: Namespace):
        import os
        from ..audio import Audio
        
        if len(args.files) == 0:
            console.print('[red]No files found[/]')
            return
        
        for filename in args.files:
            audio = Audio(filename)
            name = os.path.splitext(os.path.basename(filename))[0]
            
            console.print(f'converting [green]{filename}[/]')
            
            if isinstance(audio, list):
                for i, stream in enumerate(audio):
                    output = os.path.join(args.output, name, f'{name}_{i}.{args.format}')
                    output = os.path.abspath(output)
                    os.makedirs(os.path.dirname(output), exist_ok = True)
                    stream.save(output)
            else:
                output = os.path.join(args.output, f'{name}.{args.format}')
                output = os.path.abspath(output)
                os.makedirs(os.path.dirname(output), exist_ok = True)
                audio.save(output)
                
