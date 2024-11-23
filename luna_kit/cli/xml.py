from argparse import ArgumentParser, Namespace
import glob
import os

import charset_normalizer

from ..console import console
from .cli import CLI, CLICommand


@CLI.register_command
class XMLCommand(CLICommand):
    COMMAND = 'xml'
    HELP = 'easy xml tools'
    
    @classmethod
    def build_args(cls, parser: ArgumentParser):
        parser.add_argument(
            'file',
            nargs = '+',
            help = 'Input xml file(s)',
        )
        
        parser.add_argument(
            '-f', '--format',
            action = 'store_true',
            dest = 'format',
            help = 'Format xml files',
        )
        
        parser.add_argument(
            '-i', '--indent',
            dest = 'indent',
            help = 'Formatted indent level. Default to 4',
            default = 4,
            type = int,
        )
        
    @classmethod
    def run_command(cls, args: Namespace):
        from lxml import etree
        from bs4 import BeautifulSoup
        
        files = []
        
        for file in args.file:
            files.extend(glob.glob(file, recursive = True))
        
        for file in files:
            console.print(f'Formatting [yellow]{file}[/yellow]')
            soup = None
            encoding = 'utf-8'
            try:
                encoding = charset_normalizer.from_path(file).best().encoding
                
                with open(file, 'r', encoding = encoding) as file_in:
                    soup = BeautifulSoup(
                        file_in.read(),
                        'xml',
                        from_encoding = encoding,
                    )
            except Exception as e:
                e.add_note(f'file unable to read: {file}')
                raise e
            
            if soup is not None:
                with open(file, 'wb') as file_out:
                    file_out.write(soup.encode(
                        encoding = encoding,
                        indent_level = 4,
                    ))
            else:
                console.print(f'[yellow]failed to format {file}[/yellow]')
    
