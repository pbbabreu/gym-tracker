#!/usr/bin/env python3
"""Import free-exercise-db into the vault's Exercise Dump/ as raw material.

    python tools/import-dump.py --source path/to/exercises.json
    python tools/import-dump.py --source ... --dry-run

Source: github.com/yuhonas/free-exercise-db -- 873 exercises, **Unlicense
(public domain)**, the only major open exercise dataset with no license
strings attached (wger's catalog is CC-BY-SA, i.e. share-alike).

These notes are RAW MATERIAL, not content. Everything written here lands at
`status: tbd` in a folder the generator never reads, so nothing here can
reach the app. Promotion into Exercise Library/ is the review act: real
PT-BR name, real classification, real cues.

Rules this script follows so the dump stays honest:

  * Classification is MAPPED, never GUESSED. Their 17 muscle labels fold
    onto our 13 groups mechanically, and that mapping is recorded as a
    hint to be checked -- their taxonomy genuinely doesn't line up with
    ours (they split lats/middle back/lower back/traps where we have one
    "back"; they have "neck", we don't).
  * `movementPattern` is left UNSET. There is no pattern field upstream,
    and inferring one from an exercise name is exactly the kind of
    plausible-looking guess that would poison a library. The reviewer
    assigns it at promotion, where the generator will validate it belongs
    to its muscle group.
  * Re-runs PRESERVE triage verdicts (added 2026-08-02). Any existing note
    whose `status` is not `tbd` -- duplicate/rejected/wip, i.e. a human
    touched it -- is skipped, never overwritten. Without this, refreshing
    the dataset would wipe every triage stamp accumulated during L2.
  * A `sourceId` that already exists in the curated library is a CERTAIN
    duplicate (identity, not name similarity): flagged `status: duplicate`
    with a definitive pointer, no fuzzy matching involved. Name matching
    missed exactly this once -- the 2026-07-27 import ran before the first
    promotions existed, leaving two consumed originals unflagged in the
    triage queues (found 2026-08-02).
  * Name matching is BILINGUAL: dump names (English) are compared against
    each curated entry's `name`, `name_en` AND `aliases`. The curated
    library went PT-BR-primary on 2026-07-29, so matching `name` alone
    would score English dump names near zero and silently kill the
    dup-flagging on any re-run. Curated ids/names are read from the vault
    notes themselves, not library.json: library.json only carries `ready`
    entries and drops `sourceId` (app-irrelevant provenance), and a `wip`
    note mid-promotion must already flag its dump lookalikes.
"""
import argparse, json, pathlib, re, sys, difflib

REPO = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_VAULT = REPO.parent.parent / "Projects Vault" / "Gym Tracker"

# Their muscle vocabulary -> ours. Lossy on purpose; every one of these is a
# hint the reviewer confirms.
MUSCLE_MAP = {
    "quadriceps": "quads",
    "hamstrings": "hamstrings",
    "calves": "calves",
    "glutes": "glutes",
    "abductors": "glutes",      # our taxonomy files hip abduction under glutes
    "adductors": "adductors",   # ...but adductors are their own group (different nerve supply)
    "chest": "chest",
    "lats": "back",
    "middle back": "back",
    "lower back": "back",
    "traps": "back",            # AMBIGUOUS: upper traps read as shoulders, mid/lower as back
    "shoulders": "shoulders",
    "biceps": "biceps",
    "triceps": "triceps",
    "forearms": "forearms",
    "abdominals": "abs",
    "neck": None,               # no equivalent group -- left unclassified
}

EQUIPMENT_MAP = {
    "barbell": "barbell", "e-z curl bar": "barbell",
    "dumbbell": "dumbbell", "kettlebells": "kettlebell",
    "cable": "cable", "machine": "machine",
    "body only": "bodyweight", "bands": "band",
    "medicine ball": "other", "exercise ball": "other",
    "foam roll": "other", "other": "other",
}

# Categories a set/rep/load tracker can't really model -- imported anyway (the
# owner asked for the full dump) but called out so triage can bulk-reject.
OUT_OF_SCOPE = {"stretching", "cardio"}


