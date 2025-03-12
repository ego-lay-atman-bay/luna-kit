import argparse
import glob
import logging
from argparse import Action
from typing import Any


class GlobFiles(Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ):
        
        logging.debug(f'glob files: {values}')

        result = []
        
        if isinstance(values, str):
            values = [values]
        
        for value in values:
            result.extend(glob.glob(
                value,
                recursive = True,
                include_hidden = True,
            ))
        
        setattr(namespace, self.dest, result)
    
    def format_usage(self):
        return 'hello'
