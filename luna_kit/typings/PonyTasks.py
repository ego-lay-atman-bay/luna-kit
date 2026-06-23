from typing import NotRequired, TypedDict

    
class CustomConfigObject(TypedDict):
    object: str
    zone: str

class CustomConfig(TypedDict):
    teleport: NotRequired[bool]
    objects: NotRequired[list[CustomConfigObject]]
    type: str
    ponies: NotRequired[list[str]]
    show_horn: NotRequired[bool]
    animations: NotRequired[list[str]]

class CounterRequirement(TypedDict):
    Counter: str
    Value: int

class Particle(TypedDict):
    Y: int
    X: int
    Scale: float
    File: str

class PonyTask(TypedDict):
    RewardCoins: int
    Pony: str
    IdleDuration: NotRequired[int]
    PonyRequirement: NotRequired[str]
    RewardConsumableAmount: int
    LocalizedName: str
    RewardConsumable: str
    SkipCost: int
    RewardXp: int
    TrackingID: int
    Animations: NotRequired[list[str]]
    Duration: int
    HideTask: NotRequired[bool]
    RewardGems: int
    ID: str
    Icon: str
    GoToHouse: NotRequired[str]
    ObjectXOffset: NotRequired[int]
    AdditionalObject: NotRequired[str]
    ObjectYOffset: NotRequired[int]
    ObjectZOffset: NotRequired[int]
    ObjectAnimation: NotRequired[str]
    Particle: NotRequired[Particle]
    CounterRequirements: NotRequired[list[CounterRequirement]]
    SyncAnimation: NotRequired[bool]
    CustomConfig: NotRequired[CustomConfig]
    QuestRequirements: NotRequired[list[str]]
    StartCinematic: NotRequired[str]
    FinishCinematic: NotRequired[str]

class PonyTasksType(TypedDict):
    PonyTasks: list[PonyTask]
