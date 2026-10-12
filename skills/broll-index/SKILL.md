---
name: broll-index
description: >-
  Builds a searchable index of your own b-roll clips (duration, size, orientation, tags from file names) and
  finds clips by word. Use when you have a folder of footage you want to reuse, when an edit needs a shot that
  matches a spoken word, or when you keep losing track of what you already filmed.
metadata:
  category: content-production
  version: 0.1.0
  status: stable
  requires: [ffprobe, python3]
  origin: written from scratch
---

# B-roll index

**Outcome:** `index.json` listing every clip with its length, size and tags, and a search command that returns
the clips matching a word. The point: when you say a word in the video, you can find a shot that shows it.

## Prepare

- A folder of your own clips, for example `workspace/broll/`.
- Name files and folders by what is in them: `workspace/broll/cafe/window-rain.mp4`,
  `workspace/broll/city/night-walk.mp4`. The names become the tags.

## Steps

1. Build the index:
   ```bash
   python3 skills/broll-index/scripts/broll.py index workspace/broll --out workspace/broll/index.json
   ```
2. Search by the word you say in the edit:
   ```bash
   python3 skills/broll-index/scripts/broll.py search --index workspace/broll/index.json rain --min-seconds 3 --portrait
   ```
3. For clips you will reuse, open `index.json` and fill in `"description"` with one plain sentence.
   Re-indexing keeps what you wrote.
4. Put the chosen paths into your cut list (`reel-render` accepts a `source` per piece).

Rule for b-roll: it has to match the words said at that moment. A random pretty shot weakens the edit.

## Verify

- The clip count equals the number of video files in the folder.
- A search for a word in a file name returns that file.

## Will not do

- Change, move or rename your clips.
- Guess what is in a clip from its pixels; tags come from names and descriptions you write.
