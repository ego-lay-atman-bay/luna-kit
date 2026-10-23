import argparse
from argparse import Action
import glob
import logging
import os
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
                os.path.expanduser(value),
                recursive = True,
                include_hidden = True,
            ))
        
        logging.debug(f'found: {result}')
        
        setattr(namespace, self.dest, result)
    
    def format_usage(self):
        return 'hello'
