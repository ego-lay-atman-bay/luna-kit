from collections import UserDict
from dataclasses import dataclass
import dataclasses
import os

from lxml import etree

from .file_utils import PathOrBinaryFile
from .utils import strToBool, strToFloat, strToInt
from .xml import parse_xml

@dataclass
class Count:
    type: str
    category: str
    sub_object: str
    value: int

@dataclass
class Item:
    id: str = ''
    value: int = 0
    alt_currency: int = 0
    alt_value: int = 0
    consumable_id: str = ''
    consumable_count: int = 0

@dataclass
class Task:
    name: str = ''
    description: str = ''
    icon: str = ''
    skippable: bool = False
    is_OFT: bool = False
    skip_cost: int = 0
    skip_time_exp: int = 0
    tracking_id: int = 0
    type_tracking_id: int = 0
    has_go: bool = False
    no_skip_by_ads: bool = False

    counts: list[Count] = dataclasses.field(default_factory = list)

@dataclass
class Event:
    type: str = ''
    value: str = ''

@dataclass
class QuestInfo:
    title: str = ''
    skippable: bool = False
    auto_start: bool = False
    global_quest: bool = False
    invisible_quest: bool = False
    skip_for_COPPA: bool = False
    skip_for_OFT: bool = False
    add_to_complete_after_start: bool = False
    is_OFT_only: bool = False
    description: str = ''
    icon: str = ''
    giver_icon: str = ''
    giver_image: str = ''
    complete_description: str = ''
    tracking_id: int = 0
    mapzone: int = -1

@dataclass
class QuestRequirements:
    any_quest: bool = False
    quests_completed: list[str] = dataclasses.field(default_factory = list)
    global_counts: list[Count] = dataclasses.field(default_factory = list)
    start_zones: list[int] = dataclasses.field(default_factory = list)

@dataclass
class QuestRewards:
    bits: int = 0
    gems: int = 0
    social_currency: int = 0
    xp: int = 0
    item: Item = dataclasses.field(default_factory = Item)
    item2: Item = dataclasses.field(default_factory = Item)

@dataclass
class QuestEvents:
    start: list[Event] = dataclasses.field(default_factory = list)
    end: list[Event] = dataclasses.field(default_factory = list)

