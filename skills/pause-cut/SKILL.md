---
name: pause-cut
description: >-
  Finds the dead pauses in a talking-head clip and writes a cut list that removes them while keeping short
  breaths and never putting two jump cuts close together. Use when you want to tighten a raw take, cut silences
  automatically, remove a stumbled word without leaving a choppy edit, or prepare a cut list before rendering a reel.
metadata:
  category: content-production
  version: 0.2.0
  status: stable
  requires: [ffmpeg, python3]
  origin: written from scratch
---

# Pause cut

**Outcome:** a `cuts.json` file listing the pieces of the clip to keep, and a printed summary of how many
seconds the cut removes. Nothing is rendered here; `reel-render` turns the list into a video.

Two rules sit behind it:

1. **The silence level is measured, not guessed.** The tool reads the loudness of the take and puts the threshold
   between the room noise and the voice, so a quiet evening voice is not taken for silence.
2. **Rhythm rule: no two cuts closer than `--min-piece` seconds (default 3.0).** When several pauses compete, the plan
   keeps the cuts that remove the most dead air and leaves the shorter pauses as they were. A single word between two
   pauses is therefore never cut out of both sides. The summary lists the pauses it left in place and why.

## Prepare

- A video with speech, for example `workspace/takes/take-01.mov`.
- Nothing else: `--noise auto` is the default. Set `--noise -25` only if a loud room still leaves pauses uncut.

## Steps

1. Plan the cuts:
   ```bash
   python3 skills/pause-cut/scripts/pause_cut.py workspace/takes/take-01.mov --out workspace/out/cuts.json
   ```
2. Read the summary: the threshold it measured, each kept piece with its start, end and length, and the pauses left
   in place by the rhythm rule.
3. Remove a stumble or a filler word yourself: take its time from the player (source seconds) and add it. The range
   is widened to the pauses on both sides, so it costs one cut, and it wins over automatic cuts it overlaps:
   ```bash
   python3 skills/pause-cut/scripts/pause_cut.py take-01.mov --out cuts.json --drop 12.4-12.9 --drop 31.0-31.6
   ```
4. Adjust if the result is wrong:
   - cuts clip the first or last word: raise `--keep-pause` (0.4).
   - pauses survive that should go: lower `--min-pause` (0.3), or lower `--min-piece` (2.0) to allow cuts closer together.
   - the result still feels choppy: raise `--min-piece` (4.0).
5. Open `cuts.json`. You can edit it by hand: change a start or end, delete a piece, or add `"zoom"` or `"grade"` to a
   piece (see `reel-render`).

## Verify

- `kept_seconds` is shorter than `duration`, and `shortest_piece` is at least `--min-piece`, except where you forced a
  `--drop`.
- Play the joins in the render; a join should not cut a word, and no two joins should fall within a few seconds.
- `python3 -m unittest discover -s tests` passes (the planning logic has unit tests).

## Will not do

- Edit or overwrite the original clip.
- Decide which sentences to keep; it only removes silence and the ranges you name. Choosing content is your job.
- Remove filler words by itself: that needs a transcript, so name them with `--drop`.
