import re
from pathlib import Path

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


def _transpile_code(source: str, lexi_to_python: dict[str, str]) -> str:
    out: list[str] = []
    i = 0
    n = len(source)

    while i < n:
        if source[i] == "#":
            start = i
            while i < n and source[i] != "\n":
                i += 1
            out.append(source[start:i])
            continue

        if i + 2 < n:
            t = source[i : i + 3]
            if t in ('"""', "'''"):
                q = t
                out.append(q)
                i += 3
                while i + 2 < n:
                    if source[i : i + 3] == q:
                        out.append(q)
                        i += 3
                        break
                    out.append(source[i])
                    i += 1
                else:
                    out.append(source[i:])
                    i = n
                continue

        if source[i] in "\"'":
            quote = source[i]
            out.append(quote)
            i += 1
            while i < n:
                if source[i] == "\\":
                    if i + 1 < n:
                        out.append(source[i : i + 2])
                        i += 2
                    else:
                        out.append(source[i])
                        i += 1
                    continue
                if source[i] == quote:
                    out.append(quote)
                    i += 1
                    break
                out.append(source[i])
                i += 1
            continue

        if source[i].isalpha() or source[i] == "_":
            start = i
            i += 1
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            ident = source[start:i]
            out.append(lexi_to_python.get(ident, ident))
            continue

        out.append(source[i])
        i += 1

    return "".join(out)


def transpile(source: str, mapping_doc: dict) -> str:
    header_name = parse_name_header(source)
    if header_name is None:
        raise ValueError(
            'Missing header: # @leximorph name=Your Name Here  (must match mapping file)'
        )
    doc_name = mapping_doc["canonical_name"]
    if canonicalize_header_name(header_name) != doc_name:
        raise ValueError(
            f"Script name {header_name!r} does not match mapping {doc_name!r}. "
            "LexiMorph programs only run for the same chosen name."
        )
    lexi = mapping_doc["lexi_to_python"]
    body_lines: list[str] = []
    for line in source.splitlines(keepends=True):
        if _MAGIC.match(line.rstrip("\r\n")):
            continue
        body_lines.append(line)
    body = "".join(body_lines)
    return _transpile_code(body, lexi)


def transpile_file(src_path: Path, mapping_doc: dict) -> str:
    return transpile(src_path.read_text(encoding="utf-8"), mapping_doc)
