# CodeSlim

`CodeSlim` is a library that automatically extracts and refactors code based on required dependencies (Package\Module\File) in a large and nested python project/module/package. 
It's based on AST(Abstract syntax tree) to optimize your codebase by extracting relevant functions and classes into more modular components, and also simplifying the code structure, making it easier to understand, manage and maintain.

Run the slim file in tests to figue out what `CodeSlim` can do now.

## Introduction

Currently, `CodeSlim` is under early develepment stage.

The goals of `CodeSlim` are as following:

1. Automatically extracting **relevant code** through some given entries and endpoints, and refactoring the extracted code into certain **given structure**(file(s), folder(s)).
2. Simplifying some complex and chained class inherience. Eliminating class inherience relationship.
3. Fully support user customized strategies(Entry, Endpoint, CodeGen).
4. Some other insteresting and optional functions, such as inline, function merging...

## Core Concepts

Currently, `CodeSlim` is establish on `Entry`, `Endpoint` and `CodeGen`.

As the name suggests, `Entry` is the enter point of analysis, all the final extracted code is relevant to entries, such as reference, function call, class inherience and etc.

`EndPoint` grant `CodeSlim` the ability to trace or not trace some certain python library files instead of only local files. By default, we only trace local files which are determined by the directory scope of the `Entry`.

`CodeGen` is significant to refactor code into target structure.


## Analysis of key and difficult points.

The key and difficult points in slim procedure are as following:

1. Import relationship. (Relative imports/Absolute imports/(Sub)Module inner imports/Import from file/Import from (sub)module/Import all(*))
2. Function call. (Directly call/Call from Attributes(getitem, getattar)/Chained Call)
3. Generate proper refactored structure. (Analysis the refactored import relationship)
