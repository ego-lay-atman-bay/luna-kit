# from textwrap import dedent
from typing import IO

from lxml import etree

from .utils import strToFloat, strToInt


class ShopData():
    def __init__(self, file: str | IO) -> None:
        self.categories = {}
        
        tree = etree.parse(file)        
        
        root = tree.getroot()
        
        for element in root:
            if element.tag == 'ShopItemCategory':
                category = ShopCategory.from_xml(element)
                category_name = category.id
                self.categories[category_name] = category


class ShopItem():
    def __init__(
        self,
        id: str,
        unlock_value: int = 0,
        cost: int = 0,
        currency_type: int = 0,
        sort_price: float = 0.0,
        map_zone: int | list[int] = 0,
        task_token_id: str = "",
        quest: str = "",
    ) -> None:
        self.id = id
        self.unlock_value = unlock_value
        self.cost = cost
        self.currency_type = currency_type
        self.sort_price = sort_price
        self.map_zone = map_zone
        self.task_token_id = task_token_id
        self.quest = quest
    
    @classmethod
    def from_xml(self, xml: etree._Element):
        map_zone = xml.get('MapZone')
        
        if map_zone:
            map_zone = [strToInt(zone) for zone in map_zone.split(',')]

            if len(map_zone) == 1:
                map_zone = map_zone[0]
        
        return ShopItem(
            id = xml.get('ID'),
            unlock_value = strToInt(xml.get('UnlockValue')),
            cost = strToInt(xml.get('Cost')),
            currency_type = strToInt(xml.get('CurrencyType')),
            sort_price = strToFloat(xml.get('SortPrice')),
            map_zone = map_zone,
            task_token_id = xml.get('TaskTokenID'),
            quest = xml.get('Quest'),
        )

class ShopCategory():
    def __init__(
        self,
        id: str,
        label: str,
        items: list[ShopItem],
        is_visible: bool = True,
        icon: str = "",
        debug_only: bool = False,
        show_inventory: bool = False,
    ) -> None:
        self.id = id
        self.label = label
        self.is_visible = is_visible
        self.icon = icon
        self.debug_only = debug_only
        self.show_inventory = show_inventory
        
        self.items = items
        
    @classmethod
    def from_xml(cls, xml: etree._Element):
        id = xml.get('Name')
        label = xml.get('Label')
        icon = xml.get('Icon')
        is_visible = bool(strToInt(xml.get('IsVisible')))
        debug_only = bool(strToInt(xml.get('DebugOnly')))
        show_inventory = bool(strToInt(xml.get('ShowInventory')))
        
        items = []
        
        for child in xml:
            items.append(ShopItem.from_xml(child))
        
        return ShopCategory(
            id = id,
            label = label,
            items = items,
            is_visible = is_visible,
            icon = icon,
            debug_only = debug_only,
            show_inventory = show_inventory,
        )
    
    # def __repr__(self) -> str:
    #     return dedent(f"""\
    #         {self.__class__.__name__}(
    #             id = {self.id},
    #             label = {self.label},
    #             is_visible = {self.is_visible},
    #             icon = {self.icon},
    #             debug_only = {self.debug_only},
    #             show_inventory = {self.show_inventory},
    #         )""")

