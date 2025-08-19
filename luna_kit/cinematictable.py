from collections import UserDict
from dataclasses import field
from dataclasses import dataclass
import os

from lxml import etree

from .console import console
from .file_utils import PathOrBinaryFile
from .utils import strToBool, strToFloat, strToInt
from .xml import parse_xml


@dataclass
class AttributeType:
    name: str
    type: str
    tag: str

    def parse_value(self, value: str):
        match self.type:
            case 'bool':
                return strToBool(value)
            case 'int':
                return strToInt(value)
            case 'float':
                return strToFloat(value)
            case _:
                return value

@dataclass
class ParameterType:
    name: str = ''
    attributes: dict[str, AttributeType] = field(default_factory = dict)


@dataclass
class EventType:
    name: str = ''
    force_wait: bool = False
    tag: str = ''
    parameters: dict[str, ParameterType] = field(default_factory = dict)

@dataclass
class Event:
    name: str = ''
    wait_for_me: bool = False
    group: str = ''
    parameters: dict[str, dict[str | bool | int | float]] = field(default_factory = dict)

@dataclass
class Scene:
    name: str = ''
    is_tutorial: bool = False
    track_tutorial_complete: bool = False
    events: list[Event] = field(default_factory = list)

class CinematicTable(UserDict):
    data: dict[str, Scene]

    def __init__(
        self,
        cinematictable: PathOrBinaryFile,
        cinematicmanager: PathOrBinaryFile | None = None,
    ) -> None:
        """
        Parse `cinematictable.xml` file. If a path to `cinematictable.xml` is provided, it will
        try to grab `cinematicmanager.xml` from the same directory. If `cinematictable` is a
        file-like object, you will have to also explicitly pass in `cinematicmanager`.

        P.S. `cinematicmanager.xml` is basically just a schema for `cinematictable.xml`,
        so it makes my job a lot easier with parsing value types.
        If you want to understand what a value is for, it may be explained in `cinematicmanager.xml`
        (if the devs explained it).

        Args:
            cinematictable (PathOrBinaryFile): `cinematictable.xml`
            cinematicmanager (PathOrBinaryFile | None, optional): `cinematicmanager.xml`. Defaults to None.

        Raises:
            TypeError: `cinematicmanager` must be provided if `cinematictable` is not a path
        """
        super().__init__()

        if isinstance(cinematictable, str) and cinematicmanager is None:
            cinematictable = os.path.abspath(cinematictable)
            cinematicmanager = os.path.join(os.path.dirname(cinematictable), 'cinematicmanager.xml')
        
        if cinematicmanager is None:
            raise TypeError('cinematicmanager must be file')

        cinematictable_xml = parse_xml(cinematictable)[0]
        cinematicmanager_xml = parse_xml(cinematicmanager)[0]

        self._schema: dict[str, EventType] = {}

        self._parse_schema(cinematicmanager_xml)
        self._parse_cinematic_table(cinematictable_xml)

    @property
    def scenes(self):
        return self.data
    @scenes.setter
    def scenes(self, value: dict[str, Scene]):
        self.data = value
    
    def _parse_schema(self, cinematicmanager_xml: etree._Element):
        self._schema.clear()
        
        for event_xml in cinematicmanager_xml:
            if event_xml is etree.Comment:
                continue
            if event_xml.tag != 'EventType':
                console.print(f'[yellow]Unrecognized tag: {event_xml.tag}[/]')
                continue
                
            event_type = EventType(
                name = event_xml.get('Name', ''),
                force_wait = strToBool(event_xml.get('ForceWait', '0')),
            )
            self._schema[event_type.name] = event_type

            for element in event_xml:
                if element is etree.Comment:
                    continue

                if element.tag == 'Tag':
                    event_type.tag = element.text
                
                if element.tag == 'Parameter':
                    parameter = ParameterType(
                        name = element.get('Name', '')
                    )
                    event_type.parameters[parameter.name] = parameter

                    for attribute_xml in element:
                        if attribute_xml is etree.Comment:
                            continue

                        if attribute_xml.tag != 'Attribute':
                            console.print(f'[yellow]unexpected parameter tag: {attribute_xml.tag}[/]')
                            continue
                        
                        attribute = AttributeType(
                            name = attribute_xml.get('Name', ''),
                            type = attribute_xml.get('Type', ''),
                            tag = attribute_xml.get('Tag', ''),
                        )
                        parameter.attributes[attribute.name] = attribute
        
    def _parse_cinematic_table(self, cinematictable_xml: etree._Element):
        self.scenes.clear()
        
        for scene_xml in cinematictable_xml:
            if scene_xml is etree.Comment:
                continue
            if scene_xml.tag != 'Scene':
                console.print(f'[yellow]unexpected scene tag: {scene_xml.tag}[/]')
                continue
            
            scene = Scene(
                name = scene_xml.get('Name', ''),
                is_tutorial = strToBool(scene_xml.get('IsTutorial', '0')),
                track_tutorial_complete = strToBool(scene_xml.get('TrackTutorialComplete', '0')),
            )
            self.scenes[scene.name] = scene

            for event_xml in scene_xml:
                if event_xml is etree.Comment:
                    continue
                if event_xml.tag != 'Event':
                    console.print(f'[yellow]unexpected event tag: {event_xml.tag}[/]')
                    continue

                event = Event(
                    name = event_xml.get('Name', ''),
                    wait_for_me = strToBool(event_xml.get('WaitForMe', '0')),
                )
                scene.events.append(event)

                event_type = self._schema.get(event.name)

                for parameter_xml in event_xml:
                    if parameter_xml is etree.Comment:
                        continue
                    
                    parameter_type = None
                    if event_type is not None:
                        parameter_type = event_type.parameters.get(parameter_xml.tag)
                    else:
                        console.print(f'[yellow]unknown event type: {event.name}')

                    for attribute, value in parameter_xml.attrib.items():
                        if parameter_type is not None:
                            attribute_type = parameter_type.attributes.get(attribute)
                            if attribute_type is not None:
                                value = attribute_type.parse_value(value)
                        
                        event.parameters.setdefault(parameter_xml.tag, {})[attribute] = value
