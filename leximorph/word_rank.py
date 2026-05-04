"""Word commonness for LexiMorph candidate ordering (bundled ranks + optional zipf)."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

_RANK_PATH = Path(__file__).resolve().parent / "data" / "word_ranks.txt"
_DEFAULT_UNK_RANK = 60_000


@lru_cache(maxsize=1)
def _rank_map() -> dict[str, int]:
    if not _RANK_PATH.is_file():
        return {}
    text = _RANK_PATH.read_text(encoding="utf-8")
    return {w: i for i, w in enumerate(text.splitlines()) if w}


def _zipf(word: str) -> float:
    try:
        from wordfreq import zipf_frequency

        return float(zipf_frequency(word, "en"))
    except Exception:
        return 0.0


def _tie(seed: int, length: int, word: str) -> int:
    h = hashlib.blake2b(
        f"{seed}:{length}:{word}".encode(),
        digest_size=8,
    ).digest()
    return int.from_bytes(h, "big")


def candidate_sort_key(word: str, *, seed: int, length: int) -> tuple[float, int, int]:
    """
    Sort ascending: better candidates (more common / higher zipf) sort first.
    Tie-break is deterministic from ``seed`` so mappings stay stable per name.
    """
    z = _zipf(word)
    r = _rank_map().get(word, _DEFAULT_UNK_RANK)
    t = _tie(seed, length, word)
    return (-z, r, t)


def mapping_seed_from_name(canonical_name: str) -> int:
    digest = hashlib.sha256(canonical_name.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def shuffle_list(items: list[str], *, seed: int, tag: str) -> list[str]:
    """Deterministic Fisher–Yates shuffle."""
    out = list(items)
    rng_seed = int.from_bytes(
        hashlib.blake2b(f"{seed}:{tag}".encode(), digest_size=8).digest(),
        "big",
    ) % (2**63 - 1) or 1
    x = rng_seed
    for i in range(len(out) - 1, 0, -1):
        x = (x * 6364136223846793005 + 1) % (2**64)
        j = x % (i + 1)
        out[i], out[j] = out[j], out[i]
    return out
