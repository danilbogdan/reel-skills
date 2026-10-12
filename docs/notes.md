# Notes

Skills read notes from one place: a folder of Markdown files. Every notes backend ends up as that folder, so adding a backend never changes a skill.

## Default: Markdown in `notes/`

- One file per day: `notes/2026-10-12.md`. The date in the file name is the key.
- Optional frontmatter at the top of a file:

  ```yaml
  ---
  date: 2026-10-12
  tags: [work, reel]
  ---
  ```

- Works with any editor, with Obsidian (point it at the `notes/` folder), and with git.

## Notion

Notion has no direct connection in the base repo. Export instead:

1. In Notion, open the page or workspace you want, then use the export option and choose Markdown.
2. Put the exported files in `notes/`.
3. Keep the date in each page's title (`2026-10-12 ...`) so the file name carries it, or add a `date:` line in the frontmatter.

Re-export when you want skills to see newer notes. A live Notion connection is not supported yet.

## Google Docs

1. Open the document, then choose the Markdown download option (File, then Download, then Markdown, if your version has it).
2. If your version only offers .docx, convert it with pandoc: `pandoc notes.docx -t gfm -o notes/2026-10-12.md`.
3. Name each file with its date.

## Rules for every backend

- The end result is a folder of `.md` files, one per day or per entry, with the date in the name or frontmatter.
- Do not commit `notes/` to git. It is ignored by default.
- Notes are yours: skills read them but never publish or send them anywhere.
