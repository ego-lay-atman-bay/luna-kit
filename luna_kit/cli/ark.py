from argparse import ArgumentParser, Namespace
from .cli import CLI, CLICommand

@CLI.register_command
class ARKParser(CLICommand):
    COMMAND = 'ark'
    HELP = 'Extract .ark files'
    
    @classmethod
    def build_args(cls, parser: ArgumentParser):
        parser.add_argument(
            'files',
            nargs = '+',
            help = 'input .ark files',
        )
        
        parser.add_argument(
            '-f', '--separate-folders',
            dest = 'separate_folders',
            help = 'Output each .ark file in separate folders',
            action = 'store_true',
        )
        
        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'output directory for .ark file(s)',
        )
        
        parser.add_argument(
            '-i', '--ignore-errors',
            dest = 'ignore_errors',
            action = 'store_true',
            help = 'ignore errors',
        )
    
    @classmethod
    def run_command(cls, args: Namespace):
        from ..ark import ARK
        from glob import glob
        import os
            
        output = './'
        
        files = []
        for pattern in args.files:
            files.extend(glob(pattern))
        
        if args.output:
            output = args.output
        elif len(files) == 1:
            output = os.path.splitext(os.path.basename(args.files[0]))[0]
        
        if len(files) == 1:
            ark_file = ARK(args.files[0], output = output, ignore_errors = args.ignore_errors)
        else:
            for filename in files:
                filename: str
                if args.separate_folders:
                    path = os.path.join(output, os.path.splitext(os.path.basename(filename))[0])
                else:
                    path = output
                
                ark_file = ARK(filename, output = path, ignore_errors = args.ignore_errors)
