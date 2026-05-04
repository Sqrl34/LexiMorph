import hashlib
import json
import keyword
from collections import Counter, defaultdict
from pathlib import Path

from leximorph.miner import can_spell, is_forbidden_lexi_token, mine_words
from leximorph.pool import augment_pool, base_pool, canonical_name
from leximorph.word_rank import (
    candidate_sort_key,
    mapping_seed_from_name,
    shuffle_list,
)


def _keywords_by_length() -> dict[int, list[str]]:
    buckets: dict[int, list[str]] = defaultdict(list)
    for k in keyword.kwlist:
        buckets[len(k)].append(k)
    for length in buckets:
        buckets[length].sort(key=str.lower)
    return dict(buckets)


def _pair_by_length_bucket(
    words: list[str],
    *,
    canonical_name: str,
    name_pool: Counter[str],
) -> dict[str, str]:
    """
    Map LexiMorph word -> Python keyword per length bucket.

    Words spellable using **only** letters from the person's name (``name_pool``)
    are preferred: they are ordered by commonness first. Words that require
    filler letters (RSTLNE) added to the multiset come after, also by commonness.
    Within the chosen set, assignment to keywords is shuffled deterministically
    from ``canonical_name``.
    """
    seed = mapping_seed_from_name(canonical_name)
    kw_by_len = _keywords_by_length()
    lexi_by_len: dict[int, list[str]] = defaultdict(list)
    for w in words:
        lexi_by_len[len(w)].append(w)

    mapping: dict[str, str] = {}
    for length in sorted(kw_by_len):
        kws = kw_by_len[length]
        lexi = lexi_by_len.get(length, [])
        if len(lexi) < len(kws):
            raise ValueError(
                f"Not enough mined words of length {length}: "
                f"need {len(kws)}, have {len(lexi)}."
            )

        tier1 = [w for w in lexi if can_spell(w, name_pool)]
        tier2 = [w for w in lexi if not can_spell(w, name_pool)]
        key = lambda w: candidate_sort_key(w, seed=seed, length=length)
        lexi_sorted = sorted(tier1, key=key) + sorted(tier2, key=key)
        chosen = lexi_sorted[: len(kws)]
        shuffled_lexi = shuffle_list(
            chosen,
            seed=seed,
            tag=f"lex:{length}",
        )
        shuffled_kw = shuffle_list(
            list(kws),
            seed=seed,
            tag=f"kw:{length}",
        )
        for lx, py in zip(shuffled_lexi, shuffled_kw):
            mapping[lx] = py
    return mapping


def _pool_sufficient(pool: Counter[str], dict_path: Path) -> bool:
    words = mine_words(pool, dict_path)
    lexi_by_len: dict[int, list[str]] = defaultdict(list)
    for w in words:
        lexi_by_len[len(w)].append(w)
    kw_by_len = _keywords_by_length()
    for length, kws in kw_by_len.items():
        if len(lexi_by_len.get(length, [])) < len(kws):
            return False
    return True


def build_mapping(
    first_last: str,
    dict_path: Path,
    *,
    min_buffer: int = 0,
) -> dict:
    """
    Build full mapping document: letter pool, optional fillers, lexi->python.
    """
    name = canonical_name(first_last)
    pool0 = base_pool(first_last)

    def sufficient(p: Counter[str]) -> bool:
        if not _pool_sufficient(p, dict_path):
            return False
        if min_buffer <= 0:
            return True
        return len(mine_words(p, dict_path)) >= len(keyword.kwlist) + min_buffer

    pool = augment_pool(pool0, sufficient)
    words = mine_words(pool, dict_path)
    lexi_to_python = _pair_by_length_bucket(
        words,
        canonical_name=name,
        name_pool=pool0,
    )
    for lx in lexi_to_python:
        if is_forbidden_lexi_token(lx):
            raise RuntimeError(
                f"Internal error: LexiMorph token {lx!r} is a Python keyword/soft keyword; "
                "report this mapping bug."
            )

    return {
        "leximorph_version": 1,
        "canonical_name": name,
        "mapping_seed_hex": hashlib.sha256(name.encode("utf-8")).hexdigest()[:16],
        "name_letter_pool": dict(sorted(pool0.items())),
        "letter_pool": dict(sorted(pool.items())),
        "reserved_lexi": sorted(lexi_to_python.keys()),
        "lexi_to_python": lexi_to_python,
        "python_to_lexi": {v: k for k, v in lexi_to_python.items()},
    }


def export_mapping(doc: dict, out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")


def load_mapping(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
