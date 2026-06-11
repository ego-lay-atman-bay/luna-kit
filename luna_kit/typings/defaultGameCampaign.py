from typing import TypedDict, Literal, Optional, NotRequired, Required, Mapping

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
    IsEnabled: NotRequired[bool]
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
    SpecialUnlock: NotRequired[MapzoneSpecialUnlock]
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

# group quests

class GroupQuests_ChestLootItem(TypedDict):
    item: str
    max: int
    weight: int
    min: int

class GroupQuests_SPReward(TypedDict):
    item: str
    bad_chance: float
    max: int
    good_chance: float
    min: int

class GroupQuests_ConsolationPrize(TypedDict):
    item: str
    max: int
    min: int

class GroupQuests_Chest(TypedDict):
    Items: list[GroupQuests_ChestLootItem]
    Amount: int
    Requirement: int
    Icon: str

class GroupQuests_Slot(TypedDict):
    sp_chance: float
    sp_rewards: list[GroupQuests_SPReward]
    difficulty: float
    consolation_prize: GroupQuests_ConsolationPrize
    enabled: bool
    skip_gems_per_hour: int
    multiplier_step: float
    multiplier_requirements: list[int]
    loot: list[GroupQuests_Chest]
    sp_delay_minutes: int

class GroupQuests_SeasonalSlot(GroupQuests_Slot):
    seasonal: str
    season_start_time: int

class GroupQuests(TypedDict):
    tokens_per_chest: int
    iv_skip_minutes: list[int]
    token_id_per_chest: Literal['Token_GQ_bonus']
    tutorial_slot: GroupQuests_Slot
    slots: list[GroupQuests_Slot]
    random_pros: list[str]
    seasonal_slots: list[GroupQuests_SeasonalSlot]
    alt_prize: list[GroupQuests_ChestLootItem]

# GlobalDefines

class GlobalDefines_SocialTreasureDrop(TypedDict):
    amount: int
    id: str

class GlobalDefines_Derpy(TypedDict):
    gem_chance: float
    minecart_wheel_chance: float
    spawn_time: int
    find_coin_reward: int
    min_exist_time: int
    find_time: int
    respawn_timer: int

class GlobalDefines_UpdateGift(TypedDict):
    amount: int
    id: str

class GlobalDefines_VacuumCleaner(TypedDict):
    is_enabled: bool
    one_hour_gem_price: int
    required_lvl: int
    override: dict[Literal[
            'canterlot',
            'saa',
            'ponyville',
            'ce',
            'klugetown',
        ], dict[Literal[
            'attract_shop_count',
            'next_use_delay',
        ], int]]
    attract_shop_count: int
    next_use_delay: int

class GlobalDefines_MysteryPony(TypedDict):
    gem_chance: float
    spawn_time: int
    find_coin_reward: int
    min_exist_time: int
    find_leaderboard_currency: int
    find_time: int
    respawn_timer: int

class GlobalDefines_ParaspritesGenerator(TypedDict):
    min_shards: dict[Literal[
        'Laughter_min_shard',
        'Honesty_min_shard',
        'Kindness_min_shard',
        'Magic_min_shard',
        'Loyalty_min_shard',
        'Generosity_min_shard',
    ], int]
    amx_shards: dict[Literal[
        'Laughter_max_group',
        'Honesty_max_group',
        'Kindness_max_group',
        'Magic_max_group',
        'Loyalty_max_group',
        'Generosity_max_group',
    ], int]

class GlobalDefines_EventConversion(TypedDict):
    Gems: int
    Currency: int

class GlobalDefines_TokenDrop(TypedDict):
    shop_chance: int
    type: str

class GlobalDefines_IAPSort(TypedDict):
    promo_first: bool
    order: str

class GlobalDefines_SubPointcut(TypedDict):
    pointcutId: str
    limit: int

class GlobalDefines_SubWelcomeGift(TypedDict):
    Quantity: int
    GiftId: str

class GlobalDefines_SubscribeData(TypedDict):
    available: bool
    firstSubscribeAwardGems: int
    WheelsSubscriptionCap: int
    AltPointcuts: list[GlobalDefines_SubPointcut]
    MCRevivesPerRide: int
    vacuumTimer: int
    subscriptionDuration: int
    ShopBonus: int
    PonyTaskBoost: float
    SubscriptionPlusWelcomeGifts: list[GlobalDefines_SubWelcomeGift]


class FortuneShopItemType(TypedDict):
    id: str
    amount: NotRequired[int]
    price_list: list[int]
    sub_price_list: NotRequired[list[int]]

