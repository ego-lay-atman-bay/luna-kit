from .cli import CLI, CLICommand

@CLI.register_command
class SwfCommand(CLICommand):
    COMMAND = 'swf'
    HELP = 'Convert swf to animated webp'

    @classmethod
    def build_args(cls, parser):
        parser.add_argument(
            'swf_command',
            choices = ['render', 'fix'],
            help = 'Fix the swf or render it to an animated webp'
        )
        
        parser.add_argument(
            'input',
            help = 'Input swf file',
        )

        parser.add_argument(
            '-o', '--output',
            help = 'Output swf or animated webp file',
        )

        parser.add_argument(
            '--ffdec',
            dest = 'ffdec',
            help = "Path to ffdec.jar. Defaults to system installed ffdec (if it's available on the PATH)",
        )

    @classmethod
    def run_command(cls, args):
        from ..swf import SWF
        from ..console import console
        import shutil
        import os
        
        ffdec: str | None = args.ffdec

        if ffdec is None:
            ffdec = shutil.which('ffdec')
            if ffdec is None:
                console.print('Cannot find ffdec. Please either add it to the PATH or provide --ffdec ffdec.jar.\n\nYou can download ffdec from https://github.com/jindrapetrik/jpexs-decompiler/releases/latest')
                return

        command: str = args.swf_command
        input: str = args.input
        output: str | None = args.output

        if command == 'fix':
            if output is None:
                output = input
            
            console.print('Loading swf')
            swf = SWF(input, ffdec = ffdec)
            console.print('Fixing swf')
            swf.fix()
            swf.save(output)
            console.print(f'Saved to "{output}"')
        else:
            if output is None:
                output = os.path.splitext(input)[0] + '.webp'
            
            console.print('Loading swf')
            swf = SWF(input, ffdec = ffdec)
            console.print('Fixing swf')
            swf.fix()
            console.print('Rendering webp')
            swf.render_webp(output)
