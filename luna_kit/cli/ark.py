import os
from argparse import ArgumentParser, Namespace

from rich.progress import Progress, track, TextColumn, BarColumn, MofNCompleteColumn, TimeRemainingColumn

from ..console import console, track
from ._actions import GlobFiles
from .cli import CLI, CLICommand


@CLI.register_command
class ARKParser(CLICommand):
    COMMAND = 'ark'
    HELP = 'Extract .ark files'
    
    @classmethod
    def build_args(cls, parser: ArgumentParser):
        subcommand = parser.add_subparsers(
            title = 'Action',
            dest = 'action',
        )

        list_ = subcommand.add_parser(
            'list',
            help = 'List all files in an ark file',
        )

        list_.add_argument(
            'files',
            nargs = '+',
            help = 'input .ark files',
            action = GlobFiles,
        )

        extract = subcommand.add_parser(
            'extract',
            help = 'Extract ark files',
        )
        
        extract.add_argument(
            'files',
            nargs = '+',
            help = 'input .ark files',
            action = GlobFiles,
        )

        extract.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'Output folder. Defaults to the ark filename. You can add {name} for the ark filename.',
        )

        extract.add_argument(
            '-i', '--ignore-errors',
            dest = 'ignore_errors',
            help = "Don't exit on error",
            action = 'store_true',
        )

        extract.add_argument(
            '-f', '--filter', '--files',
            dest = 'filter',
            nargs = '+',
            help = 'Only extract these files. Can be glob pattern.'
        )

        create = subcommand.add_parser(
            'create',
            help = 'Create an ark file',
        )

        add = subcommand.add_parser(
            'add',
            help = 'Add files to an ark file',
        )

        for action in [create, add]:
            action.add_argument(
                'input_files',
                nargs = '+',
                help = 'input files/folders to add. Will stript dirnames.',
                # action = GlobFiles,
            )

            action.add_argument(
                '-t', '--use-system-timestamps',
                dest = 'use_system_timestamps',
                action = 'store_true',
                help = 'Use the last modified time on files instead of the current date.',
            )

            action.add_argument(
                '-o', '--output',
                dest = 'output',
                help = 'Output .ark file.',
                required = True,
            )
    
    @classmethod
    def run_command(cls, args: Namespace):
        import os
        import fnmatch
        
        from ..ark import ARK
        from ..ark_filename import sort_ark_filenames

        if args.action == 'list':
            files: list[str] = args.files
            for filename in files:
                console.print(f'[yellow]{os.path.basename(filename)}[/]')
                with ARK(filename) as ark:
                    for info in ark.infolist():
                        print(info.filename, info.timestamp)
        
        elif args.action == 'extract':
            arks: list[str] = args.files
            if len(arks) == 0:
                console.print('[red]No ark files found[/]')
                return
            
            try:
                arks = sort_ark_filenames(arks)
            except:
                console.print_exception()
                console.print('[red]Could not smart sort files, sorting alphabetically[/]')
                arks.sort()
            
            if args.output is None:
                base_output = './{name}'
            else:
                base_output: str = args.output
            
            base_output = os.path.abspath(base_output)

            for ark_filename in arks:
                output = base_output.format(name = os.path.splitext(os.path.basename(ark_filename)))
                errors = 0
                try:
                    with ARK(ark_filename) as ark:
                        console.print(f'Extracting [yellow]{os.path.basename(ark_filename)}[/]')
                        for filename in track(
                            ark.namelist(),
                            description = 'Extracting...',
                            transient = True,
                            columns = [
                                TextColumn("[progress.description]{task.description}"),
                                BarColumn(),
                                MofNCompleteColumn(),
                                TimeRemainingColumn(),
                            ]
                        ):
                            if isinstance(args.filter, list) and not any(fnmatch.fnmatch(filename, pattern) for pattern in args.filter):
                                continue
                            try:
                                ark.extract(filename, output)
                            except Exception as e:
                                e.add_note(f'filename: {filename}')
                                errors += 1
                                if args.ignore_errors:
                                    console.print(e)
                                else:
                                    raise e
                    
                    console.print(f'[{"green" if errors == 0 else "yellow"}]Finished with {errors} errors[/]')

                except Exception as e:
                    e.add_note(f'ark: {os.path.basename(ark_filename)}')
                    raise e
        elif args.action in ['add', 'create']:
            output: str = os.path.abspath(args.output)
            os.makedirs(os.path.dirname(output), exist_ok = True)

            mode = 'a' if args.action == 'add' else 'w'

            # list[tuple[filename, arcname]]
            added_files: list[tuple[str, str]] = []

            for filename in args.input_files:
                filename: str
                arcname = None
                if '=' in filename:
                    filename, arcname = filename.rsplit('=', 1)
                
                if os.path.isfile(filename):
                    if arcname is None:
                        arcname = os.path.basename(filename)
                    
                    added_files.append((filename, arcname))
                elif os.path.isdir(filename):
                    if arcname is None:
                        arcname = ''
                    for dirpath, dirnames, filenames in os.walk(filename):
                        for file in filenames:
                            added_files.append((
                                os.path.join(dirpath, file),
                                os.path.join(arcname, os.path.relpath(os.path.join(dirpath, file), filename)),
                            ))
                else:
                    console.print(f'[red]file "{filename}" not found[/]')
            
            if len(added_files) == 0:
                console.print('[red]No files to add[/]')
                return

            with ARK(output, mode) as arkfile:
                for inpath, arcname in added_files:
                    arkfile.write(
                        inpath,
                        arcname,
                        use_edit_time = args.use_system_timestamps,
                    )
            
            console.print(f'[green]Added {len(added_files)} files[/]')

