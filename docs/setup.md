# Setup

## 1. Required tools

| Tool | Why | Check |
|---|---|---|
| Python 3.10 or newer | every script | `python3 --version` |
| ffmpeg (includes ffprobe) | cutting, probing and rendering video | `ffmpeg -version` |

Install on Ubuntu or Debian: `sudo apt install ffmpeg python3`
Install on macOS with Homebrew: `brew install ffmpeg python`
On Windows, use WSL and follow the Ubuntu line.

## 2. Optional tools

| Tool | Needed for | Install |
|---|---|---|
| Whisper (speech-to-text) | transcripts, finding words in a clip | `pip install openai-whisper`, or whisper.cpp |
| pandoc | converting .docx notes to Markdown | `sudo apt install pandoc` or `brew install pandoc` |

A skill that needs something else lists it under `requires:` in its `SKILL.md` and explains it in its "Prepare" section.

## 3. Check your machine

```bash
scripts/doctor.sh
```

It prints OK or MISSING for each tool and exits non-zero if a required tool is missing.

## 4. Keys and accounts

The base repo needs no API keys and no accounts. A skill that uses an online service says so in its "Prepare" section, and keeps the key in a `.env` file (ignored by git) or an environment variable. Never paste a key into a skill or a note.

## 5. Prepare your material

Create these folders (all git-ignored):

```
workspace/
  reference/      reference reels you analyse (only ones you have the right to view)
  takes/          your own footage, one file per take
notes/            your notes, one Markdown file per day (see docs/notes.md)
```

Use plain file names such as `take-01.mov`. Keep the originals; skills write their output next to the input or into `workspace/out/`.

## 6. Reproduce with the sample first

Before using your own footage, run the sample to confirm the tools work:

```bash
scripts/make_sample.sh
ffprobe -v error -show_entries format=duration -of csv=p=0 samples/sample.mp4
```

The sample is a 10-second test pattern with a tone. It has no people and no personal content.
