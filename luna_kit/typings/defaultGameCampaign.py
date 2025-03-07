from typing import TypedDict, Literal, Optional, Required, Mapping

__all__ = ['DefaultGameCampaignType']

# General

class Reward(TypedDict):
    Item: str
    Amount: int

class ConversionMilestone(TypedDict):
    Currency: int
    Gems: int

class Price(TypedDict):
    currency: str
    cost: int

# Siege info
class ChangelingUPG(TypedDict):
    ID: str
    Power: int

class SiegeUpgrade(TypedDict):
    Bonus: int
    Cost: int
    NewCostume: bool

class SiegeBoss(TypedDict):
    ID: str
    BossHP: int
    TimeMinutes: float
    MinionsBeforeBoss: int
    MinionHP: int
    MinionCurrencyReward: int
    CurrencyCappings: list[int]
    ClickerBonus: dict[Literal[
        'CurrencyPerClick',
        'MaxClicksPerActivation',
        'ActivationDurationMin',
        'ActivationDurationMax',
        'ActivationCooldownMin',
        'ActivationCooldownMax',
        'CurrencyCapping',
        'CurrencyCooldownMinutes',
    ], int]
    

class Siege(TypedDict):
    TLS_ID: str
    HelperPowers: list[int]
    ChangelingUPG: list[ChangelingUPG]
    MainPonyBasePower: int
    HelmUpgrades: list[SiegeUpgrade]
    ArmorUpgrades: list[SiegeUpgrade]
    ConversionMilestones: list[ConversionMilestone]
    Bosses: list[SiegeBoss]


# Blitz data
class HitCurrencyReward(TypedDict):
    Min: int
    Max: int
    Chance: float

class BlitzReward(TypedDict):
    RemainingHP: int
    AltReward: Reward
    Reward: Reward

class BlitzUpgrade(TypedDict):
    Cost: int
    Kind: Literal[0,1,2]
    Amount: int

class Blitz(TypedDict):
    TLS_ID: str
    BossHP: int
    BasePower: int
    BaseEnergy: int
    BaseCooldown: int
    HitCurrencyRewards: list[HitCurrencyReward]
    Rewards: list[BlitzReward]
    Upgrades: list[BlitzUpgrade]
    Helpers: list[dict[Literal['PowerBonus'], int]]
    ConversionMilestones: list[ConversionMilestone]
    BossHP2nd: int
    Helpers2nd: list[dict[Literal['PowerBonus'], int]]
    HelpersLB: list[dict[Literal['PowerBonus'], int]]

# Arena
class Arena(TypedDict):
    Parameters: list[Siege]
    Bosses: list[SiegeBoss]
    ClickerBosses: list

# PiggyBank

class PiggyBankReward(TypedDict):
    cashBackPercent: int
    levelUp: Mapping[str, int]

class PiggyBank(TypedDict):
    tiers: dict[str, dict[Literal['startValue', 'maxValue'], int]]
    firstStartValue: int
    requiredLvl: int
    maxValue: int
    burstAmount: int
    reward: PiggyBankReward
    startValue: int

# mapzones

class MapzoneSpecialUnlock(TypedDict):
    IsEnabled: Optional[bool]
    CurrencyCount: int
    CurrencyName: str
    AltCurrencyCount: int

class SpawnEnemyLimits(TypedDict):
    PlunderseedVineMedium: dict[Literal['Min', 'Max'], int]
    PlunderseedVineSmall: dict[Literal['Min', 'Max'], int]
    Changeling: dict[Literal['Min', 'Max'], int]
    PlunderseedVineLarge: dict[Literal['Min', 'Max'], int]
    Parasprite: dict[Literal['Min', 'Max'], int]


class Mapzone(TypedDict):
    SpecialUnlock: Optional[MapzoneSpecialUnlock]
    expand_spawn_enemy_limits: SpawnEnemyLimits
    trash_spawn_enemy: SpawnEnemyLimits

# Changeling Kingdom boss

class CK_Prize(TypedDict):
    MainAmount: int
    Alt: str
    Main: str
    AltAmout: int

class CK_Booster(TypedDict):
    Pony: str
    Value: int

class CK_Phase(TypedDict):
    TimeLimitedPrize: CK_Prize
    GuaranteedPrize: CK_Prize
    PointsCooldownSeconds: int
    GoalPoints: int
    Boosters: list[CK_Booster]
    DurationSeconds: int
    SkipPrice: int
    ChangelingsPrize: int

class CK_Boss(TypedDict):
    GemsTransformTable: list[int]
    InitialGoodChangelings: int
    GemsTransformPrice: list[int]
    ActivePhases: list[CK_Phase]

# Minigames

## Clear the Skies
class CTS_Coin(TypedDict):
    score: int
    type: str
    weight: int

class CTS_Level(TypedDict):
    booster_time: int
    booster_spawn_max: int
    booster_start_delay: int
    segments: list[str]
    coins: list[CTS_Coin]
    booster_spawn_min: int
    fever_time: int
    booster_chance: float
    pony_score_multiplier: float
    duration: int
    type: Literal['easy', 'medium', 'hard']
    
