#!/usr/bin/env python3
"""Generate the app's exercise data from the vault's curated notes.

    python tools/build-library.py --check   # validate + diff, writes nothing
    python tools/build-library.py           # regenerate

The vault is the SOURCE OF TRUTH for exercise content (see the vault note
"Library System"). Everything downstream -- library.json, SEED_CLASSIFICATION
in index.html, the catalog seed SQL -- is generated from it, so the three
copies that used to be hand-synced can never drift again.

HARD SAFETY PROPERTY: only `Exercise Library/` is read, and only notes with
`status: ready` are emitted. Raw `Exercise Dump/` material can never reach the
app, and a half-finished curated entry can never ship. Any validation failure
aborts the whole run -- never a partial write.

The classification VOCABULARY (muscle groups, per-group movement patterns) is
parsed out of index.html rather than duplicated here: index.html stays the
authority on what's a valid value, the vault stays the authority on content.
No third copy.

No third-party dependencies on purpose (this machine has Python 3 and no pip
packages guaranteed) -- hence the small frontmatter parser below.
"""
import argparse, json, pathlib, re, sys

REPO = pathlib.Path(__file__).resolve().parent.parent
# Vault lives beside the repo: Projects/Code/gym-tracker + Projects/Projects Vault
DEFAULT_VAULT = REPO.parent.parent / "Projects Vault" / "Gym Tracker"

# Fields emitted into library.json, in this order. Optional ones are omitted
# when empty, so adding a schema field never perturbs notes that don't use it.
REQUIRED = ["id", "name", "type", "compound", "regime", "mainMuscle", "movementPattern"]
OPTIONAL = ["accessoryMuscles", "name_en", "aliases", "equipment",
            "cues_pt", "cues_en", "errors_pt", "errors_en", "stretchEmphasis", "rest"]
# Vault-only bookkeeping -- deliberately never shipped to the app.
VAULT_ONLY = {"status", "source", "sourceId"}

VALID_STATUS = {"tbd", "wip", "ready", "rejected", "duplicate"}
VALID_TYPE = {"strength", "hypertrophy"}
VALID_REGIME = {"weighted", "assisted", "bodyweight"}


# ── minimal YAML frontmatter parser ──────────────────────────────────────────
# Handles exactly what Obsidian's property editor writes: scalars (quoted or
# bare), flow lists [a, b], and block lists (- item per line). Anything more
# exotic is a schema violation we'd want to hear about anyway.
def parse_frontmatter(text, where):
    if not text.startswith("---"):
        raise ValueError(f"{where}: no frontmatter")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError(f"{where}: unterminated frontmatter")
    body = text[3:end].strip("\n")

    def scalar(v):
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            return v[1:-1].replace("''", "'") if v[0] == "'" else v[1:-1]
        if v == "true":  return True
        if v == "false": return False
        if v in ("null", "~", ""): return None
        if re.fullmatch(r"-?\d+", v): return int(v)
        return v

    data, key, lines = {}, None, body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][\w]*):\s*(.*)$", line)
        if m:
            key, rest = m.group(1), m.group(2).strip()
            if rest.startswith("[") and rest.endswith("]"):          # flow list
                inner = rest[1:-1].strip()
                data[key] = [scalar(x) for x in inner.split(",")] if inner else []
            elif rest.startswith("{") and rest.endswith("}"):        # flow map (rest overrides)
                inner = rest[1:-1].strip()
                obj = {}
                for pair in filter(None, (p.strip() for p in inner.split(","))):
                    k, _, v = pair.partition(":")
                    obj[k.strip()] = scalar(v)
                data[key] = obj
            elif rest == "":                                         # block list or empty
                block, j = [], i + 1
                while j < len(lines) and re.match(r"^\s*-\s+", lines[j]):
                    block.append(scalar(re.sub(r"^\s*-\s+", "", lines[j])))
                    j += 1
                data[key] = block if block else None
                i = j - 1
            else:
                data[key] = scalar(rest)
        i += 1
    return data


