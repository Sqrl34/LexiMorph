"""Built-in callables LexiMorph may remap (surface token -> Python name)."""

import keyword

_RAW_DEFAULT: tuple[str, ...] = (
    "print",
    "range",
    "len",
    "str",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "set",
    "tuple",
    "input",
    "open",
    "min",
    "max",
    "sum",
    "enumerate",
    "zip",
    "abs",
    "round",
    "ord",
    "chr",
    "repr",
)


def normalize_builtin_names(names: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    """Lowercase, dedupe, drop keywords/soft keywords and empty strings."""
    if not names:
        return ()
    seen: set[str] = set()
    out: list[str] = []
    is_soft = getattr(keyword, "issoftkeyword", None)
    for raw in names:
        b = raw.strip().lower()
        if not b or not b.isidentifier():
            continue
        if keyword.iskeyword(b):
            continue
        if is_soft is not None and is_soft(b):
            continue
        if b in seen:
            continue
        seen.add(b)
        out.append(b)
    return tuple(out)


def default_builtin_names() -> tuple[str, ...]:
    """Curated builtins (common REPL-style helpers), safe for LexiMorph tokens."""
    return normalize_builtin_names(_RAW_DEFAULT)
