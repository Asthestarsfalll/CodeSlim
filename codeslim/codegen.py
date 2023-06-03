import os
import os.path as osp
import shutil
from ast import (AST, ClassDef, FunctionDef, Import, ImportFrom,
                 NodeTransformer, NodeVisitor)
from collections import OrderedDict, defaultdict
from typing import Callable, Dict, List, Optional, Union

import astor
from astpretty import pprint  # for pdb debug

from .parse import DefaultASTParser, Parser, _DefType
from .utils import cd

__all__ = ["FileLevelCodeGenerator", "SegmentCodeGenerator"]

CODEGEN_PREFIX = "# Generated by CodeSlim\n"
REMOVE_NODE = None


def _is_file_exist(dir, filename):
    return osp.exists(osp.join(dir, filename))


def _get_file_name(file_path):
    file = osp.basename(file_path).split(".")[:-1]
    return ".".join(file)


def _get_local_methods(parser: DefaultASTParser):
    local_methods = {}
    for name, func in parser._local_defs.items():
        if func.def_type == _DefType.Method:
            local_methods[name] = func
    return local_methods


# Copy lines or generating code from AST node?
# It seems that generating code form AST node is more
# convenient for rewriting, for instance,
# import modules from refactored file structures,
# inheriting from rewritten base class...
class CodeGenerator:
    def generate(self):
        raise NotImplementedError()

    def _preprocess(self, file, parser):
        pass

    def _postprocess(self):
        pass

    def _generate_from_str(self, filename, contends: Optional[List[str]] = None):
        with open(filename, "w", encoding='UTF-8') as f:
            f.writelines(CODEGEN_PREFIX)
            if contends:
                for c in contends:
                    f.writelines(c)

    def _generate_from_ast(self, filename, ast):
        source_code = astor.to_source(ast)
        with open(filename, "w", encoding='UTF-8') as f:
            f.writelines(CODEGEN_PREFIX)
            f.write(source_code)

    def generate_init(self, target_path, force=False):
        if not force and _is_file_exist(target_path, "__init__.py"):
            raise RuntimeError("__init__.py exists!")
        path = osp.join(target_path, "__init__.py")
        self._generate_from_str(path)

    def rewrite_imports(self, ast, module_mapper):
        raise NotImplementedError()

    def copy_file(self, source_file, target_dir, force=False):
        if not force and _is_file_exist(target_dir, osp.basename(source_file)):
            raise RuntimeError(f"{source_file} exists!")
        shutil.copy(source_file, target_dir)

    def makedirs(self, path):
        os.makedirs(path, exist_ok=True)

    # Do we need to fotmat generated code?
    def format(self, file_path):
        pass


class Rewriter(NodeTransformer):
    def __init__(
        self,
        targets: Dict[str, Callable],
        pre_hooks: Optional[Dict[str, Callable]] = None,
        post_hooks: Optional[Dict[str, Callable]] = None,
    ):
        for name, func in targets.items():
            setattr(self, "visit_" + name, func)

        self.pre_hooks = pre_hooks or {}
        self.post_hooks = post_hooks or {}

    def visit(self, node):
        node_name = node.__class__.__name__
        if node_name in self.pre_hooks:
            self.pre_hooks[node_name](node)
        if node is REMOVE_NODE:
            return node
        method = "visit_" + node_name
        visitor = getattr(self, method, self.generic_visit)
        node = visitor(node)
        if node_name in self.post_hooks:
            node = self.post_hooks[node_name](node)
        return node


class _ClassVisitor(NodeVisitor):
    def __init__(self, cls_node):
        self.methods = {}
        self.visit(cls_node)

    def visit_FunctionDef(self, node: FunctionDef):
        self.methods[node.name] = node
        return self.generic_visit(node)


# Do we need to support class merging in file-level code slim?
#   Maybe it's not cater to the definition of file-level?
# ClassMerging or InheritanceMerging?
# maybe we can also support some kinds of inline mechanism like c++.
# Is there has any uasge scenario the inner class is inherited from a extern class?
class ClassMerging:
    Eliminate = 1  # merge into one class inheriting from object
    KeepOne = 2  # merge into two class -- the lowest level class and base class.
    # all the methods, property will be patched to the highest level base class.
    def __init__(self, parser, base_parsers: Dict, class_name: str):
        self.parser = parser
        self.base_parsers = base_parsers
        self.rewriter = Rewriter(
            {"FunctionDef": self._merge_methods, "Name": self._rewrite_name}
        )
        self.cls_node = parser._local_defs[class_name].node
        self.methods = _ClassVisitor(self.cls_node).methods

    # TODO
    def _rewrite_super(self):
        pass

    def _merge_methods(self, node):
        if node.name not in self.methods:
            # astor.to_source do not use lineno, so just append it
            self.cls_node.body.append(node)
        return node

    def _rewrite_name(self, node):
        return node

    def _merge_property(self, node):
        pass

    def merge(self):
        for base_name, base_parser in self.base_parsers.items():
            self.cur_base = base_name
            base_node = base_parser._local_defs[base_name].node
            self.cls_node.bases = base_node.bases
            self.rewriter.visit(base_node)
        # FIXME(Asthestarsfalll): need to re-analysis the dependency of each parser.


