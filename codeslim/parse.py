import importlib
import os
from ast import (AST, Attribute, Call, ClassDef, Constant, FunctionDef, Import,
                 ImportFrom, Name, NodeVisitor, Subscript)
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from astpretty import pprint

from .endpoint import EndPointManager, LocalEndPoint
from .entry import Entry
from .utils import cd

__all__ = ["Parser"]


_IMPORT_CACHE = ["torch", "torch.nn"]


@dataclass
class _ImportNode:
    node: Union[ImportFrom, Import]
    import_name: str
    module: str
    alias_name: Optional[str]
    is_target: bool = False

    def _parse_module(self, endpoints):
        module_name = self.module
        # need cache to prevent some heavy imports?
        try:
            imported_module = importlib.import_module(module_name)
            assert imported_module is not None
            if not hasattr(imported_module, "__file__"):
                return None
            file_path = imported_module.__file__
        except ModuleNotFoundError:
            # just a workaround for relative import
            # should find some other methods.
            file_path = os.path.join(
                os.getcwd(), module_name.replace(".", os.sep) + ".py"
            )
            if not os.path.exists(file_path):
                raise RuntimeError(f"Cannot import module {module_name}")
        if not endpoints.check(locals()):
            # FIXME (Asthestarsfalll): may produce inconsistent results due to some unknown reasons.
            # ugly patch
            self.node.is_target = True
            self.is_target = True
            return file_path



@dataclass
class _CallNode:
    name: str
    trace_info: List[str]


class _DefType(Enum):
    Function = 0
    Class = 1
    Method = 2


class _DefNode:
    def __init__(
        self,
        node: Union[FunctionDef, ClassDef],
        def_type: _DefType,
        parent: Optional[str] = None,
        base: Optional[str] = None,
        meta: Optional[str] = None,
    ) -> None:
        if not isinstance(node, (FunctionDef, ClassDef)):
            raise TypeError()
        self.name = node.name
        self.def_type = def_type
        self.parent = parent
        self.lineno = node.lineno
        self.end_lineno = node.end_lineno
        self.base = base
        self.meta = meta

    def __repr__(self) -> str:
        return f"_DefNode(name={self.name})"


class _PassController:
    def __init__(self) -> None:
        self.attached = []

    def attach(self, inp: Any) -> None:
        self.attached.append(id(inp))

    def detach(self, node: Any) -> None:
        self.attached.remove(id(node))

    def __call__(self, inp: Any) -> bool:
        if id(inp) in self.attached:
            self.detach(inp)
            # do pass
            return True
        return False


