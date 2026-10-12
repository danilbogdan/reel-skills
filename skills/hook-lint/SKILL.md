---
name: hook-lint
description: >-
  Checks the hook of a short video (the on-screen caption and the first spoken sentence) against simple rules
  and lists six hook shapes to write from. Use when you are writing or reviewing the first three seconds of a
  reel, when a video gets no views despite good editing, or when you need a quick pass before you shoot.
metadata:
  category: writing
  version: 0.1.0
  status: stable
  requires: [python3]
  origin: written from scratch
---

# Hook lint

**Outcome:** a PASS / WARN / FAIL list for your hook, and a clear idea of which of six shapes it follows.
The words stay yours; this checks length, openers and concreteness only.

## Prepare

- Your draft caption (what appears on screen) and, if you have it, the first spoken sentence.
- Read [references/hook-types.md](references/hook-types.md) once to pick a shape.

## Steps

1. Lint it:
   ```bash
   python3 skills/hook-lint/scripts/hook_lint.py "A clean kitchen in 15 minutes" \
     --spoken "It used to take me a whole evening."
   ```
2. Fix every FAIL first (too long, greeting opener). Then read the WARN lines and decide; a warning is a
   question, not an error.
3. Write two versions with one difference between them. Pick one by saying both aloud, or run both as trial posts.
4. Check the promise: list what the video delivers in the first ten seconds. If the hook promises more, change the hook.

## Verify

- The command exits 0 (no FAIL).
- You can name the hook shape from the table and the one thing the viewer learns if they stay.

## Will not do

- Write the hook for you or rewrite your script.
- Judge whether a claim is true; that is yours.
- Predict views.
