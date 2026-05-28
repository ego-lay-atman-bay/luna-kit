from .cli import CLI, CLICommand

@CLI.register_command
class SwfCommand(CLICommand):
    COMMAND = 'swf2webp'
    HELP = 'Convert swf to animated webp'

    @classmethod
    def build_args(cls, parser):
        parser.add_argument(
            'input',
            help = 'Input swf file',
        )

        parser.add_argument(
            'output',
            help = 'Output animated webp file',
        )

        parser.add_argument(
            '--ffdec',
            dest = 'ffdec',
            help = "Path to ffdec.jar. Defaults to system installed ffdec (if it's available on the PATH)",
        )

    @classmethod
    def run_command(cls, args):
        from ..swf2webp import swf2webp
        from ..console import console
        import shutil
        
        ffdec = args.ffdec

        if ffdec is None:
            ffdec = shutil.which('ffdec')
            if ffdec is None:
                console.print('Cannot find ffdec. Please either add it to the PATH or provide --ffdec ffdec.jar.\n\nYou can download ffdec from https://github.com/jindrapetrik/jpexs-decompiler/releases/latest')
                return

        swf2webp(args.input, args.output, ffdec_path = ffdec, console = console)
