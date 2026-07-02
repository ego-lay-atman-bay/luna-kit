from ..console import console
from .cli import CLI, CLICommand
from typing import overload
import argparse


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
            default = 'latest',
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

        parser.add_argument(
            '--force',
            dest = 'force',
            help = argparse.SUPPRESS,
            action = 'store_true',
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
        from ..api import API, Version, get_latest_version, DLCManifest
        import requests
        from requests import HTTPError
        import json
        
        if not args.astc_manifest and not args.dlc_manifest:
            if args.platform == 'android':
                args.astc_manifest = True
            elif args.platform == 'ios':
                args.dlc_manifest = True
        
        file_types = {
            'ark': 'ark',
            'arkdiff': 'arkdiff',
        }

        latest_version: Version | None = None

        raw_latest_version = get_latest_version()
        if raw_latest_version is not None:
            latest_version = Version.parse(raw_latest_version)
        else:
            response = requests.get('https://assets.all-the-ponies.com/game_version.json')
            if response.ok:
                latest_version = Version.parse(response.json()['game_version'])

        if latest_version is None:
            console.print('[red]Could not find version[/]')
            return

        raw_version: str = args.version

        if raw_version == 'latest':
            version = latest_version
            console.print(f'Found version [cyan]{latest_version}[/]')
        else:
            version = Version.parse(raw_version)
        
        if not args.force and version > latest_version:
            console.print('[red]Could not find version[/]')
            return
        
        api = API(
            args.platform,
            version,
        )
        
        downloaded = []
        output: str = os.path.abspath(args.output.format(version = version))
        output = output

        def download_files(manifest: DLCManifest):
            for file in manifest.get('dlc_items', []):
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
        
        astc_manifest: DLCManifest | None = None
        manifest: DLCManifest | None = None
        
        if args.astc_manifest:
            try:
                astc_manifest = api.get_astc_dlc_manifest()
                download_files(astc_manifest)
            except HTTPError:
                pass
        
        if args.dlc_manifest:
            try:
                manifest = api.get_dlc_manifest()
                download_files(manifest)
            except HTTPError:
                pass
        
        if manifest is astc_manifest is None:
            console.print('[red]Could not find version[/]')
            return
        
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
        
