import os
from abc import ABCMeta, abstractmethod
from typing import List, Union

"""
EndPoint will grant us the ability to trace or not trace some certain python library files instead of only local files.
By default, we only trace local files which are determined by the directory scope of the Entry.

Need to be refactored.
"""


class EndPoint(metaclass=ABCMeta):
    __target__ = ["file_path"]

    @abstractmethod
    # It seems that we only need to check file path(s)?
    def __call__(self, file_path):
        pass


# Maybe BuiltinEndPoint should be implemented in base EndPoint class?
class BuiltinEndPoint(EndPoint):
    def __init__(self):
        self.builtins = list(globals()["__builtins__"].keys())

    def __call__(self, module_name):
        return module_name in self.builtins


class LocalEndPoint(EndPoint):
    def __init__(self, local_dir):
        self.local_dir = os.path.dirname(os.path.abspath(local_dir))

    def __call__(self, file_path):
        file_abs_path = os.path.abspath(file_path)
        return os.path.commonprefix([file_abs_path, self.local_dir]) != self.local_dir


class ExceptEndPoint(LocalEndPoint):
    __target__ = ["file_path", "module_name"]

    def __init__(self, local_dir, excepts):
        if isinstance(excepts, str):
            excepts = [excepts]
        self.excepts = excepts
        super().__init__(local_dir)

    def __call__(self, file_path, module_name):
        if module_name in self.excepts:
            return False
        else:
            return super().__call__(file_path)


class EndPointManager:
    INCOMPATIBLE = [(LocalEndPoint, ExceptEndPoint)]

    def __init__(self, endpoints: Union[EndPoint, List[EndPoint]]):
        if not isinstance(endpoints, list):
            endpoints = [endpoints]
        endpoint_types = [type(i) for i in endpoints]
        for pair in EndPointManager.INCOMPATIBLE:
            if pair[0] in endpoint_types and pair[1] in endpoint_types:
                raise ValueError(f"Imcompatible endpoints: {pair}")
        self.endpoints = endpoints

    @classmethod
    def add_imcompatible_pair(cls, pair):
        assert len(pair) == 2
        cls.INCOMPATIBLE.append(pair)

    def check(self, local):
        for endpoint in self.endpoints:
            kwargs = {k: local[k] for k in endpoint.__target__}
            if endpoint(**kwargs):
                return True
        return False
