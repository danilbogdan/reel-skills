---
name: reel-render
description: >-
  Renders a vertical 1080x1920 reel from a cut list: trims the pieces, crops to 9:16, adds a gentle zoom in and
  out, applies a warm grade, joins them and burns in captions from an SRT. Use when you have a cut list from
  pause-cut or written by hand and want a watchable draft, or when you want captions readable without sound.
metadata:
  category: content-production
  version: 0.1.0
  status: stable
  requires: [ffmpeg, python3, "whisper (optional, for captions)"]
  origin: written from scratch
---

# Reel render

**Outcome:** `reel.mp4`, 1080x1920, with hard cuts between pieces, a small zoom per piece, a warm grade and
optional burned-in captions.

## Prepare

- A cut list. Either one from `pause-cut`, or write your own (JSON, see below).
- Optional: an `.srt` file for captions (see step 3).

## The cut list

```json
{
  "source": "workspace/takes/take-01.mov",
  "segments": [
    {"start": 0.0, "end": 4.2},
    {"start": 6.0, "end": 9.5, "zoom": 0.1, "zoom_style": "out"},
    {"start": 0.0, "end": 3.0, "source": "workspace/broll/street.mp4", "zoom": 0, "grade": "none"}
  ]
}
```

Each piece can use its own `source`, so b-roll is just another piece. Use `broll-index` to find clips and
`media-search` to find music and sounds.

## Steps

1. Draft without captions:
   ```bash
   python3 skills/reel-render/scripts/render.py workspace/out/cuts.json --out workspace/out/draft.mp4
   ```
2. Watch it. Adjust the cut list or the look: `--zoom 0.1` for a stronger push, `--zoom-style in`,
   `--grade none` to turn the warm grade off, `--dry-run` to see the ffmpeg commands.
3. Captions: transcribe the draft (`whisper workspace/out/draft.mp4 --output_format srt --output_dir workspace/out`),
   fix wrong words in the `.srt`, then render again:
   ```bash
   python3 skills/reel-render/scripts/render.py workspace/out/cuts.json --out workspace/out/final.mp4 \
     --srt workspace/out/draft.srt
   ```
4. Add music last, under the voice: voice about 4 dB above the music, music ducked while someone speaks.

## Verify

- `ffprobe -v error -show_entries stream=width,height -of csv=p=0 final.mp4` prints `1080,1920`.
- The duration matches the sum of the pieces in the cut list.
- Captions match the spoken words; a caption never covers the face.

## Will not do

- Overwrite your source clips.
- Publish the reel or upload it anywhere.
- Fix a bad take; it only cuts, crops, zooms and grades.
