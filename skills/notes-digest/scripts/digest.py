#!/usr/bin/env python3
"""Turn a folder of Markdown notes into a digest of story candidates, and a table to fill in.

Usage:
  digest.py NOTES_DIR --out digest.md [--since YYYY-MM-DD] [--until YYYY-MM-DD]
            [--markers markers.txt] [--private-words private.txt]

What it does:
  * reads every .md file under NOTES_DIR; the date comes from `date:` in the frontmatter or from a file name
    that starts with YYYY-MM-DD;
  * skips any folder named private or _private;
  * prints, per note, the lines that contain a marker word (problem, stuck, decided, learned, ...), verbatim,
    with line numbers;
  * drops lines that contain a word from --private-words;
  * ends with an empty "pain -> what I did -> result" table for you (or your assistant) to fill with QUOTES.
It never summarises, never invents results, and never sends your notes anywhere. Standard library only.
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

DEFAULT_MARKERS = [
    "problem", "stuck", "hard", "difficult", "struggl", "frustrat", "decided", "realized", "learned", "lesson",
    "finally", "fixed", "solved", "worked", "didn't work", "failed", "mistake", "afraid", "procrastinat",
    "проблем", "сложно", "трудно", "застр", "решил", "понял", "урок", "наконец", "получилось",
    "не получилось", "ошибк", "боюсь", "исправил", "откладыв", "прокрастин",
]


def read_markers(path, default):
    if not path:
        return default
    return [l.strip().lower() for l in Path(path).read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def note_date(path, text):
    m = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    s = m.group(1) if m else (re.match(r"(\d{4}-\d{2}-\d{2})", path.name) or [None, None])[1]
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def title_of(path, text):
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else path.stem


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notes_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--markers", help="file with one marker word per line (replaces the default list)")
    ap.add_argument("--private-words", help="file with words; lines containing them are dropped")
    args = ap.parse_args()

    root = Path(args.notes_dir)
    if not root.is_dir():
        sys.exit(f"error: {root} is not a folder")
    since = date.fromisoformat(args.since) if args.since else date.min
    until = date.fromisoformat(args.until) if args.until else date.max
    markers = read_markers(args.markers, DEFAULT_MARKERS)
    private = read_markers(args.private_words, [])

    notes, undated, skipped_private = [], [], 0
    for p in sorted(root.rglob("*.md")):
        if {"private", "_private"} & set(p.relative_to(root).parts):
            skipped_private += 1
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        d = note_date(p, text)
        if d is None:
            undated.append(p)
            continue
        if not since <= d <= until:
            continue
        hits = []
        for n, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if any(w in low for w in private):
                continue
            if any(m in low for m in markers):
                hits.append((n, line.strip()))
        notes.append((d, p, title_of(p, text), len(text.split()), hits))
    notes.sort(key=lambda x: x[0])

    out = [f"# Notes digest {args.since or '...'} to {args.until or '...'}", "",
           f"{len(notes)} notes in range, {sum(1 for n in notes if n[4])} with marker lines, "
           f"{len(undated)} undated (skipped), {skipped_private} in private folders (skipped).", "",
           "Lines below are quoted exactly from your notes. Use them as evidence: do not add facts that are not "
           "in the notes.", ""]
    for d, p, title, words, hits in notes:
        out.append(f"## {d.isoformat()}  {title}")
        out.append(f"`{p.relative_to(root)}`, {words} words")
        if hits:
            out += [f"- line {n}: {l}" for n, l in hits[:12]]
        else:
            out.append("- (no marker lines)")
        out.append("")
    out += ["## Pairs to fill in", "",
            "One row per story. Quote the notes; leave a cell empty rather than guess.", "",
            "| Pain or need (quote) | What I did (quote) | Result (quote) | Source note | Privacy: public / private / never |",
            "|---|---|---|---|---|",
            "|  |  |  |  |  |", "|  |  |  |  |  |", "|  |  |  |  |  |"]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(notes)} notes, {sum(len(n[4]) for n in notes)} marker lines -> {args.out}")


if __name__ == "__main__":
    main()
