import os
from typing import overload, Literal

try:
    import charset_normalizer
    from lxml import etree
except ImportError as e:
    e.add_note('xml dependencies not found')
    raise e

from .file_utils import PathOrBinaryFile, PathOrFile, is_file_like, open_binary


@overload
def parse_xml(
    file: PathOrBinaryFile,
) -> etree._Element: ...
@overload
def parse_xml(
    file: PathOrBinaryFile,
    *,
    as_tree: Literal[False],
) -> etree._Element: ...
@overload
def parse_xml(
    file: PathOrBinaryFile,
    *,
    as_tree: Literal[True],
) -> etree._ElementTree: ...
@overload
def parse_xml(
    file: PathOrBinaryFile,
    *,
    with_encoding: Literal[True]
) -> tuple[etree._Element, str]: ...
@overload
def parse_xml(
    file: PathOrBinaryFile,
    *,
    as_tree: Literal[False],
    with_encoding: Literal[True]
) -> tuple[etree._Element, str]: ...
@overload
def parse_xml(
    file: PathOrBinaryFile,
    *,
    as_tree: Literal[True],
    with_encoding: Literal[True]
) -> tuple[etree._ElementTree, str]: ...
def parse_xml(
    file: PathOrBinaryFile,
    *,
    as_tree: bool = False,
    with_encoding: bool = False,
):
    encoding = None
    best = None
    
    with open_binary(file) as file_in:
        data = file_in.read()
    
    encoding = charset_normalizer.from_bytes(data).best().encoding
    
    if encoding is not None:
        encoding = encoding.replace('_', '-')
    
    root = etree.fromstring(
        f'<root>{data.decode(encoding)}</root>',
        parser = etree.XMLParser(
            recover = True,
        )
    )

    roots = []
    for child in root: # body
        # filter <?xml version="1.0"??>
        if child.tag is etree.ProcessingInstruction:
            continue
        # filter comments
        if child.tag is etree.Comment:
            continue
        
        roots.append(child)
    
    result = etree.Element('root')
    result.extend(roots)
    
    if as_tree:
        result = etree.ElementTree(result)
    
    if with_encoding:
        return result, encoding
    else:
        return result

def tostring(
    element: etree._Element,
    *,
    encoding: str | None = None,
    method = "xml",
    xml_declaration: bool | None = None,
    pretty_print: bool = False,
    standalone: bool | None = None,
    doctype: str | None = None
):
    result = b''
    for index, child in enumerate(element):
        if isinstance(child, str):
            continue
        
        xml_string = etree.tostring(
            child,
            xml_declaration = xml_declaration and index == 0,
            method = method,
            encoding = encoding,
            pretty_print = pretty_print,
            with_tail = False,
            standalone = standalone,
            doctype = doctype if index == 0 else None,
        )
        result += xml_string
    
    return result
