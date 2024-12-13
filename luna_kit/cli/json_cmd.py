import charset_normalizer
from .cli import CLI, CLICommand
from ._actions import GlobFiles
from ..console import console

@CLI.register_command
class JSONCommand(CLICommand):
    COMMAND = 'json'
    HELP = 'Format json files'
    
    @classmethod
    def build_args(cls, parser):
        parser.add_argument(
            'files',
            action = GlobFiles,
            nargs = '+',
            help = 'Input json files.',
        )
        
        parser.add_argument(
            '-f', '--format',
            dest = 'format',
            action = 'store_true',
            help = 'Format json files.'
        )
        
        parser.add_argument(
            '-i', '--indent',
            dest = 'indent',
            type = int,
            help = 'Json indent',
            default = 2,
        )
    
    @classmethod
    def run_command(cls, args):
        import json
        
        for file in args.files:
            console.print(f'Formatting [yellow]{file}[/yellow]')
            try:
                encoding = charset_normalizer.from_path(file).best().encoding

                with open(file, 'r', encoding = encoding) as file_in:
                    data = json.load(file_in)
                with open(file, 'w', encoding = encoding) as file_out:
                    json.dump(
                        data,
                        file_out,
                        ensure_ascii = False,
                        indent = args.indent if args.format else None,
                    )
            except Exception as e:
                console.print(f'[red]Filed to format {file}[/red]')
                console.print(f'[red]{e}[/red]')
