"""Split markdown documentation into sections and mine code references."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DocSection:
    section_id: str        # path#heading-path
    path: str
    heading_path: str      # "Configuration > Environment Variables"
    content: str
    code_refs: list[str] = field(default_factory=list)


def parse_markdown(path: str, text: str) -> list[DocSection]:
    sections: list[DocSection] = []
    stack: list[tuple[int, str]] = []
    current_lines: list[str] = []
    current_heading = "(intro)"

    def flush():
        if not current_lines and current_heading == "(intro)":
            return
        content = "\n".join(current_lines).strip()
        refs = sorted(set(re.findall(r"`([A-Za-z_][A-Za-z0-9_.()]*)`", content)))
        refs = [r.rstrip("()") for r in refs]
        sections.append(DocSection(
            section_id=f"{path}#{current_heading}",
            path=path, heading_path=current_heading,
            content=content, code_refs=refs))

    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            flush()
            level = len(match.group(1))
            title = match.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            current_heading = " > ".join(t for _, t in stack)
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    return sections


def parse_doc_file(path: str) -> list[DocSection]:
    with open(path, encoding="utf-8") as fh:
        return parse_markdown(path, fh.read())
