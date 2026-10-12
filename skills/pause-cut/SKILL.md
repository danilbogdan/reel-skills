---
name: pause-cut
description: >-
  Finds the dead pauses in a talking-head clip and writes a cut list that removes them while keeping short
  breaths and never leaving one-second fragments. Use when you want to tighten a raw take, cut silences
  automatically, or prepare a cut list before rendering a reel.
metadata:
  category: content-production
  version: 0.1.0
  status: stable
  requires: [ffmpeg, python3]
  origin: written from scratch
---

# Pause cut

**Outcome:** a `cuts.json` file listing the pieces of the clip to keep, and a printed summary of how many
seconds the cut removes. Nothing is rendered here; `reel-render` turns the list into a video.

Rule behind it: do not cut every silence. If cutting a pause would leave a piece of about one second, the pause
stays, so the finished reel is made of runs of a few seconds, not choppy fragments.

## Prepare

- A video with speech, for example `workspace/takes/take-01.mov`.
- Know the noise level: a quiet room works with the default `-30` dB; a noisy room needs `-25` or higher.

## Steps

1. Plan the cuts:
   ```bash
   python3 skills/pause-cut/scripts/pause_cut.py workspace/takes/take-01.mov --out workspace/out/cuts.json
   ```
2. Read the summary. Each line is a kept piece with its start, end and length.
3. Adjust if the result is wrong:
   - cuts clip the first or last word: raise `--keep-pause` (0.4).
   - pauses survive that should go: lower `--min-pause` (0.3) or raise `--noise` (-25).
   - the result feels choppy: raise `--min-piece` (1.5).
4. Open `cuts.json`. You can edit it by hand: change a start or end, delete a piece, or add `"zoom"` or `"grade"` to a
   piece (see `reel-render`).

## Verify

- `kept_seconds` is shorter than `duration`, and every piece is at least `--min-piece` long except possibly one.
- Play the pieces' joins in the render; a join should not cut a word.

## Will not do

- Edit or overwrite the original clip.
- Decide which sentences to keep; it only removes silence. Choosing content is your job.
