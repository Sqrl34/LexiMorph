import keyword
from collections import Counter
from pathlib import Path


def is_forbidden_lexi_token(word: str) -> bool:
    """
    True if ``word`` must not be used as a LexiMorph surface token because it
    is a Python keyword or soft keyword (would read as Python or confuse tools).
    """
    if not word.isascii() or not word.isalpha():
        return True
    w = word.lower()
    if keyword.iskeyword(w):
        return True
    is_soft = getattr(keyword, "issoftkeyword", None)
    if is_soft is not None and is_soft(w):
        return True
    return False


_RAW_TWO_LETTER = """
ad am an at be do ed em en er es ex he id it me my no od of oh ok on ox
re so to up us we
""".split()

# Two-letter English fragments allowed as LexiMorph tokens; never keywords.
_TWO_LETTER = frozenset(w for w in _RAW_TWO_LETTER if not is_forbidden_lexi_token(w))


def can_spell(word: str, pool: Counter[str]) -> bool:
    need = Counter(word)
    return all(pool[ch] >= need[ch] for ch in need)


def mine_words(pool: Counter[str], dict_path: Path) -> list[str]:
    """
    Return sorted unique words from dict_path with length >= 3, plus curated
    two-letter words spellable from the pool. Excludes Python keywords and
    soft keywords so LexiMorph tokens never mirror Python's reserved names.
    """
    found: set[str] = set()

    with dict_path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = line.strip().lower()
            if len(w) < 3 or not w.isalpha():
                continue
            if is_forbidden_lexi_token(w):
                continue
            if can_spell(w, pool):
                found.add(w)

    for w in _TWO_LETTER:
        if can_spell(w, pool):
            found.add(w)

    return sorted(found)


def count_distinct_mined(pool: Counter[str], dict_path: Path) -> int:
    return len(mine_words(pool, dict_path))
