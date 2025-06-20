from ..console import console
from ._actions import GlobFiles
from .cli import CLI, CLICommand

@CLI.register_command
class DumpCommand(CLICommand):
    COMMAND = 'dump'
    HELP = "Dump all files in .ark files, as well as put them all in a more readable format."

    @classmethod
    def build_args(cls, parser):
        parser.add_argument(
            'files',
            action = GlobFiles,
            nargs = '+',
            help = 'Input .ark files',
        )

        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'Output folder for dumped files',
            default = '{dir}/{name}',
        )

        parser.add_argument(
            '-i', '--ignore-errors',
            dest = 'ignore_errors',
            action = 'store_true',
            help = 'ignore errors',
        )

        parser.add_argument(
            '-f', '--filter',
            dest = 'filter',
            help = 'Filter extracted files based on glob pattern',
        )

        parser.add_argument(
            '-a', '--no-atlas',
            dest = 'atlas',
            action = 'store_false',
            help = "Don't split texatlas files",
        )

        parser.add_argument(
            '-l', '--no-loc',
            dest = 'loc',
            action = 'store_false',
            help = "Don't convert .loc files",
        )

        parser.add_argument(
            '-lf', '--loc-format',
            dest = 'loc_format',
            choices = ['json', 'csv'],
            help = '.loc converted file format',
            default = 'json',
        )

        parser.add_argument(
            '-j', '--no-json',
            dest = 'json',
            action = 'store_false',
            help = "Don't format json files",
        )

        parser.add_argument(
            '-ji', '--json-indent',
            dest = 'json_indent',
            type = int,
            default = 2,
            help = 'Json indent level',
        )

        parser.add_argument(
            '-x', '--no-xml',
            dest = 'xml',
            action = 'store_false',
            help = "Don't format xml files",
        )

        parser.add_argument(
            '-p', '--no-pvr',
            dest = 'pvr',
            action = 'store_false',
            help = "Don't convert pvr files",
        )

        parser.add_argument(
            '-pf', '--pvr-format',
            dest = 'pvr_format',
            help = 'pvr file format',
            default = 'png',
        )
    
    @classmethod
    def run_command(cls, args):
        from typing import Iterable, Optional, Sequence, Union
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            ProgressType,
            TextColumn,
            TimeRemainingColumn,
        )

        import os
        from fnmatch import fnmatch
        from glob import glob
        import charset_normalizer
        from ..safe_format import safe_format
        from ..ark import ARK
        from ..ark_filename import sort_ark_filenames
        from ..xml import parse_xml, tostring
        from ..texatlas import TexAtlas
        from ..loc import LOC
        from ..pvr import PVR
        import json
        import csv

        COLUMNS = [
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
        ]

        def track(
            sequence: Union[Iterable[ProgressType], Sequence[ProgressType]],
            total: Optional[float] = None,
            description: str = 'Working...',
            transient: bool = False,
        ):
            progress = Progress(
                *COLUMNS,
                console = console,
                transient = transient,
            )

            with progress:
                yield from progress.track(
                    sequence = sequence,
                    description = description,
                )

        def glob_files(pattern: str, folders: list[str] | set[str]) -> set[str]:
            files = set()
            for folder in folders:
                files |= {os.path.join(folder, file) for file in glob(
                    pattern,
                    root_dir = folder,
                    recursive = True,
                    include_hidden = True,
                )}
            return files

        base_output = args.output

        arks = args.files
        if len(arks) == 0:
            console.print('[red]No ark files found[/]')
            return

        try:
            arks = sort_ark_filenames(files)
        except:
            arks.sort()

        extracted_folders = set()

        console.print('Extracting ark files')

        for ark_filename in arks:
            ark_filename = os.path.abspath(ark_filename)
            folder = os.path.abspath(safe_format(
                base_output,
                name = os.path.splitext(os.path.basename(ark_filename))[0],
                dir = os.path.dirname(ark_filename),
            ))
            extracted_folders.add(folder)
            try:
                with ARK(ark_filename) as ark:
                    for file_metadata in track(
                        ark.files,
                        description = os.path.basename(ark_filename),
                        transient = True,
                    ):
                        if args.filter and (not fnmatch(file_metadata.full_path, args.filter)):
                            continue
                        try:
                            file = ark.extract(file_metadata)
                            filepath = os.path.join(folder, file_metadata.full_path)
                            file.save(filepath)
                        except Exception as e:
                            e.add_note(f'filename: {file_metadata.full_path}')
                            if args.ignore_errors:
                                console.print(e)
                            else:
                                raise e
            except Exception as e:
                e.add_note(f'ark: {os.path.basename(ark_filename)}')
                raise e
            
        if args.loc:
            console.print('Converting loc files')
            loc_files = glob_files('**/*.loc', extracted_folders)

            for loc_filename in track(
                loc_files,
                description = 'Converting...',
                transient = True,
            ):
                loc = LOC(loc_filename)
                loc_output = os.path.splitext(loc_filename)[0] + f'.{args.loc_format}'
                match args.loc_format:
                    case 'json':
                        loc.export(loc_output, indent = args.json_indent)
                    case 'csv':
                        with open(loc_output, 'w', newline = '', encoding = 'utf-8') as csvfile:
                            writer = csv.writer(csvfile)
                            writer.writerow(['key', 'string'])
                            writer.writerows(loc.items())
            
        if args.json:
            console.print('Formatting json files')
            json_files = glob_files('**/*.json', extracted_folders)
            
            for json_filename in track(
                json_files,
                description = 'Formatting...',
                transient = True,
            ):
                encoding = charset_normalizer.from_path(json_filename).best().encoding

                with open(json_filename, 'r+', encoding = encoding) as file:
                    data = json.load(file)
                    file.seek(0)
                    file.truncate()
                    json.dump(
                        data,
                        file,
                        indent = None if args.json_indent == 0 else args.json_indent,
                        ensure_ascii = False,
                    )
        
        if args.xml:
            console.print('Formatting xml file')
            xml_files = glob_files('**/*.xml', extracted_folders)

            for xml_filename in track(
                xml_files,
                description = 'Formatting...',
                transient = True,
            ):
                root, encoding = parse_xml(xml_filename, with_encoding = True)
                with open(xml_filename, 'wb') as file:
                    file.write(tostring(
                        root,
                        xml_declaration = True,
                        encoding = encoding,
                        pretty_print = True,
                    ))
    
        if args.atlas:
            console.print('Splitting texatlas files')
            atlas_files = glob_files('*/**.texatlas', extracted_folders)

            with Progress(*COLUMNS, console = console, transient = True) as progress:
                atlas_progress = progress.add_task('Splitting...')
                files_progress = progress.add_task('Splitting...', total = len(atlas_files))

                for atlas_filename in atlas_files:
                    atlas = TexAtlas(atlas_filename)
                    progress.update(
                        atlas_progress,
                        description = os.path.basename(atlas_filename),
                        total = len(atlas.images),
                        completed = 0,
                    )
                    for image in atlas.images:
                        image_filename = os.path.join(image.dir, image.filename)
                        if not os.path.exists(image_filename):
                            os.makedirs(os.path.dirname(image_filename), exist_ok = True)
                            image.image.save(image_filename)
                        
                        progress.update(atlas_progress, advance = 1)
                    progress.update(files_progress, advance = 1)

        if args.pvr:
            console.print('Converting pvr files')
            pvr_files = glob_files('**/*.pvr', extracted_folders)

            for pvr_file in track(
                pvr_files,
                description = 'Converting...',
                transient = True,
            ):
                if pvr_file.endswith('.alpha.pvr'):
                    continue

                pvr = PVR(pvr_file, external_alpha = True)
                pvr.save(f'{os.path.splitext(pvr_file)[0]}.{args.pvr_format}')

        console.print('Finished!')
