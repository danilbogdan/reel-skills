# reel-skills

Skills for making short vertical videos (reels) from your own footage and notes. Each skill is a folder with a `SKILL.md`: when to use it, the steps, how to check the result, and what it will not do. Scripts are plain Python 3 or bash.

You bring the material: your clips, your reference videos (ones you have rights to view), and your notes. This repo holds only the methods and tools.

## Quick start

```bash
git clone <repo-url> reel-skills && cd reel-skills
scripts/doctor.sh                       # checks Python, ffmpeg and optional tools
scripts/run_demo.sh                     # runs the whole pipeline on a synthetic clip, prints "demo ok"
scripts/install.sh ~/.claude/skills     # optional: link the skills into your agent's skills folder
```

Setup details and what to prepare before using your own footage: [docs/setup.md](docs/setup.md).
How the skills fit together: [docs/workflow.md](docs/workflow.md).

## Skills

Three jobs: learn what works, make the video fast, find something worth saying.

| Skill | Job | What it does |
|---|---|---|
| [video-analysis](skills/video-analysis/SKILL.md) | learn | Analyzes a YouTube video or reel from a link: views and engagement, shots and cuts per minute, loudness, hook quote, frame per shot; compares several videos |
| [hook-lint](skills/hook-lint/SKILL.md) | learn | Checks a hook caption and first sentence; six hook shapes to write from |
| [pause-cut](skills/pause-cut/SKILL.md) | make | Plans removal of dead pauses, keeps breaths, never leaves one-second fragments |
| [reel-render](skills/reel-render/SKILL.md) | make | Cut list to a vertical 1080x1920 reel: zoom, warm grade, burned captions |
| [broll-index](skills/broll-index/SKILL.md) | make | Indexes your own b-roll and finds a clip by the word you say |
| [media-search](skills/media-search/SKILL.md) | make | Free music, sound effects, stock images and video from Pixabay, Freesound, Jamendo, with license and credit |
| [videogen](skills/videogen/SKILL.md) | make | One AI video clip from a prompt or your own frame (FLUX 3 video): shows the cost first, draft before full render |
| [notes-digest](skills/notes-digest/SKILL.md) | say | Your Markdown notes to story candidates and a pain, action, result table |

Each skill is one folder: a `SKILL.md` (when to use it, steps, how to verify, what it will not do) and scripts you
can run directly.

## Your notes

Notes are plain Markdown files in a `notes/` folder by default. Notion and Google Docs can be used too; each one ends up as the same folder of Markdown files. See [docs/notes.md](docs/notes.md).

## Privacy

Your footage and notes never go into this repo. `.gitignore` blocks media, `workspace/`, `notes/` and `.env`. Before sharing changes, run:

```bash
python3 scripts/audit_privacy.py
python3 scripts/validate_skills.py
```

## License

MIT. See [LICENSE](LICENSE). You may use, change and redistribute these skills, including commercially, if you keep the copyright notice.
