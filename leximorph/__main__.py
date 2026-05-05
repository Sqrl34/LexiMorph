import argparse
import keyword
import sys
from pathlib import Path

from leximorph.mapping import build_mapping, export_mapping, load_mapping
from leximorph.header import canonicalize_header_name, parse_name_header


def _default_dict() -> Path:
    bundled = Path(__file__).resolve().parent / "data" / "word_ranks.txt"
    if bundled.is_file():
        return bundled
    for p in (Path("/usr/share/dict/words"), Path("/usr/share/dict/web2")):
        if p.is_file():
            return p
    raise FileNotFoundError(
        "No word list found. Pass --dict /path/to/words with one word per line."
    )


def cmd_generate(args: argparse.Namespace) -> int:
    dpath = Path(args.dict) if args.dict else _default_dict()
    if args.no_builtins:
        builtins_arg: tuple[str, ...] | None = ()
    elif args.builtins is not None:
        from leximorph.builtins_map import normalize_builtin_names

        builtins_arg = normalize_builtin_names(
            [s.strip() for s in args.builtins.split(",") if s.strip()]
        )
    else:
        builtins_arg = None
    doc = build_mapping(args.name, dpath, min_buffer=args.buffer, builtins=builtins_arg)
    out = Path(args.output)
    export_mapping(doc, out)
    n_kw = len(keyword.kwlist)
    n_bi = len(doc.get("builtins_mapped") or [])
    print(f"Wrote {out} ({n_kw} keyword + {n_bi} builtin mappings).")
    return 0


def cmd_interpret(args: argparse.Namespace) -> int:
    from leximorph.interpreter import run_program

    doc = load_mapping(Path(args.mapping))
    src = Path(args.source).read_text(encoding="utf-8")
    header_name = parse_name_header(src)
    if header_name is None:
        print(
            "Missing header: # @leximorph name=Your Name Here  (must match mapping file)"
        )
        return 1
    doc_name = doc["canonical_name"]
    if canonicalize_header_name(header_name) != doc_name:
        print(
            f"Script name {header_name!r} does not match mapping {doc_name!r}. "
            "LexiMorph programs only run for the same chosen name."
        )
        return 1
    return run_program(src, doc)


def main() -> int:
    p = argparse.ArgumentParser(
        prog="leximorph",
        description="LexiMorph name-pool interpreter (no Python code generation)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Build mapping JSON from a name")
    g.add_argument("--name", required=True, help='Full name, e.g. "James Bond"')
    g.add_argument("-o", "--output", required=True, help="Output .json path")
    g.add_argument("--dict", help="Word list file (default: macOS /usr/share/dict/words)")
    g.add_argument(
        "--buffer",
        type=int,
        default=0,
        help="Mine extra words beyond keywords + default builtins (default 0)",
    )
    g.add_argument(
        "--no-builtins",
        action="store_true",
        help="Do not remap print/range/etc.; keywords only.",
    )
    g.add_argument(
        "--builtins",
        metavar="NAMES",
        help="Comma-separated builtin names to remap instead of the default set.",
    )
    g.set_defaults(func=cmd_generate)

    i = sub.add_parser(
        "interpret",
        help="Parse and interpret with the built-in LexiMorph interpreter (no CPython exec)",
    )
    i.add_argument("source")
    i.add_argument("-m", "--mapping", required=True)
    i.set_defaults(func=cmd_interpret)

    args = p.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