def norm(s):
    s = re.sub(r"[^a-z0-9 ]", " ", str(s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def yaml_str(v):
    return "'" + str(v).replace("'", "''") + "'"


def read_frontmatter(path):
    """Minimal frontmatter reader for curated notes -- scalars and inline
    [lists] only, which covers every field this script needs (id, name,
    name_en, aliases, sourceId). Block-style lists (cues) are irrelevant
    here and parse as empty, which is fine."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    fm = {}
    if not m:
        return fm
    for line in m.group(1).splitlines():
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.split("  #")[0].strip()
        if val.startswith("[") and val.endswith("]"):
            fm[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
        else:
            fm[key] = val.strip("'\"")
    return fm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=pathlib.Path, required=True)
    ap.add_argument("--vault", type=pathlib.Path, default=DEFAULT_VAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads(args.source.read_text(encoding="utf-8"))

    # Curated identity + names come from the VAULT notes (the source of
    # truth), not library.json -- see the module docstring for why.
    # `existing` maps every normalized name/name_en/alias -> curated id
    # (bilingual fuzzy-match pool); `consumed` maps sourceId -> curated id
    # (identity: this dump entry has already been promoted).
    existing, consumed = {}, {}
    for note in sorted((args.vault / "Exercise Library").glob("*.md")):
        if note.stem == "_Template":
            continue
        fm = read_frontmatter(note)
        cid = fm.get("id")
        if not cid:
            continue
        if fm.get("sourceId"):
            consumed[fm["sourceId"]] = cid
        for cand in [fm.get("name"), fm.get("name_en"), *fm.get("aliases", [])]:
            c = norm(cand)
            if c:
                existing.setdefault(c, cid)

    out_dir = args.vault / "Exercise Dump"
    stats = {"written": 0, "dupes": 0, "unmapped": 0, "out_of_scope": 0,
             "preserved": 0, "consumed": 0}
    seen_files = set()

    for ex in data:
        name = ex.get("name") or ""
        if not name:
            continue

        # Filename bookkeeping FIRST (collision suffixes must stay
        # deterministic across runs -- every name registers in seen_files
        # whether or not the file gets written), then the preserve check:
        # a note a human already triaged (status != tbd) is never touched.
        safe = re.sub(r'[<>:"/\\|?*]', "-", name).strip()[:120]
        if safe.lower() in seen_files:          # names repeat across the source
            safe = f"{safe} ({ex.get('id','')[:8]})"
        seen_files.add(safe.lower())
        target = out_dir / f"{safe}.md"
        if target.exists():
            m = re.search(r"^status:\s*(\S+)", target.read_text(encoding="utf-8"), re.M)
            if m and m.group(1) != "tbd":
                stats["preserved"] += 1
                continue

        prim = [m for m in (ex.get("primaryMuscles") or [])]
        mapped = [MUSCLE_MAP.get(m) for m in prim]
        main_muscle = next((m for m in mapped if m), None)
        if not main_muscle:
            stats["unmapped"] += 1
        acc = []
        for m in (ex.get("secondaryMuscles") or []):
            v = MUSCLE_MAP.get(m)
            if v and v != main_muscle and v not in acc:
                acc.append(v)

        equipment = EQUIPMENT_MAP.get(ex.get("equipment"), "other" if ex.get("equipment") else None)
        regime = "bodyweight" if ex.get("equipment") == "body only" else "weighted"
        mechanic = ex.get("mechanic")
        compound = True if mechanic == "compound" else False if mechanic == "isolation" else None
        category = ex.get("category")
        if category in OUT_OF_SCOPE:
            stats["out_of_scope"] += 1

        # Identity beats similarity: a sourceId already in the curated
        # library means this exact entry WAS promoted -- no fuzzy matching,
        # no matchScore (a hand-assigned score would pretend the matcher
        # earned it).
        promoted_as = consumed.get(ex.get("id", ""))
        if promoted_as:
            stats["consumed"] += 1

        # Nearest existing library entry, so triage can spot "we already have
        # this" instead of promoting a second copy of something curated.
        # Whole-string similarity ALONE is too strict here: our curated names
        # are short ("Bench press") and theirs are long and qualified
        # ("Barbell Bench Press - Medium Grip"), which drags the ratio below
        # any sane threshold even though it's plainly the same lift. So a
        # containment check runs alongside it -- if every word of a curated
        # name appears in theirs, that's a match regardless of length.
        best_id, best_score = None, 0.0
        if not promoted_as:
            n = norm(name)
            n_words = set(n.split())
            for ename, eid in existing.items():
                score = difflib.SequenceMatcher(None, n, ename).ratio()
                e_words = set(ename.split())
                if e_words and e_words <= n_words:
                    score = max(score, 0.75 + 0.20 * len(e_words) / max(len(n_words), 1))
                if score > best_score:
                    best_id, best_score = eid, score
        is_dupe = best_score >= 0.72
        if is_dupe:
            stats["dupes"] += 1

        fm = [
            "---",
            f"status: {'duplicate' if promoted_as else 'tbd'}",
            f"name_en: {yaml_str(name)}",
            "source: free-exercise-db",
            f"sourceId: {yaml_str(ex.get('id',''))}",
            f"category: {category or 'unknown'}",
            f"level: {ex.get('level') or 'unknown'}",
            f"force: {ex.get('force') or 'unknown'}",
            f"equipment: {equipment or 'unknown'}",
            f"regime: {regime}",
            f"compound: {'true' if compound is True else 'false' if compound is False else 'null'}",
            f"mainMuscle: {main_muscle or 'undefined'}",
            f"accessoryMuscles: [{', '.join(acc)}]" if acc else "accessoryMuscles: []",
            "movementPattern: ''  # atribuído na promoção, nunca adivinhado aqui",
            f"sourceMuscles: [{', '.join(prim)}]" if prim else "sourceMuscles: []",
        ]
        if promoted_as:
            fm += [f"possibleDuplicateOf: {promoted_as}"]
        elif is_dupe:
            fm += [f"possibleDuplicateOf: {best_id}", f"matchScore: {best_score:.2f}"]
        if category in OUT_OF_SCOPE:
            fm.append("outOfScope: true")
        fm.append("---")

        warn = []
        if promoted_as:
            warn.append(f"> Já promovida para a biblioteca curada como **{promoted_as}** (mesma entrada da fonte — sourceId). Não promover de novo.")
        elif is_dupe:
            warn.append(f"> Parece já existir na biblioteca curada como **{best_id}** (semelhança {best_score:.0%}). Confira antes de promover.")
        if category in OUT_OF_SCOPE:
            warn.append(f"> Categoria **{category}** — o app registra séries/reps/carga, então isto provavelmente não se aplica.")
        if not main_muscle:
            warn.append(f"> Sem grupo muscular equivalente na nossa taxonomia (origem: {', '.join(prim) or '—'}).")

        instructions = ex.get("instructions") or []
        body = f"""
# {name}

> [!warning] Material bruto — não curado
> Classificação **mapeada automaticamente** a partir de outra taxonomia: trate como ponto de partida, não como verdade. `movementPattern` foi deixado em branco de propósito — atribua na promoção.
{chr(10).join(warn)}

## Instruções originais (inglês, fonte)

{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(instructions)) or '_(sem instruções na fonte)_'}

## Curadoria

- [ ] Nome em PT-BR (+ `name_en` já preenchido, vira alias)
- [ ] Grupo muscular conferido · padrão de movimento atribuído
- [ ] `movement` atribuído — reusar uma nota de `Movements/` ou criar (e `family:` na nota do movimento, onde existir)
- [ ] Tipo (força/hipertrofia) e composto/isolado revisados
- [ ] 2–3 dicas + 1–2 erros comuns, nas duas línguas
- [ ] `id` slug definido → mover para `Exercise Library/` com `status: wip`
"""
        if not args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(fm) + body, encoding="utf-8")
        stats["written"] += 1

    print(f"{'DRY RUN — ' if args.dry_run else ''}{stats['written']} entries -> {out_dir}")
    print(f"  preserved (status != tbd, human triage wins):      {stats['preserved']}")
    print(f"  consumed by promotion (sourceId already curated):  {stats['consumed']}")
    print(f"  flagged as possible duplicates of curated entries: {stats['dupes']}")
    print(f"  flagged out of scope (stretching/cardio):          {stats['out_of_scope']}")
    print(f"  no equivalent muscle group in our taxonomy:        {stats['unmapped']}")


if __name__ == "__main__":
    main()
