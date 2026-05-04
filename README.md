# LexiMorph

LexiMorph is a small transpiler: you pick a **name**, it builds a personal vocabulary from the letters in that name (plus `rstlne` only if needed), maps Python’s **keywords** and a curated set of **builtins** (for example `print` and `range`) to those words, and swaps them back to real Python when you run a script. Your source file is **locked** to that name via a header line.

---

## Requirements

- **Python 3.9+** (uses `pathlib`, `keyword.issoftkeyword`, etc.).
- A **word list**: one word per line, lowercase optional.  
  On macOS/Linux this is usually `/usr/share/dict/words`. If `generate` cannot find one, pass `--dict` with a path to your own file.
- **Optional:** `python3 -m pip install wordfreq` for slightly better “common word first” ranking when mining (the repo already ships a bundled frequency list).

All commands below assume you are in the **repository root** (the folder that contains `leximorph/` and this `README.md`).

```bash
cd /path/to/LexiCode
```

---

## Step 1 — Generate a mapping for your name

This writes a JSON file that lists every LexiMorph token and the Python keyword or builtin it stands for.

```bash
python3 -m leximorph generate --name "Your Full Name" -o mymap.leximorph.json
```

**Example (Lucas Guzylak):**

```bash
python3 -m leximorph generate --name "Lucas Guzylak" -o lucas_guzylak.leximorph.json
```

**Use a custom dictionary path** (if the default file is missing):

```bash
python3 -m leximorph generate --name "Ada Lovelace" -o ada.json --dict /usr/share/dict/words
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

If this does not match the mapping’s `canonical_name` (see the JSON), `run` / `transpile` will error on purpose so one person’s vocabulary cannot run with another’s mapping by mistake.

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

## Step 5 — Run or transpile

**Run** (transpile in memory and execute with the current `python3`):

```bash
python3 -m leximorph run your_script.lex -m lucas_guzylak.leximorph.json
```

**Print Python to the terminal:**

```bash
python3 -m leximorph transpile your_script.lex -m lucas_guzylak.leximorph.json
```

**Write Python to a file:**

```bash
python3 -m leximorph transpile your_script.lex -m lucas_guzylak.leximorph.json -o your_script.py
```

**Validate** (transpile, `ast.parse`, and a simple check for reserved words used like `name =` at the start of a line):

```bash
python3 -m leximorph validate your_script.lex -m lucas_guzylak.leximorph.json
```

---

## Bundled example (James Bond)

From the repo root:

```bash
python3 -m leximorph run examples/mission.lex -m examples/james_bond.leximorph.json
```

Regenerate that example mapping after changing the generator logic:

```bash
python3 -m leximorph generate --name "James Bond" -o examples/james_bond.leximorph.json
```

Then update `examples/mission.lex` so its tokens match the new `python_to_lexi` entries (they change when ranking, pairing, or builtin rules change).

---

## Command summary

| Command | Purpose |
|--------|---------|
| `python3 -m leximorph generate --name "…" -o file.json` | Build mapping (keywords + default builtins) |
| `… generate … --no-builtins` | Keywords only |
| `… generate … --builtins print,range` | Custom builtin list |
| `python3 -m leximorph run SOURCE -m MAPPING.json` | Transpile and execute |
| `python3 -m leximorph transpile SOURCE -m MAPPING.json [-o OUT.py]` | Emit Python |
| `python3 -m leximorph validate SOURCE -m MAPPING.json` | Quick sanity checks |

---

## Other file in this repo

`keyword_name_variations.py` is a separate small experiment (per-keyword name rotations to JSON). It is **not** used by the LexiMorph CLI above.
