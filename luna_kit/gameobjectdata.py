import contextlib
import io
import os
from itertools import zip_longest

from lxml import etree

from .file_utils import is_binary_file, is_text_file
from .utils import strToInt


class GameObjectData():
    categories: dict
    
    def __init__(self, file) -> None:
        self.categories = {}
        
        tree = etree.parse(file)
        
        root = tree.getroot()
        
        for element in root:
            if element.tag == 'Category':
                category = []
                self.categories[element.get('ID')] = category

                for child in element:
                    if child.tag == 'GameObject':
                        category.append(GameObject(child))
                
                
        

class GameObject():
    def __init__(self, xml: etree._Element) -> None:
        for element in xml:
            if element.tag == 'Name':
                self.name = element.get('Unlocal')
            elif element.tag == 'Description':
                self.description = element.get('Unlocal')
            elif element.tag == 'Minigames':
                self.minigames = {
                    'EXP_Rank': element.get('EXP_Rank'),
                    'CanPlayMineCart': element.get('CanPlayMineCart'),
                    'NoWings': element.get('NoWings'),
                    'PlayActionSkipAgainCost': element.get('PlayActionSkipAgainCost'),
                    'LockedGames': element.get('LockedGames'),
                    'TimeBetweenPlayActions': element.get('TimeBetweenPlayActions'),
                }
            elif element.tag == 'Icon':
                self.icon = element.get('Icon', '') + '.png'
            elif element.tag == 'House':
                self.house = {
                    'Type': element.get('Type'),
                    'HomeMapZone': element.get('HomeMapZone'),
                }
            elif element.tag == 'Shop':
                self.shop = {
                    'Icon': element.get('Icon'),
                    'OffsetX': element.get('OffsetX'),
                    'OffsetY': element.get('OffsetY'),
                    'Scale': element.get('Scale'),
                    'CanBeAssign': element.get('CanBeAssign'),
                }
            elif element.tag == 'Model':
                self.model = {
                    'EffectColour_B': element.get('EffectColour_B'),
                    'Collision_Y': element.get('Collision_Y'),
                    'Base_Growing': element.get('Base_Growing'),
                    'ShadowBone': element.get('ShadowBone'),
                    'EffectColour_R': element.get('EffectColour_R'),
                    'BaseFG': element.get('BaseFG'),
                    'ShadowScale': element.get('ShadowScale'),
                    'PivotY': element.get('PivotY'),
                    'Collision_W': element.get('Collision_W'),
                    'BaseBG': element.get('BaseBG'),
                    'FixedZOffset': element.get('FixedZOffset'),
                    'AutoScale': element.get('AutoScale'),
                    'ScrollSpeed': element.get('ScrollSpeed'),
                    'ZOffset': element.get('ZOffset'),
                    'VineID': element.get('VineID'),
                    'EffectColour_G': element.get('EffectColour_G'),
                    'Alpha': element.get('Alpha'),
                    'Base_Ready': element.get('Base_Ready'),
                    'PivotX': element.get('PivotX'),
                    'Scale': element.get('Scale'),
                    'Scrolling': element.get('Scrolling'),
                    'DefaultIsLeft': element.get('DefaultIsLeft'),
                    'Rotation': element.get('Rotation'),
                    'MediumLOD': element.get('MediumLOD'),
                    'GridSize': element.get('GridSize'),
                    'Model': element.get('Model'),
                    'Foreground': element.get('Foreground'),
                    'RootBone': element.get('RootBone'),
                    'Base': element.get('Base'),
                    'Collision_X': element.get('Collision_X'),
                    'LowLOD': element.get('LowLOD'),
                    'HighLOD': element.get('HighLOD'),
                    'Camera': element.get('Camera'),
                    'Collision_Z': element.get('Collision_Z'),
                }
            elif element.tag == 'AI':
                self.ai = {
                    'Special_AI': element.get('Special_AI'),
                    'Max_Level': element.get('Max_Level'),
                }
            elif element.tag == 'Tracking':
                self.tracking = {
                    'TrackingID': element.get('TrackingID'),
                    'ArrivalPush': element.get('ArrivalPush'),
                }
            elif element.tag == 'OnArrive':
                self.arrival_xp = strToInt(element.get('EarnXP', 0))
            elif element.tag == 'StarRewards':
                self.star_rewards = []
                ids = element.find('ID') if element.find('ID') is not None else etree.Element('ID')
                amounts = element.find('Amount') if element.find('Amount') is not None else etree.Element('Amount')

                for id, amount in zip_longest(
                    ids, amounts,
                    fillvalue = etree.Element('Item', value = ''),
                ):
                    reward = {
                        'reward': id.get('Value'),
                        'amount': strToInt(amount.get('Value')),
                    }
                    
                    self.star_rewards.append(reward)
                
