"""Parse source code into semantic chunks with stable identifiers."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class CodeChunk:
    chunk_id: str          # path::qualified_name
    kind: str              # function | class | constant
    name: str
    signature: str
    docstring: str
    params: list[str] = field(default_factory=list)
    defaults: dict[str, str] = field(default_factory=dict)
    source: str = ""


def _signature_of(node: ast.FunctionDef) -> tuple[str, list[str], dict[str, str]]:
    params, defaults = [], {}
    args = node.args
    all_args = args.posonlyargs + args.args + args.kwonlyargs
    for arg in all_args:
        params.append(arg.arg)
    positional = args.posonlyargs + args.args
    for arg, default in zip(positional[len(positional) - len(args.defaults):],
                            args.defaults):
        defaults[arg.arg] = ast.unparse(default)
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is not None:
            defaults[arg.arg] = ast.unparse(default)
    rendered = []
    for param in params:
        rendered.append(f"{param}={defaults[param]}" if param in defaults
                        else param)
    return f"{node.name}({', '.join(rendered)})", params, defaults


def parse_source(path: str, source: str) -> list[CodeChunk]:
    tree = ast.parse(source)
    chunks: list[CodeChunk] = []

    def visit(node, prefix: str = ""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                signature, params, defaults = _signature_of(child)
                qualified = f"{prefix}{child.name}"
                chunks.append(CodeChunk(
                    chunk_id=f"{path}::{qualified}", kind="function",
                    name=qualified, signature=signature,
                    docstring=ast.get_docstring(child) or "",
                    params=params, defaults=defaults,
                    source=ast.unparse(child)))
            elif isinstance(child, ast.ClassDef):
                qualified = f"{prefix}{child.name}"
                chunks.append(CodeChunk(
                    chunk_id=f"{path}::{qualified}", kind="class",
                    name=qualified, signature=f"class {child.name}",
                    docstring=ast.get_docstring(child) or "",
                    source=ast.unparse(child)))
                visit(child, prefix=f"{qualified}.")
            elif isinstance(child, ast.Assign) and prefix == "":
                for target in child.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        chunks.append(CodeChunk(
                            chunk_id=f"{path}::{target.id}", kind="constant",
                            name=target.id,
                            signature=f"{target.id} = {ast.unparse(child.value)}",
                            docstring="",
                            source=ast.unparse(child)))

    visit(tree)
    return chunks


def parse_file(path: str) -> list[CodeChunk]:
    with open(path, encoding="utf-8") as fh:
        return parse_source(path, fh.read())
