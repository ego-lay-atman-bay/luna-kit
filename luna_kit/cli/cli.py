import sys
from abc import abstractmethod
from argparse import ArgumentParser, Namespace
from typing import Type


class CLI():
    def __init__(self, argv: list[str]) -> None:
        self.argparser = ArgumentParser(
            description = 'Decrypt .ark files from My Little Pony Magic Princess (the Gameloft game).',
        )
        self.subparser = self.argparser.add_subparsers(
            title = 'commands',
            dest = 'command',
        )
        
        self.build_args()
    
    COMMANDS: 'dict[str,CLICommand]' = {}
    
    @classmethod
    def register_command(cls, command: 'Type[CLICommand]'):
        if not issubclass(command, CLICommand):
            raise TypeError('action must inherit from CLIAction')
        
        cls.COMMANDS[command.COMMAND] = command
        
        return command
    
    def build_args(self):
        for command in self.COMMANDS.values():
            command.build_args(self.subparser.add_parser(
                command.COMMAND,
                help = command.HELP,
            ))
            
    def parse_args(self, argv: list[str]):
        if len(argv) < 1:
            self.argparser.print_help()
            sys.exit()
        
        args = self.argparser.parse_args(argv)
        
        
        command = self.COMMANDS.get(args.command)
        if command:
            command.run_command(args)

class CLICommand():
    COMMAND = ''
    HELP = ''
    
    @classmethod
    @abstractmethod
    def build_args(cls, parser: ArgumentParser):
        ...
    
    @classmethod
    @abstractmethod
    def run_command(cls, args: Namespace):
        ...


def register_command[T](cls: T) -> T:
    CLI.register_command(cls)

    return cls