# ── classification vocabulary, read from index.html ─────────────────────────
def load_vocabulary(html):
    """Returns (ordered muscle-group keys, {muscle: {valid patterns}}).

    Order matters: it drives the generated file order (see sort_key), so the
    library groups by muscle the way MUSCLE_GROUPS itself is declared.
    """
    def obj_block(name):
        m = re.search(r"const " + name + r" = \{(.*?)\n\};", html, re.S)
        if not m:
            sys.exit(f"could not find {name} in index.html")
        return m.group(1)

    muscles = re.findall(r"^\s*(\w+):\s*'", obj_block("MUSCLE_GROUPS"), re.M)
    patterns = {}
    for line in obj_block("MOVEMENT_PATTERNS").split("\n"):
        m = re.match(r"\s*(\w+):\s*\{(.*?)\},?\s*$", line)
        if m:
            patterns[m.group(1)] = set(re.findall(r"(\w+):\s*'", m.group(2)))
    if not muscles or not patterns:
        sys.exit("failed to parse the classification vocabulary from index.html")
    return muscles, patterns


# ── load + validate ─────────────────────────────────────────────────────────
def load_notes(lib_dir, muscles, patterns):
    notes, errors, seen = [], [], {}
    for path in sorted(lib_dir.glob("*.md")):
        rel = path.name
        try:
            fm = parse_frontmatter(path.read_text(encoding="utf-8"), rel)
        except ValueError as e:
            errors.append(str(e))
            continue

        status = fm.get("status")
        if status not in VALID_STATUS:
            errors.append(f"{rel}: status {status!r} not one of {sorted(VALID_STATUS)}")
            continue
        if status != "ready":
            continue  # curated but not finished -- silently skipped, never shipped

        for f in REQUIRED:
            if f not in fm or fm[f] is None and f != "compound":
                errors.append(f"{rel}: missing required field '{f}'")
        if errors and errors[-1].startswith(rel):
            continue

        ex_id = fm["id"]
        if ex_id in seen:
            errors.append(f"{rel}: duplicate id '{ex_id}' (also in {seen[ex_id]})")
            continue
        seen[ex_id] = rel

        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(ex_id)):
            errors.append(f"{rel}: id '{ex_id}' must be a lowercase slug")
        if fm["type"] not in VALID_TYPE:
            errors.append(f"{rel}: type '{fm['type']}' invalid")
        if fm["regime"] not in VALID_REGIME:
            errors.append(f"{rel}: regime '{fm['regime']}' invalid")
        if fm["compound"] not in (True, False, None):
            errors.append(f"{rel}: compound must be true/false/null")

        muscle, pattern = fm["mainMuscle"], fm["movementPattern"]
        if muscle not in muscles:
            errors.append(f"{rel}: mainMuscle '{muscle}' not a real group")
        elif pattern not in patterns.get(muscle, set()):
            # the scoped-vocabulary rule: a biceps 'curl' and a hamstring
            # 'curl' are different patterns living under different groups
            errors.append(f"{rel}: pattern '{pattern}' does not belong to '{muscle}' "
                          f"(valid: {sorted(patterns.get(muscle, []))})")
        for acc in fm.get("accessoryMuscles") or []:
            if acc not in muscles or acc == "undefined":
                errors.append(f"{rel}: accessory '{acc}' not a real muscle group")

        notes.append(fm)
    return notes, errors


# ── emitters ────────────────────────────────────────────────────────────────
def build_library_json(notes):
    out = []
    for fm in notes:
        e = {f: fm[f] for f in REQUIRED}
        for f in OPTIONAL:
            v = fm.get(f)
            if v not in (None, "", [], {}):
                e[f] = v
        e.setdefault("accessoryMuscles", [])
        out.append(e)
    return json.dumps({"exercises": out}, ensure_ascii=False, indent=2) + "\n"


