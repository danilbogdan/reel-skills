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
| yt-dlp | downloading a video from a link for `video-analysis` | `pip install yt-dlp` or `brew install yt-dlp` |
| Whisper (speech-to-text) | transcripts, finding words in a clip, automatic captions (`reel-render --transcribe` needs the `whisper` command) | `pip install openai-whisper` |
| Inter font | the thin caption look of `reel-render` (family "Inter Light") | https://rsms.me/inter/ (OFL), or `--fonts-dir` |
| pandoc | converting .docx notes to Markdown | `sudo apt install pandoc` or `brew install pandoc` |

A skill that needs something else lists it under `requires:` in its `SKILL.md` and explains it in its "Prepare" section.

## 3. Check your machine

```bash
scripts/doctor.sh
```

It prints OK or MISSING for each tool and exits non-zero if a required tool is missing.

## 4. Keys and accounts

Only `media-search` needs keys, and only for the sources you use. Export them in your shell (or keep them in a
`.env` file that git ignores); never paste a key into a file in this repo.

| Source | Variable | Where to get it |
|---|---|---|
| Pixabay (images, videos) | `PIXABAY_API_KEY` | https://pixabay.com/api/docs/ |
| Freesound (sound effects) | `FREESOUND_API_KEY` | https://freesound.org/apiv2/apply |
| Jamendo (music) | `JAMENDO_CLIENT_ID` | https://devportal.jamendo.com/ |

Every other skill needs no account.

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

```bash
scripts/run_demo.sh
```

It makes a 12-second synthetic clip (four scenes, a tone with pauses), then runs analysis, pause-cut, render and
hook-lint on it. It ends with `demo ok` when everything works. The sample has no people and no personal content.
Outputs are in `workspace/demo/` (git-ignored).
