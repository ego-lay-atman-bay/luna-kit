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
        
    @classmethod
    def run_command(cls, args: Namespace):
        from lxml import etree
        from ..xml import parse_xml, tostring
        
        files = []
        
        for file in args.file:
            files.extend(glob.glob(file, recursive = True))
        
        for file in files:
            console.print(f'Formatting [yellow]{file}[/yellow]')
            root = []
            encoding = 'utf-8'
            try:
                root, encoding = parse_xml(file, with_encoding = True)
            except Exception as e:
                e.add_note(f'file unable to read: {file}')
                raise e
            
            if len(root):
                with open(file, 'wb') as file_out:
                    file_out.write(tostring(
                        root,
                        xml_declaration = True,
                        encoding = encoding,
                        pretty_print = args.format,
                    ))
                    # for index, child in enumerate(root):
                    #     if isinstance(child, str):
                    #         continue
                    #     xml_string = etree.tostring(
                    #         child,
                    #         xml_declaration = index == 0,
                    #         encoding = encoding,
                    #         pretty_print = args.format,
                    #         with_tail = False,
                    #     )
                    #     file_out.write(
                    #         xml_string
                    #     )
            else:
                console.print(f'[yellow]failed to format {file}[/yellow]')
            
            # if soup is not None:
            #     with open(file, 'wb') as file_out:
            #         file_out.write(soup.encode(
            #             encoding = encoding,
            #             indent_level = 4,
            #         ))
            # else:
            #     console.print(f'[yellow]failed to format {file}[/yellow]')
    