## Balloon Pop

class BalloonPop_Item(TypedDict):
    type_name: str
    min: int
    max: int
    weight: float
    featured: Optional[Literal['FALSE', 'TRUE']]
    tag: Optional[Literal['rare', 'legendary', '']]

class BalloonPop_Lottery(TypedDict):
    currency_1: str
    price_1: int
    currency_2: str
    price_2: int
    currency_3: str
    price_3: int
    altCurrency: str
    altCost: int
    
    loot_table: list[BalloonPop_Item]
    alt_loot_table: list[BalloonPop_Item]

    play_session_time: int
    enabled: bool
    chest_icon: str
    tracking_id: int
    tier_name: str
    lotto_bg: str
    action_phase_balloon_type: Literal['round']

class BalloonPop(TypedDict):
    TokenAmountForLottoAdsReward: int
    TokenAmountForLottoCrystalAdsReward: int
    lottogamepop: dict[Literal['loot_table'], list[BalloonPop_Item]]
    costs: dict[Literal['poplottery'], Price]
    lottos_list: dict[str, BalloonPop_Lottery]

## Minecart

class Minecart_Prize(TypedDict):
    scale: float
    string: str
    min: int
    max: int
    image: str
    object: str
    offsetx: float
    offsety: float
    id: int
    objecttype: int

class Minecart_Rewards(TypedDict):
    loot_table: list[Minecart_Prize]
    distance_table: list[int]
    infinite_loot_table: list[Minecart_Prize]

class Minecart(TypedDict):
    revive_cost_table: list[int]
    minecart_play_cost_gem: int
    cart_selection: dict[Literal[
            'cart0',
            'cart1',
            'cart2',
        ], dict[Literal[
            'cart_type',
            'currency',
            'cost',
            'multiplier',
        ], int]
    ]
    prize_distance_factor: float
    Level: dict[Literal[
        'revivetimer',
        'revive_powerup_spawn_reduction',
        'coinvalue',
        'powerupspawn',
        'nodangerperiod',
    ], int]
    rewards_9: Minecart_Rewards
    gems_cap_table: list[int]
    minecart_play_cost_wheel: int
    default_gems_cap: int
    minecart_wheel_cap: int
    reward_minecartwheel_time_interval: int
    reset_gem_cap: bool

## Find a Pair
class FAP_MilestonItem(TypedDict):
    itemID: str
    amount: int
    score: int
    altID: str
    altAmount: int

class FindAPair(TypedDict):
    enter_cost: int
    lvlBasePrice: dict[Literal['baseCoins', 'baseGems', 'maxCoins'], int]
    retry_cost: list[int]
    refill_time: int
    curCap: int
    resetInf: int
    time_session: int
    tiers_list: dict[Literal[
        'Tier0',
        'Tier1',
        'Tier2',
    ], int]
    MilestonItems: list[FAP_MilestonItem]
    MilestonInfItems: list[FAP_MilestonItem]

## Daily Goals
class DailyGoals_Item(TypedDict):
    item_id: str
    cost: int

class DailyGoals(TypedDict):
    goal_refresh_cost: int
    goals_refresh_cost_1: int
    goals_refresh_cost_2: int
    goals_refresh_cost_3: int
    itemshop: list[DailyGoals_Item]

class CalendarPrize(TypedDict):
    day: Optional[int]
    itemID: str
    amount: int
    altID: str
    altAmount: int

class NewcomerCalendar(TypedDict):
    background_img: str
    active_days: int
    main_rewards: list[CalendarPrize]
    days: list[CalendarPrize]


class MiniGames(TypedDict):
    special_clear_skies: list[CTS_Level]
    balloonpop: BalloonPop
    minecart: Minecart
    findpair: FindAPair
    dailygoals: DailyGoals
    newcamer_calendar: NewcomerCalendar
    ponybookminigame: dict[Literal['swap_cost_gem'], int]
    

# DefaultGameCampaign
class DefaultGameCampaignType(TypedDict):
    AskIDFATracking: dict[Literal['Enabled'], bool]
    CrashlyticsParams: dict[Literal['Enabled'], bool]
    Arena: Arena
    deprecated_game_version: dict[Literal['versions'], list[str]]
    PiggyBank: PiggyBank
    mapzones: dict[Literal[
        'mapzone_0',
        'mapzone_1',
        'mapzone_2',
        'mapzone_3',
        'mapzone_4',
        'mapzone_6',
    ], Mapzone]
    CK_Boss: CK_Boss
    mini_games: MiniGames
    enable_auto_refresh: int
    global_defines: dict
    CollectionsData: dict
    player: dict
    init: dict
    VIP: dict
    Redeem: dict
    item_fuse: dict
    group_quests: dict
    ReferralRewards: dict
    game_object_data: dict
    events: dict
    PonyTaskData: dict
    SpinningWheel: dict
    LotteryWheel: dict
    BluePrints: dict
    
