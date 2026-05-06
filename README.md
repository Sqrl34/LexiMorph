# LexiMorph

LexiMorph is a small interpreter: you pick a **name**, it builds a personal vocabulary from the letters in that name (plus `rstlne` only if needed), maps Python’s **keywords** and a curated set of **builtins** (for example `print` and `range`) to those words, and evaluates the resulting program with a built-in tree-walking interpreter. Your source file is **locked** to that name via a header line.

# Website for more information and examples is found [here!](https://sqrl34.github.io/LexiMorph/) [https://sqrl34.github.io/LexiMorph/](https://sqrl34.github.io/LexiMorph/)

---

## Requirements

- **Python 3.9+** (uses `pathlib`, `keyword.issoftkeyword`, etc.).
- A **word list**: one word per line, lowercase optional.  
  LexiMorph ships a bundled list (default). If you want to override it, pass `--dict` with a path to your own file.
- **Optional:** `python -m pip install wordfreq` for slightly better “common word first” ranking when mining (the repo already ships a bundled frequency list).

All commands below assume you are in the **repository root** (the folder that contains `leximorph/` and this `README.md`).

```bash
cd /path/to/LexiMorph
```

---

## Step 1 — Generate a mapping for your name

This writes a JSON file that lists every LexiMorph token and the Python keyword or builtin it stands for.

```bash
python -m leximorph generate --name "Your Full Name" -o mymap.leximorph.json
```

**Example (Lucas Guzylak):**

```bash
python -m leximorph generate --name "Lucas Guzylak" -o lucas_guzylak.leximorph.json
```

**Use a custom dictionary path** (to override the bundled default):

```bash
python -m leximorph generate --name "Ada Lovelace" -o ada.json --dict /path/to/words.txt
```

**Optional flags**

- `--buffer N` — mine extra letters beyond what is needed for keywords + default builtins (default `0`).
- `--no-builtins` — only remap the 35 keywords; leave `print`, `range`, etc. as normal Python.
- `--builtins print,range,len` — your own comma-separated list instead of the default curated builtins.

Parent directories for `-o` are created automatically if they do not exist.

---

## Step 2 — Add the name header to your LexiMorph source

The first matching line in your source file must tie the script to the same name you used in `generate`. Spacing and letter case in the header are normalized; spelling must match.

```text
# @leximorph name=Lucas Guzylak
```

If this does not match the mapping’s `canonical_name` (see the JSON), `interpret` will error on purpose so one person’s vocabulary cannot run with another’s mapping by mistake.

---

## Step 3 — Look up which word means which keyword or builtin

Open your `*.leximorph.json` and use:

- **`python_to_lexi`** — Python keyword or builtin name → LexiMorph word (what you type).
- **`lexi_to_python`** — LexiMorph word → Python keyword or builtin name.
- **`builtins_mapped`** — list of builtin names included (empty if you used `--no-builtins`).
- **`reserved_lexi`** — all LexiMorph tokens you must not reuse as your own variable or function names in the obvious way.
- **`name_letter_pool`** — letters from the name only.
- **`letter_pool`** — letters used for mining (name letters plus any `rstlne` fillers that were required).

The default builtin set lives in `leximorph/builtins_map.py`. Python **keywords** and **soft keywords** are never used as LexiMorph spellings; builtin *names* like `print` are not mined as tokens so they never double as a random LexiMorph word.

---

## Step 4 — Write your program

Use normal Python layout (indentation, colons, strings, comments). Replace **keywords** and any **remapped builtins** with the LexiMorph words from `python_to_lexi`, for example:

```text
# @leximorph name=Lucas Guzylak
success = 1
# ... token for `if`, then the condition and colon ...
# ... token for `print` instead of spelling print ...
```

Use any filename you like; `.lex` is a common convention.

---

## Step 5 — Interpret (built-in interpreter)

LexiMorph evaluates programs with a small **tree-walking interpreter** and does **not** generate Python code or call `ast`, `exec`, or `subprocess`.

```bash
python -m leximorph interpret your_script.lex -m lucas_guzylak.leximorph.json
```

**Supported subset**

- **Statements**: assignment (`x = expr`), expression statement, `if/elif/else`, `while`, `for name in iterable`, `def name(params):`, `return`, `pass`, `break`, `continue`.
- **Expressions**: int/float/string/`True`/`False`/`None`, identifiers, parenthesized expressions, list literals `[a, b]`, indexing `a[i]`, calls `f(args)`, unary `-` and `not`, binary `+ - * / // % **`, comparisons `< <= > >= == !=`, boolean `and`/`or`.
- **Builtins** (implemented by the interpreter): `print`, `range`, `len`, `int`, `float`, `str`, `bool`, `abs`, `min`, `max`, `sum`, `input`, `enumerate`, `list`.

---

## Bundled example (James Bond)

From the repo root:

```bash
python -m leximorph interpret examples/mission.lex -m examples/james_bond.leximorph.json
```

Regenerate that example mapping after changing the generator logic:

```bash
python -m leximorph generate --name "James Bond" -o examples/james_bond.leximorph.json
```

Additional examples (generated for the name `jaiden`):

```bash
python -m leximorph interpret examples/fizzbuzz_jaiden.lex -m examples/jaiden.leximorph.json
```

Interpreter-subset demo (James Bond mapping):

```bash
python -m leximorph interpret examples/interpreter/interp_demo.lex -m examples/james_bond.leximorph.json
```

Then update `examples/mission.lex` so its tokens match the new `python_to_lexi` entries (they change when ranking, pairing, or builtin rules change).

---

## Command summary

| Command | Purpose |
|--------|---------|
| `python -m leximorph generate --name "…" -o file.json` | Build mapping (keywords + default builtins) |
| `… generate … --no-builtins` | Keywords only |
| `… generate … --builtins print,range` | Custom builtin list |
| `python -m leximorph interpret SOURCE -m MAPPING.json` | Parse and interpret (supported subset) |

---

## Other file in this repo

`keyword_name_variations.py` is a separate small experiment (per-keyword name rotations to JSON). It is **not** used by the LexiMorph CLI above.
