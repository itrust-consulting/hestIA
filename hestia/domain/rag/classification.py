from __future__ import annotations

from enum import Enum


class Classification(Enum):
    PUBLIC       = (0, ["public", "public (pu)", "pu", "public (ex)", "ex"])
    INTERNAL     = (1, ["internal", "internal (in)", "in", "interne (in)", "interne"])
    RESTRICTED   = (2, ["restricted", "restricted (re)", "re", "restreint (re)", "restreint"])
    CONFIDENTIAL = (3, ["confidential", "confidential (co)", "co", "confidentiel (co)", "confidentiel"])
    SECRET       = (4, ["secret", "secret (se)", "se"])

    def __init__(self, level: int, aliases: list[str]):
        self.level = level
        self.aliases = [a.lower() for a in aliases]

    @classmethod
    def from_label(cls, label: str) -> Classification | None:
        cleaned = label.strip().lower()
        for item in cls:
            if cleaned in item.aliases:
                return item
        return None
