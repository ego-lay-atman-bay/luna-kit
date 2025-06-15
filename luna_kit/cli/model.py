from .cli import CLI, CLICommand
from ._actions import GlobFiles
from ..console import console

@CLI.register_command
class ModelCommand(CLICommand):
    COMMAND = 'model'
    HELP = "Get info about models (converting models directly isn't supported yet)"

    @classmethod
    def build_args(cls, parser):
        parser.add_argument(
            'files',
            action = GlobFiles,
            help = 'Input .ark files',
            nargs = '+',
        )

    @classmethod
    def run_command(cls, args):
        from ..model import RKModel
        import os
        
        if len(args.files) == 0:
            console.print('[red]No files found[/]')
            return

        first = True

        for filename in args.files:
            model = RKModel(filename)

            if not first:
                console.line()
                console.rule()
                console.line()
            first = False

            console.print(f'[yellow]{os.path.basename(filename)}[/]')
            console.print(f'Name: [green]{model.name}[/]')
            console.print(f'Vertices: {len(model.verts)}')
            console.print(f'Bones: {len(model.bones)}')
            console.line()
            console.print(f'Meshes: {len(model.meshes)}')
            for mesh in model.meshes:
                console.print(f'  Name: [green]{mesh.name}[/]')
                console.print(f'  Triangles: {len(mesh.triangles)}')
            
            console.line()
            console.print(f'Material: {len(model.materials)}')
            for material in model.materials:
                
                if material.name != material.properties.DiffuseTexture:
                    console.print(f'  Name: [green]{material.name}[/]')
                
                console.print(f'  Texture: [green]{material.properties.texture_name}[/]')
