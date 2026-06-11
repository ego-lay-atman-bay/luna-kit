from typing import TypedDict, Literal

class PrizeTypes(TypedDict):
    PrizeData: dict[str, dict[Literal['loc_string', 'image'], str]]
    PrizeStrings: dict[str, list[str]]
