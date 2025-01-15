from rich import progress

from ..console import console
from ._actions import GlobFiles
from .cli import CLI, CLICommand


@CLI.register_command
class PVRCommand(CLICommand):
    COMMAND = "pvr"
    HELP = "Read PVR files encoded with astc encoding."
    
    @classmethod
    def build_args(cls, parser):
        parser.add_argument(
            'files',
            action = GlobFiles,
            help = 'File or files to read',
        )
        
        parser.add_argument(
            '-s', '--show',
            dest = 'show',
            action = 'store_true',
            help = 'Show the pvr file in the default image viewer.',
        )
        
        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'Output file. Can be directory or filename including {name} and {ext}',
        )
        
        parser.add_argument(
            '-f', '--format',
            dest = 'format',
            help = 'Output format to save to. If this is omitted, it will use the format guessed from the output file extension. If the output is a folder, then it will use png.',
        )
        
        confirm = parser.add_mutually_exclusive_group()
        
        confirm.add_argument(
            '-y', '--yes',
            dest = 'yes',
            action = 'store_true',
            help = 'Override files without confirmation.',
        )
        
        confirm.add_argument(
            '-n', '--no',
            dest = 'no',
            action = 'store_true',
            help = "Don't override existing files without confirmation.",
        )
    
    @classmethod
    def run_command(cls, args):
        import os

        from ..pvr import PVR
        from ..safe_format import safe_format
        from ..utils import get_PIL_format, strToBool
        
        def save_image(file: str, ):
            console.print(f'reading [yellow]{file}[/]')
            pvr = PVR(file)
            output = args.output
            name = os.path.splitext(os.path.basename(file))[0]
            if output:
                output = safe_format(
                    output,
                    name = name,
                )
                if output == args.output:
                    if len(args.files) > 1:
                        output = os.path.join(output, name + '.{format}')
                        if args.format is None:
                            args.format = "PNG"
                
                ext = os.path.splitext(os.path.basename(output))[1]
                if args.format is None:
                    format = ext[1:]
                    
                    try:
                        format = get_PIL_format(ext)
                    except ValueError:
                        output = safe_format(
                            output,
                            format = format.lower(),
                        )
                        ext = os.path.splitext(os.path.basename(output))[1]
                        
                        try:
                            format = get_PIL_format(ext)
                        except ValueError:
                            format = ext[1:]
                else:
                    format = args.format
                
                output = safe_format(
                    output,
                    format = format.lower(),
                )
                
                # console.print(f'saving [yellow]{output}[/]')
                
                dir = os.path.dirname(output)
                if dir:
                    os.makedirs(os.path.dirname(output), exist_ok = True)
                override = True
                if os.path.exists(output):
                    override = None
                    if args.yes or args.no:
                        override = args.yes
                    if override is None:
                        
                        override = console.input(f'[yellow]{output}[/yellow] already exists, do you want to override it? [dim](Y/n)[/]: ')
                        if override == '':
                            override = True
                        else:
                            override = strToBool(override)
                
                if override:
                    pvr.save(output)
            if args.show:
                pvr.show(name)
                
            
        
        for file in progress.track(
            args.files,
            description = 'saving...',
            console = console,
            
        ):
            save_image(file)
        
