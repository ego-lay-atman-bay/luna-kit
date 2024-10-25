from typing import IO, Literal

from lxml import etree

from ._gameobjects import GameObject, PonyObject


class GameObjectData():
    categories: dict
    
    def __init__(self, file: str | IO) -> None:
        self.categories: dict[Literal['Pony'] | str, list[GameObject | PonyObject]] = {}
        
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
