# Conventions (for the maintainer)

Every skill here must be useful to a stranger who clones the repo, and safe to publish. The same layout and frontmatter as the private skills repo, so skills can be exported across.

## Layout

```
skills/<skill-name>/
  SKILL.md              required; the entry point, 500 lines at most
  references/*.md       optional; long material, linked from SKILL.md
  scripts/*             optional; runnable helpers with --help
  templates/*           optional; files the skill copies or fills in
  assets/*              optional; small static files, under 1 MB each
```

- `<skill-name>` is lowercase kebab-case and equals `name:` in the frontmatter.
- Folders starting with `_` (such as `_template`) are not skills and are skipped by the validator.
- No nesting beyond the layout above.

## SKILL.md frontmatter

```yaml
---
name: reel-cut-draft
description: >-
  Third person, one or two sentences: what it does and when to use it, with the words a user would say.
metadata:
  category: content-production   # reflection | content-research | content-production | writing
  version: 0.1.0
  status: draft                  # draft | stable | experimental
  requires: [ffmpeg, python3]    # tools or accounts; empty list if none
  origin: written from scratch   # or: adapted from <url> (license)
---
```

## Writing a skill

- Start with **when to use** and the **outcome**, then the steps. Imperative voice.
- Put a mechanical step in a script, not in prose: parsing, batching, validating, rendering.
- Every skill has a **Verify** section (a file that must exist, a number in range, or a command that must exit 0) and a **Will not do** section (publishing, spending money, deleting, sending anything to anyone without a human asking).
- Long tables and examples go to `references/`.

## Scripts

- Shebang, `--help`, non-zero exit on failure, no interactive prompts, no network unless the skill says so.
- Read paths and keys from flags or environment variables, never from a personal path.
- Standard library only where possible. Print where the output went.

## Privacy (hard rules)

1. No secrets, keys, tokens, client IDs or secrets, passwords, cookies, internal URLs or IPs.
2. No real names, handles, employers, addresses, phone numbers or emails, except in `.privacy-denylist.local` (ignored).
3. No personal footage, notes, transcripts or renders, in the repo or in examples.
4. No absolute personal paths. Use `~/`, `$VAR` or flags.
5. Do not copy third-party skills or text. List third-party tools in `THIRD_PARTY.md` with source and license.
6. Provenance (which private material a skill was generalised from) goes in `docs/provenance/`, which is git-ignored. Never in a public file.

Before reporting a change as done, run:

```bash
python3 scripts/audit_privacy.py
python3 scripts/validate_skills.py
```

## Notes backends

Skills read notes only from a folder of Markdown files (see `docs/notes.md`). A skill never talks to Notion or Google directly in the base repo.

## License

Not chosen yet. Decide before the first public release, and add LICENSE, then update README.
