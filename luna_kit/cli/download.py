from ..console import console
from .cli import CLI, CLICommand
from typing import overload


class Version:
    major: int
    minor: int
    patch: int
    letter: str

    @overload
    def __init__(self, major: int, minor: int, patch: int, letter: str) -> None: ...
    @overload
    def __init__(self, version: str) -> None: ...
    def __init__(self, *args, **kwargs) -> None:
        if len(args) == 1 or 'version' in kwargs:
            pass

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}.{self.patch}{self.letter}'


@CLI.register_command
class DownloadCommand(CLICommand):
    COMMAND = 'download'
    HELP = 'download ark files'
    API_REQUIRED = False
    
    @classmethod
    def build_args(cls, parser):
        parser.add_argument(
            '-o', '--output',
            dest = 'output',
            help = 'output folder',
            default = './'
        )
        
        parser.add_argument(
            '-p', '--platform',
            dest = 'platform',
            choices = ['android', 'ios', 'windows'],
            help = 'Platform to download the arkf iles for',
            default = 'android',
        )
        
        parser.add_argument(
            '-v', '--version',
            dest = 'version',
            help = 'version to download the ark files for',
            required = True,
        )
        
        parser.add_argument(
            '-a', '--astc-manifest',
            dest = 'astc_manifest',
            action = 'store_true',
            help = 'Download from astc_dlc_manifest',
        )
        
        parser.add_argument(
            '-d', '--dlc-manifest',
            dest = 'dlc_manifest',
            action = 'store_true',
            help = 'Download from dlc_manifest',
        )
        
        # parser.add_argument(
        #     '-m', '--manifest',
        #     dest = 'manifest',
        #     help = 'Select which ',
        #     action = 'store_true',
        # )
        
        parser.add_argument(
            '-c', '--calibre',
            dest = 'calibre',
            choices = ['low', 'high', 'veryhigh', 'all'],
            nargs = '+',
            help = 'Only download from this device calibre.',
            default = ['veryhigh'],
        )
        
        parser.add_argument(
            '-t', '--tag',
            dest = 'tags',
            nargs = '+',
            help = "Only download files with these tags. You can choose from: 'mlpextra', 'mlpdata', 'mlpextragui', 'mlpextra2', 'video', and 'softdlc'",
        )
        
        parser.add_argument(
            '-f', '--files',
            dest = 'files',
            nargs = '+',
            choices = [
                'all',
                'ark',
                'arkdiff',
                'other',
            ],
            default = ['ark'],
            help = 'Only download these files.',
        )
        
        parser.add_argument(
            '--dry-run',
            dest = 'dry_run',
            action = 'store_true',
            help = 'Only print files that would be downloaded',
        )

        parser.add_argument(
            '--chunk-size',
            dest = 'chunk_size',
            type = int,
        )
        
    
    @classmethod
    def run_command(cls, args):
        import os
        from ..api import API
        from requests import HTTPError
        
        if not args.astc_manifest and not args.dlc_manifest:
            if args.platform == 'android':
                args.astc_manifest = True
            elif args.platform == 'ios':
                args.dlc_manifest = True
        
        file_types = {
            'ark': 'ark',
            'arkdiff': 'arkdiff',
        }
        
        api = API(
            args.platform,
            args.version,
            
        )
        
        downloaded = []
        output = os.path.abspath(args.output)
        
        def download_files(manifest: dict):
            for file in manifest.get('dlc_items', []):
                file: dict
                filename: str = file.get('filename')
                
                if filename in downloaded:
                    continue
                
                if args.files and ('all' not in args.files) and file_types.get(os.path.splitext(filename)[1][1:].lower(), 'other') not in args.files:
                    console.print(f'skipping {filename}')
                    continue
                
                if args.calibre and ('all' not in args.calibre) and (file.get('device_calibre', 'all') != 'all'):
                    if file.get('device_calibre') not in args.calibre:
                        console.print(f'skipping {file.get("filename")}')
                        continue
                
                if args.tags and file.get('tag', '') not in args.tags:
                    console.print(f'skipping {file.get("filename")}')
                    continue
                
                console.print(f'downloading [yellow]{filename}[/]')

                # os.makedirs(
                #     os.path.dirname(os.path.join(output, filename)),
                #     exist_ok = True,
                # )
                
                if not args.dry_run:
                    try:
                        with api.download_asset(
                            filename,
                            file = os.path.join(output, filename),
                            stream = True,
                            asset_hash = file.get('asset_hash'),
                        ) as downloader:
                            downloader.response.raise_for_status()
                            downloader.full_download(console)
                    except HTTPError:
                        console.print('failed to download')
        
        if args.astc_manifest:
            try:
                astc_manifest = api.get_astc_dlc_manifest()
                download_files(astc_manifest)
            except HTTPError:
                console.print('Faled to download astc_dlc_manifest')
        
        if args.dlc_manifest:
            try:
                manifest = api.get_dlc_manifest()
                download_files(manifest)
            except HTTPError:
                console.print('Faled to download dlc_manifest')
        
        app_files = []
        
        if api.client_id.platform == 'android':
            if ((not args.tags) or (args.tags and 'startup' in args.tags)) and ('ark' in args.files or 'all' in args.files):
                app_files.append('000_and_startup_common.ark')
        elif api.client_id.platform == 'ios':
            # app_files.extend([
            #     '000_ios_bundled_common.ark',
            #     '000_ios_startup_common.ark',
            # ])
            pass
        elif api.client_id.platform == 'windows':
            app_files.extend([
                '000_win_bundled.ark',
                '000_win_bundled_common.ark',
                '000_win_bundled_veryhigh.ark',
                '000_win_startup.ark',
                '000_win_startup_common.ark',
            ])
        
        for file in app_files:
            console.print(f'downloading [yellow]{file}[/]')
            if not args.dry_run:
                try:
                    # os.makedirs(
                    #     os.path.dirname(os.path.join(output, file)),
                    #     exist_ok = True,
                    # )
                    with api.download_asset(
                        file,
                        file = os.path.join(output, file),
                        stream = True,
                    ) as downloader:
                        downloader.response.raise_for_status()
                        downloader.full_download(console)
                except HTTPError:
                    console.print('[red]download failed[/]')
        
