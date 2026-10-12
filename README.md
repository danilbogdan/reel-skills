# reel-skills

Skills for making short vertical videos (reels) from your own footage and notes. Each skill is a folder with a `SKILL.md`: when to use it, the steps, how to check the result, and what it will not do. Scripts are plain Python 3 or bash.

You bring the material: your clips, your reference videos (ones you have rights to view), and your notes. This repo holds only the methods and tools.

## Quick start

```bash
git clone <repo-url> reel-skills && cd reel-skills
scripts/doctor.sh                       # checks Python, ffmpeg and optional tools
scripts/make_sample.sh                  # makes a synthetic test clip in samples/ (no personal media)
scripts/install.sh ~/.claude/skills     # optional: link the skills into your agent's skills folder
```

Full setup, including what to prepare before a skill can run: [docs/setup.md](docs/setup.md).

## Skills

None published yet. Each skill will be listed here with a one-line description once it is ready.

## Your notes

Notes are plain Markdown files in a `notes/` folder by default. Notion and Google Docs can be used too; each one ends up as the same folder of Markdown files. See [docs/notes.md](docs/notes.md).

## Privacy

Your footage and notes never go into this repo. `.gitignore` blocks media, `workspace/`, `notes/` and `.env`. Before sharing changes, run:

```bash
python3 scripts/audit_privacy.py
python3 scripts/validate_skills.py
```

## License

Not chosen yet. Until a LICENSE file is added, all rights are reserved.
