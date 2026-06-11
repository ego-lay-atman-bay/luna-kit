from typing import TypedDict, Literal


class Narrator(TypedDict):
    BadOutcomeAnimation: str
    RotX: float
    Scale: float
    Pony: str
    RotY: float
    GoodOutcomeAnimation: str
    TapAnimation: str
    TapSound: str
    Y: float
    X: float
    AppearanceAnimation: str
    IdleAnimation: str
    ChoiceAnimation: str

class StoryPoint(TypedDict):
    GoodTrophies: int
    Narrator: Narrator
    Name: str
    PremiumSolution: str
    Image: str
    PremiumOutcome: str
    InteractionTexts: list[str]
    BadTrophies: int
    PremiumPony: str
    TravelTexts: list[str]
    OrdinarySolutions: list[dict[Literal['BadOutcome', 'GoodOutcome', 'Name'], str]]

class GroupQuest(TypedDict):
    IntroNarrator: Narrator
    Narrator: Narrator
    Name: str
    TrophyImage: str
    HubReadyNarrator: Narrator
    Image: str
    BundleImage: str
    HubNotStartedNarrator: Narrator
    Priority: int
    InteractionTexts: list[str]
    HubImage: str
    TrackingID: int
    HubWaitingNarrator: Narrator
    Outro: str
    StoryPoints: list[StoryPoint]
    Description: str

GroupQuestsType = dict[str, GroupQuest]
