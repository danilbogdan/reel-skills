---
name: videogen
description: >-
  Makes a short AI video clip with FLUX 3 video from a prompt or from one of your own frames, showing the cost
  first and using a cheap draft before a full render. Use when an edit needs an insert you cannot film, such as
  a hand gesture or a background shot, and you want it to look like the same person and place.
metadata:
  category: content-production
  version: 0.1.0
  status: experimental
  requires: [python3, ffmpeg, "BFL_API_KEY (paid Black Forest Labs account)"]
  origin: written from scratch
---

# Videogen

**Outcome:** one short clip (5 to 20 seconds) saved to disk, made from your own frame when possible, after you
saw what it would cost.

AI video is the last resort for an insert, not the base of a reel. Real footage first; generate only the shot you
cannot film.

## Prepare

- A paid account and key from Black Forest Labs (https://docs.bfl.ai). Export it: `export BFL_API_KEY=...`.
  Never save it in a file in this repo.
- For a clip that looks like you, a frame from your own take. A prompt alone invents a stranger.

## Steps

1. Grab a starting frame from your own video:
   ```bash
   python3 skills/videogen/scripts/videogen.py frame workspace/takes/take-01.mov --at 8.0 --out workspace/gen/frame.png
   ```
2. See the request and the cost first (nothing is spent yet):
   ```bash
   python3 skills/videogen/scripts/videogen.py generate --image workspace/gen/frame.png --draft \
     --prompt "Same person, same room, same camera. He raises his right hand toward the lens and holds up one finger for two seconds, then lowers it. One continuous shot, no cuts, no text." \
     --out workspace/gen/insert-draft.mp4
   ```
3. Submit the draft: repeat the command with `--yes`. It polls until ready and downloads the file. Judge it on
   whether the action is readable and the person looks right; a draft is soft by design.
4. If the idea works, run again without `--draft` (add `--resolution fhd` only if you need it).
5. Cut exactly the second you need in your edit; the rest is wasted. Use it as one piece in a `reel-render` cut list.

## Writing the prompt

- One readable action per clip. Say what stays the same (same person, room, camera, framing) and what changes.
- Say "one continuous shot, no cuts, no text, no new objects".
- Change one thing between attempts. After two similar misses, rewrite the idea instead of adding adjectives.

## Verify

- The saved file plays, and its length matches `--seconds`.
- Check frame by frame: the person is recognisably the same, hands have the right number of fingers, no garbled text.
  Generated hands are the most common failure; reject the clip rather than hope nobody counts.
- You know what it cost (printed after submit as the reported cost).

## Will not do

- Spend money without `--yes`.
- Use a real person's likeness other than your own, or imitate a brand or a living creator's work.
- Hide that a clip is generated if your audience or platform expects disclosure.
