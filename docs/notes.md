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

Two ways. Both end with Markdown files in `notes/`.

### A. Connect Notion to your agent with MCP (live)

Notion hosts an MCP server, so your agent can read your pages directly. Nothing to install and no token to paste:
you sign in with Notion (OAuth) and the agent sees only what your account can see.

Claude Code:

```bash
claude mcp add --transport http notion https://mcp.notion.com/mcp
```

Then run `/mcp` inside Claude Code and follow the sign-in flow. Add `--scope user` to make it available in all
projects, or `--scope project` to share the setup through `.mcp.json`. Other agents (Codex, Cursor and others) take
the same address, `https://mcp.notion.com/mcp`; `https://mcp.notion.com/sse` is a fallback for clients without
streamable HTTP. Details: https://developers.notion.com/docs/get-started-with-mcp

Then ask the agent to bring the notes into the folder the skills read:

> Find my daily notes from the last 7 days in Notion. Save each one as `notes/YYYY-MM-DD.md`, with the text exactly
> as written. Do not summarise or reword. Skip anything tagged private.

Then run `notes-digest` as usual. Pages the agent reads are sent to the model like any file you let it open, so
keep private pages out of reach (do not share them with the connection, or leave them out of the request).

### B. Export by hand (no connection)

1. In Notion, open the page or workspace, then use the export option and choose Markdown.
2. Put the exported files in `notes/`.
3. Keep the date in each page's title (`2026-10-12 ...`) so the file name carries it, or add a `date:` line in the
   frontmatter.

Re-export when you want skills to see newer notes.

## Google Docs

1. Open the document, then choose the Markdown download option (File, then Download, then Markdown, if your version has it).
2. If your version only offers .docx, convert it with pandoc: `pandoc notes.docx -t gfm -o notes/2026-10-12.md`.
3. Name each file with its date.

## Rules for every backend

- The end result is a folder of `.md` files, one per day or per entry, with the date in the name or frontmatter.
- Do not commit `notes/` to git. It is ignored by default.
- Notes are yours: skills read them but never publish or send them anywhere.
