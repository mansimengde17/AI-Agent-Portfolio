"""Prompt configuration: the versioned artifact under CI."""

from __future__ import annotations

from dataclasses import dataclass, field

import yaml


@dataclass(frozen=True)
class PromptConfig:
    version: str
    model: str
    temperature: float
    system_prompt: str
    few_shot: list[dict] = field(default_factory=list)
    commit_message: str = ""

    @classmethod
    def from_yaml(cls, path: str) -> "PromptConfig":
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        return cls(
            version=str(raw["version"]),
            model=raw.get("model", "gpt-4o-mini"),
            temperature=float(raw.get("temperature", 0.0)),
            system_prompt=raw["system_prompt"],
            few_shot=raw.get("few_shot", []) or [],
            commit_message=raw.get("commit_message", ""),
        )
