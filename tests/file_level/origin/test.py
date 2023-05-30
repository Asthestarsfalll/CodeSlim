from codeslim.codegen import FileLevelCodeGenerator
from codeslim.entry import FileEntry
from codeslim.parse import Parser

FileLevelCodeGenerator("../target/", Parser(FileEntry("./train.py"))).generate()
