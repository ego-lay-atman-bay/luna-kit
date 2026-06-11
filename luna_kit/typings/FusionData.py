from typing import TypedDict

class FusionItem(TypedDict):
    id: str
    val: int

class FusionData(TypedDict):
    DecoreList: list[FusionItem]
    coinsMultiplayer: list[float]
