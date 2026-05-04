import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

from leximorph.mapping import build_mapping, export_mapping, load_mapping
from leximorph.transpiler import transpile_file


def _default_dict() -> Path:
    for p in (Path("/usr/share/dict/words"), Path("/usr/share/dict/web2")):
        if p.is_file():
            return p
    raise FileNotFoundError(
        "No system word list found. Pass --dict /path/to/words with one word per line."
    )


def cmd_generate(args: argparse.Namespace) -> int:
    dpath = Path(args.dict) if args.dict else _default_dict()
    doc = build_mapping(args.name, dpath, min_buffer=args.buffer)
    out = Path(args.output)
    export_mapping(doc, out)
    print(f"Wrote {out} ({len(doc['lexi_to_python'])} keyword mappings).")
    return 0


def cmd_transpile(args: argparse.Namespace) -> int:
    doc = load_mapping(Path(args.mapping))
    py = transpile_file(Path(args.source), doc)
    out = Path(args.output) if args.output else None
    if out:
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(py, encoding="utf-8")
        print(f"Wrote {out}")
    else:
        sys.stdout.write(py)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    doc = load_mapping(Path(args.mapping))
    py = transpile_file(Path(args.source), doc)
    ast.parse(py)
    r = subprocess.run([sys.executable, "-c", py], check=False)
    return r.returncode


def cmd_validate(args: argparse.Namespace) -> int:
    doc = load_mapping(Path(args.mapping))
    py = transpile_file(Path(args.source), doc)
    try:
        ast.parse(py)
    except SyntaxError as e:
        print(f"Syntax error after transpile: {e}")
        return 1
    reserved = set(doc["lexi_to_python"])
    bad: list[str] = []
    bind = re.compile(r"^(\s*)([A-Za-z_][\w]*)\s*=(?!=)")
    for line in Path(args.source).read_text(encoding="utf-8").splitlines():
        m = bind.match(line)
        if m:
            ident = m.group(2)
            if ident in reserved:
                bad.append(line.strip())
    if bad:
        print("Possible reserved LexiMorph word used as assignment target:")
        for b in bad:
            print(f"  {b}")
        return 1
    print("Transpile OK; no obvious reserved-word assignments.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="leximorph", description="LexiMorph name-pool transpiler")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Build mapping JSON from a name")
    g.add_argument("--name", required=True, help='Full name, e.g. "James Bond"')
    g.add_argument("-o", "--output", required=True, help="Output .json path")
    g.add_argument("--dict", help="Word list file (default: macOS /usr/share/dict/words)")
    g.add_argument(
        "--buffer",
        type=int,
        default=0,
        help="Mine extra words beyond Python keyword count (default 0)",
    )
    g.set_defaults(func=cmd_generate)

    t = sub.add_parser("transpile", help="LexiMorph source -> Python on stdout or file")
    t.add_argument("source", help=".lex or other source file")
    t.add_argument("-m", "--mapping", required=True, help="Mapping JSON from generate")
    t.add_argument("-o", "--output", help="Write Python here instead of stdout")
    t.set_defaults(func=cmd_transpile)

    r = sub.add_parser("run", help="Transpile and execute with current Python")
    r.add_argument("source")
    r.add_argument("-m", "--mapping", required=True)
    r.set_defaults(func=cmd_run)

    v = sub.add_parser("validate", help="Transpile + AST check + simple reserved binding scan")
    v.add_argument("source")
    v.add_argument("-m", "--mapping", required=True)
    v.set_defaults(func=cmd_validate)

    args = p.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
