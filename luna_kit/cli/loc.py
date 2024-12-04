from argparse import ArgumentParser, Namespace
from .cli import CLI, CLICommand

@CLI.register_command
class LOCCommand(CLICommand):
    COMMAND = 'loc'
    HELP = 'Convert .loc localization files to json.'

    @classmethod
    def build_args(cls, parser: ArgumentParser):
        parser.add_argument(
            'file',
            help = 'input .loc file',
        )
        
        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'output filename, such as "english.json"',
        )
        
        parser.add_argument(
            '-y',
            dest = 'override',
            action = 'store_true',
            help = 'Override output file if it already exists without prompt.',
        )
    
    @classmethod
    def run_command(cls, args: Namespace):
        from ..loc import LOC
        import os
        from ..console import console
            
        if not os.path.isfile(args.file):
            raise FileNotFoundError(f'file "{args.file}" does not exist or is a directory.')
        
        output = os.path.splitext(os.path.basename(args.file))[0] + '.json'
        if args.output:
            output = output
        
        if not args.override and os.path.exists(output):
            if input(f'"{output}" already exists, do you want to override it? (Y/n): ').lower() in ['n', 'no', 'false', '0']:
                exit()
        
        loc_file = LOC(args.file)
        loc_file.export(output, indent = 2)
        
        console.print(f'saved to {output}')
