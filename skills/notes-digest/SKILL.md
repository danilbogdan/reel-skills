---
name: notes-digest
description: >-
  Reads your own Markdown notes (daily notes, exported Notion or Google Docs) and builds a digest of story
  candidates: the lines where you hit a problem, decided something, learned something, with an empty table to turn
  them into pain, action and result pairs. Use when you do not know what to make videos about, want content
  ideas from your real life, or want to reflect on a week of notes.
metadata:
  category: reflection
  version: 0.1.0
  status: stable
  requires: [python3]
  origin: written from scratch
---

# Notes digest

**Outcome:** `digest.md` with your notes for a date range, the marker lines quoted exactly, and a table where each
row is one story: what hurt, what you did, what happened, and whether it can be public.

The idea: the videos worth making are things you already lived. A week of notes holds several. This finds them
without sending your notes anywhere.

## Prepare

- Notes as Markdown files in `notes/`, one per day (`2026-10-12.md`). Notion: connect it to your agent with MCP and
  have the agent save pages as Markdown, or export by hand. Google Docs: export to Markdown. See
  [docs/notes.md](../../docs/notes.md).
- Optional: move anything you never want considered into `notes/private/` (it is always skipped).
- Optional: a text file of words to drop lines on (names, places), one per line.

## Steps

1. Build the digest for the last week:
   ```bash
   python3 skills/notes-digest/scripts/digest.py notes --since 2026-10-05 --until 2026-10-12 --out workspace/out/digest.md
   ```
2. Read it. For each interesting day, open the full note: the marker line is only a pointer.
3. Fill the table by hand, or ask your assistant to propose rows from the quoted lines only. Rules for rows:
   - every cell is a quote or empty; never an invented result;
   - mark Privacy for each row: public, private (shape it before sharing) or never;
   - one story per row.
4. Choose one public row. That is a video: the pain is the hook, the action is the body, the result is the end.
   Continue with `hook-lint`.

## Verify

- Every quoted line exists in the note at the line number shown.
- No line containing a word from your private list appears in the digest.
- Each row you plan to use has a source note and a privacy mark.

## Will not do

- Summarise or rewrite your notes.
- Send notes to any service. It reads files and writes one file.
- Decide what is safe to share; the Privacy column is yours.
