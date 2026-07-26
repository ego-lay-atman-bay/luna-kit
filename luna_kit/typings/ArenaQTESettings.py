from typing import TypedDict, Literal

class ActionBar(TypedDict):
    HaveCritZone: bool
    CappingType: int
    Weight: float
    EffectType: int
    BasicWidth: float
    EffectValue: float
    LootCount: int
    CappingAmount: int
    BarType: int
    CritWidth: float
    Loot: str
    IconScale: float

class ActionStage(TypedDict):
    ExtraBlankChance: float
    Progress: float
    MinBlankBars: int

class ArenaQTPresetType(TypedDict):
    ActionBars: list[ActionBar]
    ActionGapMax: int
    ActionHitsNum: int
    ActionGapMin: int
    ActionBossPointerForwardSpeed: float
    ID: str
    ActionBossSpeed: float
    ActionCritMultiplier: int
    ActionCritChance: float
    ActionStages: list[ActionStage]
    ActionBossPointerBackwardSpeed: float

class ArenaQTESettingsType(TypedDict):
    Presets: list[ArenaQTPresetType]
