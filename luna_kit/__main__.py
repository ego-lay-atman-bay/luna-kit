import os, sys, argparse

from .ark import ARK
from .console import console

console.quiet = False

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description = 'Decrypt .ark files from My Little Pony Magic Princess (the Gameloft game).',
    )
    
    subparsers = arg_parser.add_subparsers(
        title = 'commands',
        dest = 'command',
    )
    
    ark_parser = subparsers.add_parser(
        'ark',
        help = 'Extract .ark files',
    )
    
    ark_parser.add_argument(
        'files',
        nargs = '+',
        help = 'input .ark files',
    )
    
    ark_parser.add_argument(
        '-o', '--output',
        dest = 'output',
        help = 'output directory for .ark file(s)',
    )
    
    if len(sys.argv[1:]) < 1:
        arg_parser.print_help()
        sys.exit()
    
    args = arg_parser.parse_args()
    
    if args.command == 'ark':
        output = './'
        
        if args.output:
            output = args.output
        elif len(args.files) == 1:
            output = os.path.splitext(os.path.basename(args.files[0]))[0]
        
        if len(args.files) == 1:
            ark_file = ARK(args.files[0], output = output)
        else:
            for filename in args.files:
                filename: str
                ark_file = ARK(filename, output = os.path.join(output, os.path.splitext(os.path.basename(filename))[0]))
