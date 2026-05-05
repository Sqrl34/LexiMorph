from __future__ import annotations

from dataclasses import dataclass
import keyword
import re
from typing import Iterable


_HEADER_RE = re.compile(
    r"^\s*#\s*@leximorph\s+name\s*=\s*(.+?)\s*$",
    re.IGNORECASE,
)


class LexiMorphLexError(ValueError):
    def __init__(self, message: str, *, line: int, col: int):
        super().__init__(f"{message} (line {line}, col {col})")
        self.line = line
        self.col = col


@dataclass(frozen=True, slots=True)
class Token:
    kind: str  # NAME, NUMBER, STRING, OP, KEYWORD, NEWLINE, INDENT, DEDENT, EOF
    value: object | None
    line: int
    col: int

    def __repr__(self) -> str:  # pragma: no cover
        return f"Token({self.kind!r}, {self.value!r}, line={self.line}, col={self.col})"


_TWO_CHAR_OPS = {"==", "!=", "<=", ">=", "//", "**"}
_ONE_CHAR_OPS = {
    "+",
    "-",
    "*",
    "/",
    "%",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    ":",
    ",",
    "=",
    "<",
    ">",
    ".",
}

_KEYWORDS = set(keyword.kwlist) | {"True", "False", "None"}
_SOFT_KEYWORDS: set[str] = set()
_issoft = getattr(keyword, "issoftkeyword", None)
if _issoft is not None:
    # Keep this conservative: only treat soft keywords as KEYWORD if they
    # appear verbatim in the mapping (still allowed to be user identifiers).
    _SOFT_KEYWORDS = {k for k in ("match", "case") if _issoft(k)}


def tokenize(source: str, lexi_to_python: dict[str, str]) -> list[Token]:
    """
    Tokenize LexiMorph source into a small Python-like token stream.

    - Skips comments and the `# @leximorph name=...` header.
    - Emits INDENT/DEDENT based on leading spaces (tabs are an error).
    - Folds identifiers through `lexi_to_python` so the parser can work in terms
      of canonical Python keywords/builtins (e.g. 'me' -> 'if', 'ad' -> 'print').
    """
    tokens: list[Token] = []
    indent_stack = [0]

    lines = source.splitlines()
    for line_no, raw in enumerate(lines, start=1):
        # Drop the header line entirely.
        if _HEADER_RE.match(raw):
            continue

        # Strip trailing \r for Windows files that came in with splitlines()
        line = raw[:-1] if raw.endswith("\r") else raw

        i = 0
        n = len(line)

        # Blank / whitespace-only lines don't affect indentation and don't emit NEWLINE.
        if not line.strip():
            continue

        # Comment-only lines don't affect indentation and don't emit NEWLINE.
        stripped = line.lstrip(" ")
        if stripped.startswith("#"):
            continue

        # Indentation (spaces only).
        if "\t" in line[: len(line) - len(line.lstrip("\t "))]:
            # Quick check: any leading tab is forbidden.
            first_tab = line.find("\t")
            raise LexiMorphLexError("Tabs are not allowed for indentation", line=line_no, col=first_tab + 1)

        indent = len(line) - len(line.lstrip(" "))
        if indent > indent_stack[-1]:
            indent_stack.append(indent)
            tokens.append(Token("INDENT", None, line_no, 1))
        else:
            while indent < indent_stack[-1]:
                indent_stack.pop()
                tokens.append(Token("DEDENT", None, line_no, 1))
            if indent != indent_stack[-1]:
                raise LexiMorphLexError("Inconsistent indentation", line=line_no, col=1)

        i = indent
        emitted_any = False

        while i < n:
            ch = line[i]

            if ch in " \t":
                if ch == "\t":
                    raise LexiMorphLexError("Tabs are not allowed", line=line_no, col=i + 1)
                i += 1
                continue

            if ch == "#":
                break  # comment to end of line

            col = i + 1

            # Identifier
            if ch.isalpha() or ch == "_":
                j = i + 1
                while j < n and (line[j].isalnum() or line[j] == "_"):
                    j += 1
                ident = line[i:j]
                folded = lexi_to_python.get(ident, ident)
                if folded in _KEYWORDS or folded in _SOFT_KEYWORDS:
                    tokens.append(Token("KEYWORD", folded, line_no, col))
                else:
                    tokens.append(Token("NAME", folded, line_no, col))
                emitted_any = True
                i = j
                continue

            # Number (int or float)
            if ch.isdigit():
                j = i + 1
                has_dot = False
                while j < n:
                    c = line[j]
                    if c.isdigit():
                        j += 1
                        continue
                    if c == "." and not has_dot:
                        has_dot = True
                        j += 1
                        continue
                    break
                text = line[i:j]
                if text.count(".") == 1:
                    if text.startswith(".") or text.endswith("."):
                        raise LexiMorphLexError("Invalid float literal", line=line_no, col=col)
                    val = float(text)
                else:
                    val = int(text)
                tokens.append(Token("NUMBER", val, line_no, col))
                emitted_any = True
                i = j
                continue

            # String literal: '...' or "..." with basic escapes
            if ch in ("'", '"'):
                quote = ch
                j = i + 1
                out_chars: list[str] = []
                while j < n:
                    c = line[j]
                    if c == quote:
                        break
                    if c == "\\":
                        if j + 1 >= n:
                            raise LexiMorphLexError("Unterminated string escape", line=line_no, col=j + 1)
                        esc = line[j + 1]
                        if esc == "n":
                            out_chars.append("\n")
                        elif esc == "t":
                            out_chars.append("\t")
                        elif esc == "\\":
                            out_chars.append("\\")
                        elif esc == "'":
                            out_chars.append("'")
                        elif esc == '"':
                            out_chars.append('"')
                        else:
                            raise LexiMorphLexError(f"Unsupported escape \\{esc}", line=line_no, col=j + 1)
                        j += 2
                        continue
                    out_chars.append(c)
                    j += 1
                if j >= n or line[j] != quote:
                    raise LexiMorphLexError("Unterminated string literal", line=line_no, col=col)
                tokens.append(Token("STRING", "".join(out_chars), line_no, col))
                emitted_any = True
                i = j + 1
                continue

            # Operators / punctuation
            if i + 1 < n:
                two = line[i : i + 2]
                if two in _TWO_CHAR_OPS:
                    tokens.append(Token("OP", two, line_no, col))
                    emitted_any = True
                    i += 2
                    continue
            if ch in _ONE_CHAR_OPS:
                tokens.append(Token("OP", ch, line_no, col))
                emitted_any = True
                i += 1
                continue

            raise LexiMorphLexError(f"Unexpected character {ch!r}", line=line_no, col=col)

        if emitted_any:
            tokens.append(Token("NEWLINE", None, line_no, n + 1))

    # Finalize indentation
    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(Token("DEDENT", None, line_no if lines else 1, 1))

    tokens.append(Token("EOF", None, (len(lines) if lines else 1) + 1, 1))
    return tokens


def iter_tokens(source: str, lexi_to_python: dict[str, str]) -> Iterable[Token]:
    """Streaming wrapper for tokenize() (kept for debugging / future extensions)."""
    return tokenize(source, lexi_to_python)

