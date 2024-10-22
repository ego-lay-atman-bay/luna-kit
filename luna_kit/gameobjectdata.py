import contextlib
import io
import os
from itertools import zip_longest

from lxml import etree

from ._gameobjects import GameObject


class GameObjectData():
    categories: dict
    
    def __init__(self, file) -> None:
        self.categories = {}
        
        tree = etree.parse(file)
        
        root = tree.getroot()
        
        for element in root:
            if element.tag == 'Category':
                category = []
                category_name = element.get('ID', '')
                self.categories[category_name] = category

                for child in element:
                    if child.tag == 'GameObject':
                        category.append(GameObject.from_category(child, category_name))