class FortuneShopDataType(TypedDict):
    max_items_in_shop: int
    refresh_cost: int
    refresh_period_days: int
    item_discount_chances: NotRequired[dict[Literal[
        'discount',
        'regular',
        'super',
    ], float]]
    item_price_chances: dict[Literal[
        'regular',
        'discount',
        'super',
        'ultra',
    ], float]
    item_rarity_chances: dict[Literal[
        'common',
        'uncommon',
        'rare',
    ], float]
    required_level: int
    item_lists: dict[Literal[
        'common',
        'uncommon',
        'rare',
    ], list[FortuneShopItemType]]


class GlobalDefines(TypedDict):
    edit_force_theme_level: int
    energy_restore_cost: int
    change_sectors_image_spinning_wheel_time: int
    change_name_cost: int
    forced_oft: str
    increment_spinning_wheel_cost_time: int
    mini_games: dict[Literal[
        'pop_level_requirement',
        'minecart_max_score',
        'minecart_level_requirement',
        'eg_level_requirement'
    ], int]
    social_treasure_drop: NotRequired[list[GlobalDefines_SocialTreasureDrop]]
    rate_our_game_enabled: bool
    zh_max_ingredients: int
    player_max_level: int
    tickets_cap: int
    current_subseason: int
    shop_minecart_wheel_drop_chance: float
    derpy: GlobalDefines_Derpy
    zecora_totem_ads: dict[Literal['skip_time'], int]
    ads_tls_currency_amounts: dict[Literal['arena_amounts', 'blitz_amounts'], list[int]]
    ads_currency_amount: dict[Literal['bits_amount', 'gems_amount'], int]
    oft_exclusion_country_name: str
    coppa_age: int
    contacts: dict[str, str]
    coppa_enabled_countries: str
    update_gift: list[GlobalDefines_UpdateGift]
    chest_minecart_wheel_drop_chance: float
    oft_age: int
    gdpr_enabled_countries: str
    offline_shop: dict[Literal['off_string_secondary_id', 'off_string_primary_id'], str]
    spinning_wheel_cooldown_adv_times: int
    speedup_data: dict[Literal[
            'subscribe',
            'regular',
            'subsribe_plus',
        ], dict[Literal[
            'fuelcapacity',
            'restock',
            'deltaspeed',
        ], int]]
    forced_coppa: str
    ads_reward_pony: dict
    mega_event_required_level: int
    disclaimerCountries: str
    coppa_exclusion_country_name: str
    tickets_restore_cost: int
    free_lotto_wait_time: int
    vacuum_cleaner: GlobalDefines_VacuumCleaner
    minimal_level_for_ponyversary: int
    season: str
    tq_mystery_pony: GlobalDefines_MysteryPony
    ads_params: dict[Literal['iap_building_freecash'], int]
    parasprites_generator: GlobalDefines_ParaspritesGenerator
    decore_minecart_wheel_drop_chance: float
    shards_spending_data: dict[Literal['spend_prices'], list[int]]
    didomi: dict[str, str]
    iv_farm_skip_min: list[int]
    energy_restore_time: int
    extra_promo_OFT_enabled: bool
    blitz_default_convertation_rate: list[GlobalDefines_EventConversion]
    token_drop: GlobalDefines_TokenDrop
    mega_event_default_convertation_rate: list[GlobalDefines_EventConversion]
    current_season: int
    fortune_shop_data: FortuneShopDataType
    personal_shop_data: FortuneShopDataType
    oft_enabled_countries: str
    iap_sort: GlobalDefines_IAPSort
    news_enable_OFT_COPPA: int
    atv_news_forum_enabled: int
    free_spinning_wheel_wait_time: int
    tickets_restore_time: int
    iv_animal_skip_min: list[int]
    quest_ads_data: dict[Literal[
        'minLvLForXPMultiply',
        'gems_limit',
        'rewardMultiplier',
        'bits_limit',
    ], int]
    tickets_restore_cost_new: None
    SubscribeData: GlobalDefines_SubscribeData
    energy_cap: int


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
    global_defines: GlobalDefines
    CollectionsData: dict
    player: dict
    init: dict
    VIP: dict
    Redeem: dict
    item_fuse: dict
    group_quests: GroupQuests
    ReferralRewards: dict
    game_object_data: dict
    events: dict
    PonyTaskData: dict
    SpinningWheel: dict
    LotteryWheel: dict
    BluePrints: dict
    
