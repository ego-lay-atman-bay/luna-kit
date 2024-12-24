from argparse import ArgumentParser, Namespace
from .cli import CLI, CLICommand
from ._actions import GlobFiles

@CLI.register_command
class LOCCommand(CLICommand):
    COMMAND = 'loc'
    HELP = 'Convert .loc localization files to json.'

    @classmethod
    def build_args(cls, parser: ArgumentParser):
        parser.add_argument(
            'files',
            nargs = '+',
            action = GlobFiles,
            help = 'input .loc file(s)',
        )
        
        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'output filename, such as "english.json". Can also have {name} to replace the filename.',
        )
        
        parser.add_argument(
            '-y',
            dest = 'override',
            action = 'store_true',
            help = 'Override output file if it already exists without prompt.',
        )
        
        parser.add_argument(
            '-f', '--format',
            dest = 'format',
            choices = ['json', 'csv'],
            help = "Output format.",
            default = 'json',
        )
        
        parser.add_argument(
            '-i', '--indent',
            dest = 'indent',
            type = int,
            help = 'Json indent.'
        )
        
    
    @classmethod
    def run_command(cls, args: Namespace):
        from ..loc import LOC
        import os
        from ..console import console
        import csv
        
        for file in args.files:
            output: str = f'{{name}}.{args.format}'
            if args.output:
                output = args.output
            
            output = output.format(name = os.path.splitext(os.path.basename(file))[0])
            
            if not args.override and os.path.exists(output):
                if input(f'"{output}" already exists, do you want to override it? (Y/n): ').lower() in ['n', 'no', 'false', '0']:
                    continue
            
            loc_file = LOC(file)
            if args.format == 'json':
                loc_file.export(output, indent = args.indent)
            elif args.format == 'csv':
                with open(output, 'w', newline = '', encoding = 'utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['key', 'string'])
                    writer.writerows(loc_file.strings.items())
            
            console.print(f'saved [yellow]{output}[/]')