class DefaultASTParser(NodeVisitor):
    def __init__(
            self, ast: AST, endpoints: EndPointManager, file_name: str, call_info=None
    ):
        self.ast = ast
        self.endpoints = endpoints
        self.file_name = file_name
        self.file_path = os.path.dirname(file_name)
        self.call_info = call_info
        self._pass_controller = _PassController()
        # store imported modules, functions, classes and variables
        # FIXME(Asthestarsfalll): handle alias of the imported, as well as functions.partial...
        self._imports: Dict[str, _ImportNode] = {}
        self._uncertain_imports: List[_ImportNode] = []
        self._local_defs: OrderedDict[str, _DefNode] = OrderedDict()
        self._calls: Dict[str, _CallNode] = {}
        self.visit(self.ast)

    def get_import_path(self):
        import_path = [i._parse_module(self.endpoints) for i in self._imports.values()]
        return [i for i in import_path if i]

    def get_target_import_names(self):
        list(self._imports.keys())
        return [i for i, v in self._imports.items() if v.is_target]

    def info(self):
        print("Imports:\n", self._imports)
        print("Calls:\n", self._calls)
        print("Uncertain:\n", self._uncertain_imports)
        print("LocalDef:\n", self._local_defs)

    def visit(self, node):
        if not self._pass_controller(node):
            method = "visit_" + node.__class__.__name__
            visitor = getattr(self, method, None)
            if visitor:
                visitor(node)
        return self.generic_visit(node)

    # Do not support for the case that directly import local module for now.
    # This requires analyzing the call of function/class,
    # and get the submodule/file where the function/class belong to.
    def _visit_import(self, node: Union[Import, ImportFrom]):
        import_names = node.names
        names = [i.asname or i.name for i in import_names]
        is_import_from = isinstance(node, ImportFrom)
        for name, import_name in zip(names, import_names):
            if not is_import_from:
                module_name = import_name.name
            else:
                module_name = node.module
            import_node = _ImportNode(node, name, module_name, import_name.asname)
            if name != "*":
                # FIXME(Asthestarsfalll): add some code to handle overridden imports.
                # TODO(Asthestarsfalll): use endpoint to sign the target imports and the others,
                #       so we can reduce the size of self._calls
                self._imports[name] = import_node
            else:
                self._uncertain_imports.append(import_node)

    visit_Import = _visit_import
    visit_ImportFrom = _visit_import

    def visit_FunctionDef(self, node: FunctionDef):
        self._local_defs[node.name] = _DefNode(node, _DefType.Function)

    def visit_ClassDef(self, node: ClassDef):
        for func in node.body:
            if isinstance(func, FunctionDef):
                self._local_defs[func.name] = _DefNode(node, _DefType.Method, node.name)
                self._pass_controller.attach(func)
        self._local_defs[node.name] = _DefNode(node, _DefType.Class)

    def _get_call_name(self, node, trace_info):
        if isinstance(node, Attribute):
            trace_info.append(node.attr)
            trace_info.append(".")
            node = node.value
            return self._get_call_name(node, trace_info)
        elif isinstance(node, Call):
            self._pass_controller.attach(node)
            node = node.func
            trace_info.append("()")
            return self._get_call_name(node, trace_info)
        elif isinstance(node, Subscript):
            idx = node.slice.value
            if hasattr(idx, "value"):
                idx = idx.value
            elif hasattr(idx, "id"):
                idx = idx.id
            else:
                raise RuntimeError()
            trace_info.append(f"[{idx}]")
            return self._get_call_name(node.value, trace_info)
        elif isinstance(node, Constant):
            node.id = trace_info[-1]
            return node
        elif isinstance(node, Name):
            trace_info.append(node.id)
            return node
        else:
            raise NotImplementedError(f"Unsupported type: {type(node)}")

    # damn it! Need to find some way to simplify those chained cases:
    # self.xxx[0][0].xx()
    # Maybe just store the whole Call Node
    # and analyze when need
    # We only need this when import * ?
    # So currently we don't need this
    def visit_Call(self, node: Call):
        """
        get the chained Function/Class Call:
            self.funcs[0]() -> self.funcs[0]
            self.aa.bb.cc[a].aa() -> self.aa.bb.cc[a].aa
        """
        func = node.func
        trace_info = []
        func = self._get_call_name(func, trace_info)

        name = func.id
        if trace_info:
            trace_info.reverse()
            name = "".join(trace_info)
        # if name not in self._local_defs:
            # just build them, and clean it after whole parse stage
            # prevent some issues caused by visit order (maybe)
        self._calls[name] = _CallNode(name, trace_info)

    # for getattr, but it also will be caught by visit_Call
    # maybe not need
    def visit_Str(self, node: Constant):
        pass

    def print(self):
        pprint(self.ast)


class Parser:
    def __init__(self, entry: Entry, endpoints=None, parser_type=DefaultASTParser):
        self.cache = set(*entry.get_cache())
        if endpoints is None:
            endpoints = LocalEndPoint(os.path.commonprefix(list(self.cache)))
        self.entry = entry
        self.parser_type = parser_type
        self.endpoints = EndPointManager(endpoints)
        self.ast_parsers = self._build_parsers(self.entry)
        self.relations = defaultdict(list)
        self.parse()

    def _build_parsers(self, entry):
        parsers = {}
        for file, ast in entry:
            parsers[file] = self.parser_type(ast, self.endpoints, file)
        return parsers

    def parse(self):
        temp = list(self.ast_parsers.values())
        module_path = []

        def _update_path():
            module_path.clear()
            for i in temp:
                # for some local imports
                with cd(i.file_path):
                    paths = set(i.get_import_path())
                self.relations[os.path.join(i.file_path, i.file_name)].extend(paths)
                for p in paths:
                    if p not in self.cache:
                        module_path.append(p)
                        self.cache.add(p)

        _update_path()
        while len(module_path) > 0:
            # new_entry = [self.entry.build(p) for p in module_path]
            entry = self.entry.build(module_path)
            parsers = self._build_parsers(entry)
            temp = list(parsers.values())
            self.ast_parsers.update(parsers)
            _update_path()

    def info(self):
        for file, parser in self.ast_parsers.items():
            print(f"----------{file}----------")
            parser.info()

    def get_parsers(self):
        return self.ast_parsers
