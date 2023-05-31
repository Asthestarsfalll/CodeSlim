from typing import Dict, List, Optional, TypeVar, Union

from .codegen import FileLevelCodeGenerator, SegmentCodeGenerator
from .entry import FileEntry, StringEntry
from .parse import Parser

__all__ = ['AutoSlim']


T = TypeVar('T')
LIST_OR_ITEM = Union[T, List[T]]


# Maybe we can store some generate info here
class AutoSlim:
    FileLevel = FileLevelCodeGenerator
    SegmentLevel = SegmentCodeGenerator
    File = FileEntry
    String = StringEntry
    def __init__(self, entries: LIST_OR_ITEM[str], target_dir: str, refactor_info: Optional[Dict[str, str]]=None):
        self.entries = entries
        self.target_dir = target_dir
        self._mode = AutoSlim.FileLevel
        self._refactor_info = refactor_info or {}
        # Maybe we can name this O1 like optimization of gcc hh
        self._merge_class = False
        self._entry_type = FileEntry

    def mode(self, mode):
        self._mode = mode
        return self

    def merge_class(self):
        self._merge_class = True
        return self

    def entry_type(self, type):
        self._entry_type = type
        return self

    def generate(self):
        entry = self._entry_type(self.entries)
        parser = Parser(entry)
        codegen = self._mode(self.target_dir, parser)
        codegen.generate()
        return self
