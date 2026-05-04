from collections import Counter
from typing import Callable

_FILLERS = "rstlne"


def canonical_name(first_last: str) -> str:
    """Normalize user-facing name (e.g. 'James Bond' -> 'james bond')."""
    parts = first_last.lower().split()
    return " ".join(parts) if parts else first_last.lower().strip()


def letter_pool_letters(first_last: str) -> str:
    """Letters only, lowercased, for multiset mining (spaces dropped)."""
    return "".join(ch.lower() for ch in first_last if ch.isalpha())


def base_pool(first_last: str) -> Counter[str]:
    c: Counter[str] = Counter()
    for ch in letter_pool_letters(first_last):
        c[ch] += 1
    return c


def augment_pool(pool: Counter[str], sufficient: Callable[[Counter[str]], bool]) -> Counter[str]:
    """
    Start from the name's letters only. Add ``rstlne`` filler letters one at a
    time only until ``sufficient(augmented_pool)`` is true (enough mined words
    per keyword length). If the name alone already suffices, no fillers are added.
    """
    p = pool.copy()
    filler_idx = 0
    max_steps = 5000
    for _ in range(max_steps):
        if sufficient(p):
            return p
        p[_FILLERS[filler_idx % len(_FILLERS)]] += 1
        filler_idx += 1
    raise RuntimeError(f"Sufficient letter pool not reached after {max_steps} filler steps.")