# TODO
class UnusedRemoval:
    pass


# TODO
class InLine:
    pass


class FileLevelCodeGenerator(CodeGenerator):
    def __init__(
        self,
        target_dir: str,
        parser: Parser,
        # TODO(Asthestarsfalll): Support customize file structure
        module_mapper: Optional[Dict[str, str]] = None,
        custom_rewriter: Optional[Dict[str, Callable]] = None,
        class_merge_level: Optional[int] = None,
    ):
        self.target_dir = target_dir
        self.parsers = parser.get_parsers()
        self.module_mapper = module_mapper or {}
        if (
            self.__class__.__name__ == "FileLevelCodeGenerator"
            and class_merge_level is not None
        ):
            raise ValueError("File level code slim do not support for class merging.")
        if class_merge_level:
            for p in self.parsers.values():
                p.get_target_merge_class()
        self.merge_level = class_merge_level
        self.rewriter = self._build_rewriter(custom_rewriter)
        self.imports_info = self._get_imports_info(parser.relations)
        self.relation = parser.relations

    def _build_rewriter(self, custom_rewriter):
        rewrite_funcs = {
            "Import": self.rewrite_imports,
            "ImportFrom": self.rewrite_imports,
        }
        if custom_rewriter is not None:
            rewrite_funcs.update(custom_rewriter)
        return Rewriter(rewrite_funcs)

    def _get_imports_info(self, relation):
        extra_info = defaultdict(list)
        for file, target_file in relation.items():
            for f in target_file:
                extra_info[f].append(file)
        return extra_info

    def generate(self):
        self.makedirs(self.target_dir)
        with cd(self.target_dir):
            for file, parser in self.parsers.items():
                file_name = osp.basename(parser.file_name)
                # TODO(Asthestarsfalll): need to process __init__ file
                if file_name == "__init__.py":
                    continue
                self._preprocess(file, parser)
                self.rewriter.visit(parser.ast)
                self._postprocess()
                self._generate_from_ast(file_name, parser.ast)

    def rewrite_imports(self, node: Union[ImportFrom, Import]) -> AST:
        if isinstance(node, ImportFrom) and hasattr(node, "is_target"):
            module_name = node.module
            if module_name in self.module_mapper:
                module_name = self.module_mapper[module_name]
            else:
                # FIXME(Asthestarsfalll): need automatically get the file where the imported module belongs to
                module_name = module_name.split(".")[-1]
                node.level = 0
            node.module = module_name

        return node


class SegmentCodeGenerator(FileLevelCodeGenerator):
    def _build_rewriter(self, custom_rewriter):
        rewrite_funcs = {
            "Import": self.rewrite_imports,
            "ImportFrom": self.rewrite_imports,
            "FunctionDef": self.rewrite_defs,
            "ClassDef": self.rewrite_defs,
        }
        if custom_rewriter is not None:
            rewrite_funcs.update(custom_rewriter)
        pre_hooks = {"ClassDef": self._classdef_hook}
        return Rewriter(rewrite_funcs, pre_hooks=pre_hooks)

    def _classdef_hook(self, node: ClassDef):
        if node.name not in self.class_merge_info:
            return node
        info = self.class_merge_info[node.name]
        rewrite_parsers = {k: self.parsers[info[k]] for k in info}
        self.base_parsers = rewrite_parsers
        ClassMerging(self.cur_parser, rewrite_parsers, node.name).merge()
        return REMOVE_NODE

    def _analyze_local_calls(self, parser):
        calls = parser._calls
        defs = parser._local_defs
        local_used = []
        # TODO(Asthestarsfalll): reduce the size of calls
        if calls and defs:
            # TODO(Asthestarsfalll): need more logic to tackle complex situation.
            for name, call in calls.items():
                if name in defs:
                    local_used.append(name)
        return local_used

    def _rewrite_class_imports(self, node):
        # FIXME
        if isinstance(node, ImportFrom):
            name = node.names[0].asname or node.names[0].name
            if name in self.base_parsers:
                return REMOVE_NODE
        else:
            raise NotImplemented
        return node

    def _preprocess(self, file, parser):
        merge_class = parser._to_merge_classes
        target_files = defaultdict(OrderedDict)

        for path in self.relation[file]:
            p = self.parsers[path]
            for m, bases in merge_class.items():
                for base in bases:
                    if base in p._local_defs:
                        target_files[m][base] = path

        extern_uesd = []
        for i in self.imports_info[file]:
            p = self.parsers[i]
            extern_uesd += p.get_target_import_names()
        self.extern_used = extern_uesd
        self.local_used = self._analyze_local_calls(parser)
        self.class_merge_info = target_files
        self.cur_parser = parser

    def _postprocess(self):
        rewriter = Rewriter(
            {
                "ImportFrom": self._rewrite_class_imports,
                "Import": self._rewrite_class_imports,
            }
        )
        rewriter.visit(self.cur_parser.ast)

    def rewrite_defs(self, node: Union[FunctionDef, ClassDef]):
        if node.name not in self.extern_used and node.name not in self.local_used:
            return REMOVE_NODE
        return node
