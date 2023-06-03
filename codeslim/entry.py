import ast
import os
from abc import ABCMeta, abstractmethod
from ast import ClassDef
from typing import Sequence, Union

# Need to be refactored


def parse_file(filename: str):
    ext = os.path.splitext(filename)
    if ext != ".py":
        pass
    with open(filename, "r") as f:
        source_code = f.read()
    return ast.parse(source_code)


class Entry(metaclass=ABCMeta):
    @classmethod
    def build(cls, *args):
        return cls(*args)

    @abstractmethod
    def convert_to_ast(self, entries):
        pass

    @abstractmethod
    def get_cache(self):
        pass

    def __iter__(self):
        for file, ast in zip(self.entries, self.asts):
            yield file, ast


class FileEntry(Entry):
    def __init__(self, entry_files: Union[str, Sequence[str]]) -> None:
        entries = [entry_files] if isinstance(entry_files, str) else entry_files
        self.entries = [os.path.abspath(i) for i in entries]
        self.asts = self.convert_to_ast(self.entries)

    def convert_to_ast(self, entries):
        return [parse_file(f) for f in entries]

    def get_cache(self):
        return self.entries


# It seems that Entry can not collaborate with parser well.
class StringEntry(Entry):
    pass


# TODO(Asthestarsfall): support for Function/ClassEntry
class SegmentEntry(Entry):
    pass


class ClassEntry(SegmentEntry):
    def __init__(self, class_nodes: ClassDef):
        self.entries = class_nodes
        self.ast = self.convert_to_ast(class_nodes)

    def convert_to_ast(self, entries):
        pass
