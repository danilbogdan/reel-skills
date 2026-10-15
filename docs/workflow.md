# How the skills fit together

Making a reel that works comes down to three jobs. Each has a skill (or two), and they run in this order.

| Job | Question it answers | Skills |
|---|---|---|
| 1. Learn what works | How are reels in my niche built? | `video-analysis`, `hook-lint` |
| 2. Make the video fast | How do I get from raw take to a watchable reel without days of editing? | `pause-cut`, `reel-render`, `broll-index`, `media-search`, `videogen` |
| 3. Find something worth saying | What from my own life is worth a video? | `notes-digest` |

## One loop, start to finish

1. **Find the story.** `notes-digest` on last week's notes. Pick one row marked public.
2. **Write the hook.** Pick a shape from `hook-lint/references/hook-types.md`, write the caption and the first
   spoken sentence yourself, run `hook-lint`.
3. **Study three or more references.** `video-analysis` on videos and reels in your niche, then `compare`. Note the shot length and how the
   first three seconds open. Do not copy their words.
4. **Shoot.** Two takes of the hook and the call to action; one take per point. Name files `take-01.mov`.
5. **Cut.** `pause-cut` on each take (cuts are never closer than 3 s), check the pieces, name a stumble with `--drop`, edit
   `cuts.json` by hand where needed.
6. **Add pictures that match the words.** `broll-index search <word>` for your own clips;
   `media-search` for stock shots, sound effects and a music bed. Only for a shot you cannot film: `videogen`.
7. **Render.** `reel-render --transcribe`: voice cleaned and set to -14 LUFS, quiet captions burned in, a `check:` block
   printed. Read `reel.srt` once; fix words and render again with `--srt` only if something is wrong.
8. **Check before posting.** Watch it once with the sound off (captions carry it) and once with the sound on.

Steps 5 and 7 in one command: `scripts/make_reel.py take.mov --out workspace/out/reel.mp4 --language ru`.

## Reproduce it on your machine

```bash
scripts/doctor.sh
scripts/run_demo.sh
```

`run_demo.sh` makes a synthetic clip and runs video-analysis, pause-cut, render and hook-lint on it. If it prints
`demo ok`, the tools work and you can point the same commands at your own footage.

## What is deliberately not here

- Motion-graphics frameworks and background removal. Useful, but heavier to set up. Start with the loop above.
- Posting. Nothing here uploads or publishes; what it would take is in [publishing.md](publishing.md).