def build_seed_classification(notes):
    """The SEED_CLASSIFICATION literal for index.html (backfill lookup table)."""
    width = max(len(n["id"]) for n in notes) + 4
    lines = []
    for fm in notes:
        acc = ",".join(f"'{a}'" for a in fm.get("accessoryMuscles") or [])
        key = f"'{fm['id']}':".ljust(width)
        lines.append(f"  {key}['{fm['mainMuscle']}', '{fm['movementPattern']}', [{acc}]],")
    return "const SEED_CLASSIFICATION = {\n" + "\n".join(lines) + "\n};\n"


def build_catalog_sql(notes):
    rows = []
    for fm in notes:
        e = {f: fm[f] for f in REQUIRED}
        for f in OPTIONAL:
            v = fm.get(f)
            if v not in (None, "", [], {}):
                e[f] = v
        e.setdefault("accessoryMuscles", [])
        payload = json.dumps(e, ensure_ascii=False).replace("'", "''")
        rows.append(f"  ('{fm['id']}', '{payload}'::jsonb)")
    return ("-- GENERATED by tools/build-library.py -- do not edit by hand.\n"
            "insert into public.global_exercises (id, data) values\n"
            + ",\n".join(rows)
            + "\non conflict (id) do update set data = excluded.data, updated_at = now();\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate + diff only, write nothing")
    ap.add_argument("--vault", type=pathlib.Path, default=DEFAULT_VAULT)
    args = ap.parse_args()

    lib_dir = args.vault / "Exercise Library"
    if not lib_dir.is_dir():
        sys.exit(f"curated library folder not found: {lib_dir}")

    html = (REPO / "index.html").read_text(encoding="utf-8")
    muscles, patterns = load_vocabulary(html)
    notes, errors = load_notes(lib_dir, muscles, patterns)

    if errors:
        print(f"VALIDATION FAILED ({len(errors)} problem(s)):", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        sys.exit(1)
    if not notes:
        sys.exit("no notes with status: ready -- refusing to emit an empty library")

    # Deterministic, meaningful order: muscle group (as declared in
    # MUSCLE_GROUPS) -> movement pattern -> name. This IS the default display
    # order a fresh install sees in the Biblioteca, so grouping by muscle
    # beats both alphabetical-by-slug and the hand-curated order it replaces.
    order = {m: i for i, m in enumerate(muscles)}
    notes.sort(key=lambda n: (order.get(n["mainMuscle"], 99), n["movementPattern"], n["name"]))
    artifacts = {
        REPO / "library.json": build_library_json(notes),
        REPO / "supabase" / "03-catalog-seed.sql": build_catalog_sql(notes),
    }

    print(f"{len(notes)} ready exercises from {lib_dir}")
    drift = False
    for path, content in artifacts.items():
        cur = path.read_text(encoding="utf-8") if path.exists() else None
        same = cur is not None and json.loads(cur) == json.loads(content) \
            if path.suffix == ".json" else cur == content
        status = "unchanged" if same else ("WOULD CHANGE" if args.check else "written")
        if not same:
            drift = True
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        print(f"  {path.relative_to(REPO)}: {status}")

    # SEED_CLASSIFICATION lives inside index.html; compare, and rewrite in place
    # when regenerating (the block is delimited well enough to swap safely).
    seed_block = build_seed_classification(notes)
    m = re.search(r"const SEED_CLASSIFICATION = \{.*?\n\};\n", html, re.S)
    if not m:
        sys.exit("could not locate SEED_CLASSIFICATION in index.html")
    if m.group(0) == seed_block:
        print("  index.html SEED_CLASSIFICATION: unchanged")
    else:
        drift = True
        if args.check:
            print("  index.html SEED_CLASSIFICATION: WOULD CHANGE")
        else:
            (REPO / "index.html").write_text(html.replace(m.group(0), seed_block), encoding="utf-8")
            print("  index.html SEED_CLASSIFICATION: written")

    if args.check and drift:
        sys.exit("\ngenerated output differs from what is committed -- run without --check")
    print("\nOK" + (" (no changes)" if not drift else ""))


if __name__ == "__main__":
    main()
