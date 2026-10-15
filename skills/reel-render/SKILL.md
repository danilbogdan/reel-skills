---
name: reel-render
description: >-
  Renders a vertical 1080x1920 reel from a cut list: trims the pieces, crops to 9:16, hides the jump cuts with a
  small still punch-in, warm grade, cleans the voice and sets it to -14 LUFS, and burns in quiet captions (thin
  font, no animation), with a pre-post check. Use when you have a cut list from pause-cut or written by hand and
  want a reel ready to post, or captions generated automatically.
metadata:
  category: content-production
  version: 0.2.0
  status: stable
  requires: [ffmpeg, python3, "whisper (optional, for automatic captions)", "Inter font (optional, for the caption look)"]
  origin: written from scratch
---

# Reel render

**Outcome:** `reel.mp4`, 1080x1920, with hard cuts between pieces, a still alternation between full frame and a 7 percent
punch-in so a cut reads as a change of shot, a warm grade, a clean voice at -14 LUFS, and optional captions. A
`check:` block is printed at the end.

Defaults follow the creator's brief: **clean frames, thin readable captions, nothing moves that does not have to.**
Captions are Inter Light 52 px, white with a soft dark halo (contrast on any background, no hard outline), two lines
at most, no pop, no colour change, no animation, placed above the area the app covers.

## Prepare

- A cut list. Either one from `pause-cut`, or write your own (JSON, see below).
- For automatic captions: the `whisper` command (see `docs/setup.md`). For the thin look: the Inter font installed
  (or `--fonts-dir` pointing at it). Without it the render warns and falls back to a heavier default font.

## The cut list

```json
{
  "source": "workspace/takes/take-01.mov",
  "segments": [
    {"start": 0.0, "end": 4.2},
    {"start": 6.0, "end": 9.5, "zoom": 0.1},
    {"start": 0.0, "end": 3.0, "source": "workspace/broll/street.mp4", "zoom": 0, "grade": "none"}
  ]
}
```

Each piece can use its own `source`, so b-roll is just another piece. Use `broll-index` to find clips and
`media-search` to find music and sounds.

## Steps

1. One command with captions (Whisper runs on the finished voice, so the captions match the cut):
   ```bash
   python3 skills/reel-render/scripts/render.py workspace/out/cuts.json --out workspace/out/reel.mp4 \
     --transcribe --language ru
   ```
   Without `--transcribe` you get the reel without captions; with `--srt my.srt` (or a Whisper `.json`) you caption from a
   file you control. `--transcribe` also writes `reel.srt` next to the reel.
2. Read the `check:` block. `WARN` lines are not errors; they say what to look at: a source below 1080x1920 (soft
   picture), loudness far from the target, two cuts close together, a missing font.
3. Read `reel.srt` once. Whisper can mishear names and terms. Fix the words, then render again with `--srt reel.srt`.
4. Looks: `--zoom 0` for no punch-in, `--zoom-style alternate` for the old slow push, `--grade none` for natural colour,
   `--caption-style bold` for the old heavy captions, `--dry-run` to see the ffmpeg commands.
5. Voice: `--audio auto` (default) picks a light chain (high-pass, a little mud removed, a little presence, gentle
   compression) or a full one (adds denoise, de-click, soft gate) from the room noise. `--audio none` leaves the voice
   untouched; `--lufs -16` changes the target.
6. Add music last, under the voice: voice about 4 dB above the music, music ducked while someone speaks.

The whole path from a raw take, in one command: `python3 scripts/make_reel.py take.mov --out workspace/out/reel.mp4 --language ru`.

## Verify

- The `check:` block shows 1080x1920, loudness within 1 LU of the target, peak at or under -1.0 dBFS.
- The duration matches the sum of the pieces in the cut list.
- Captions match the spoken words; a caption never covers the face.

## Will not do

- Overwrite your source clips.
- Publish the reel or upload it anywhere (see `docs/publishing.md` for what that needs).
- Fix a bad take: it cannot add energy to a flat start, remove a mumble, or sharpen a front-camera picture. It only cuts,
  crops, grades, cleans and levels.
