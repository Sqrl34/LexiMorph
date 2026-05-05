from __future__ import annotations

import re

_MAGIC = re.compile(
    r"^\s*#\s*@leximorph\s+name\s*=\s*(.+?)\s*$",
    re.IGNORECASE,
)


def parse_name_header(source: str) -> str | None:
    for line in source.splitlines():
        m = _MAGIC.match(line)
        if m:
            return m.group(1).strip()
    return None


def canonicalize_header_name(header: str) -> str:
    return " ".join(header.lower().split())