@dataclass
class Quest:
    name: str = ''
    category: str = ''
    info: QuestInfo = dataclasses.field(default_factory = QuestInfo)
    requirements: QuestRequirements = dataclasses.field(default_factory = QuestRequirements)
    task_list: list[Task] = dataclasses.field(default_factory = list)
    rewards: QuestRewards = dataclasses.field(default_factory = QuestRewards)
    events: QuestEvents = dataclasses.field(default_factory = QuestEvents)

    @classmethod
    def from_xml(cls, element: etree._Element):
        info_el = element.find('Info')
        if info_el is not None:
            info = QuestInfo(
                title = info_el.get('Title', ''),
                skippable = strToBool(info_el.get('Skippable', '')),
                auto_start = strToBool(info_el.get('AutoStart', '')),
                global_quest = strToBool(info_el.get('GlobalQuest', '')),
                invisible_quest = strToBool(info_el.get('InvisibleQuest', '')),
                skip_for_COPPA = strToBool(info_el.get('SkipForCOPPA', '')),
                skip_for_OFT = strToBool(info_el.get('SkipForOFT', '')),
                add_to_complete_after_start = strToBool(info_el.get('AddToCompleteAfterStart', '')),
                is_OFT_only = strToBool(info_el.get('IsOFTOnly', '')),
                description = info_el.get('Description', ''),
                icon = info_el.get('Icon', ''),
                giver_icon = info_el.get('GiverIcon', ''),
                giver_image = info_el.get('GiverImage', ''),
                complete_description = info_el.get('CompleteDescription', ''),
                tracking_id = strToInt(info_el.get('TrackingID', '')),
                mapzone = strToInt(info_el.get('MapZone', '')),
            )
        else:
            info = QuestInfo()
        
        requirements_el = element.find('Requirements')
        if requirements_el is not None:
            quests_completed: list[str] = []
            quests_completed_el = requirements_el.find('QuestsCompleted')
            if quests_completed_el is not None:
                for quest in quests_completed_el:
                    quests_completed.append(quest.get('Name', ''))
            
            global_counts: list[Count] = []
            global_counts_el = requirements_el.find('GlobalCounts')
            if global_counts_el is not None:
                for count in global_counts_el:
                    global_counts.append(Count(
                        type = count.tag,
                        category = count.get('Category', ''),
                        sub_object = count.get('SubObject', ''),
                        value = strToInt(count.get('Value', '0')),
                    ))
            requirements = QuestRequirements(
                any_quest = strToBool(element.get('AnyQuest', '0')),
                quests_completed = quests_completed,
                global_counts = global_counts,
            )
        else:
            requirements = QuestRequirements()
        
        task_list: list[Task] = []
        tasklist_el = element.find('TaskList')

        if tasklist_el is not None:
            for task in tasklist_el:
                global_counts: list[Count] = []
                for global_count in task:
                    global_counts.append(Count(
                        type = global_count.tag,
                        category = global_count.get('Category', ''),
                        sub_object = global_count.get('SubObject', ''),
                        value = strToInt(global_count.get('Value', '0')),
                    ))
        
                task_list.append(Task(
                    name = task.get('Name', ''),
                    description = task.get('Description', ''),
                    icon = task.get('Icon', ''),
                    skippable = strToBool(task.get('Skippable', '')),
                    is_OFT = strToBool(task.get('IsOFT', '')),
                    skip_cost = strToInt(task.get('SkipCost', '')),
                    skip_time_exp = strToInt(task.get('SkipTimeExp', '')),
                    tracking_id = strToInt(task.get('TrackingID', '')),
                    type_tracking_id = strToInt(task.get('TypeTrackingID', '')),
                    has_go = strToBool(task.get('HasGo', '')),
                    no_skip_by_ads = strToBool(task.get('NoSkipByAds', '')),
                    
                    counts = global_counts,
                ))

        rewards_el = element.find('Rewards')
        
        rewards = QuestRewards()
        if rewards_el is not None:
            for reward in rewards_el:
                match reward.tag:
                    case 'SoftCurrency':
                        rewards.bits = strToInt(reward.get('Value', '0'))
                    case 'HardCurrency':
                        rewards.gems = strToInt(reward.get('Value', '0'))
                    case 'SocialCurrency':
                        rewards.social_currency = strToInt(reward.get('Value', '0'))
                    case 'Exp':
                        rewards.xp = strToInt(reward.get('Value', '0'))
                    case 'Item':
                        rewards.item = Item(
                            id = reward.get('ID', ''),
                            value = strToInt(reward.get('Value', '0')),
                            alt_currency = strToInt(reward.get('AltCurrency', '0')),
                            alt_value = strToInt(reward.get('AltValue', '0')),
                            consumable_id = reward.get('ConsumableId', ''),
                            consumable_count = strToInt(reward.get('ConsumableCount', '0')),
                        )
                    case 'Item2':
                        rewards.item2 = Item(
                            id = reward.get('ID', ''),
                            value = strToInt(reward.get('Value', '0')),
                            alt_currency = strToInt(reward.get('AltCurrency', '0')),
                            alt_value = strToInt(reward.get('AltValue', '0')),
                            consumable_id = reward.get('ConsumableId', ''),
                            consumable_count = strToInt(reward.get('ConsumableCount', '0')),
                        )

        events_el = element.find('Events')
        if events_el is not None:
            start_events = []
            start_el = events_el.find('OnQuestStart')
            if start_el is not None:
                for event in start_el:
                    start_events.append(Event(
                        type = event.get('Type', ''),
                        value = event.get('Value', ''),
                    ))
            
            end_events = []
            end_el = rewards_el.find('OnQuestComplete')
            if end_el is not None:
                for event in end_el:
                    end_events.append(Event(
                        type = event.get('Type', ''),
                        value = event.get('Value', ''),
                    ))

            events = QuestEvents(
                start = start_events,
                end = end_events,
            )
        else:
            events = QuestEvents()

        return cls(
            name = element.get('Name', ''),
            category = element.get('Category', ''),
            info = info,
            requirements = requirements,
            task_list = task_list,
            rewards = rewards,
            events = events,
        )

class QuestTable(UserDict):
    data: dict[str, Quest]

    def __init__(self, filename: str) -> None:
        super().__init__()

        self.categories: dict[str, dict[str, Quest]] = {}
        
        questtable_xml = parse_xml(filename)[0]

        for quest_xml in questtable_xml:
            quest = Quest.from_xml(quest_xml)
            self.quests[quest.name] = quest
            self.categories.setdefault(quest.category, {})[quest.name] = quest

    @property
    def quests(self):
        return self.data
    @quests.setter
    def quests(self, data: dict):
        self.data = data
