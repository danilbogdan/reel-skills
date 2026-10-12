---
name: skill-name-here
description: >-
  One or two sentences, third person: what the skill does and when to use it, with the words a user would say.
metadata:
  category: content-production
  version: 0.1.0
  status: draft
  requires: [ffmpeg, python3]
  origin: written from scratch
---

# Skill title

**Outcome:** what the user has at the end, and how to check it in one line.

## Prepare

- What the user must have before starting: footage in `workspace/takes/`, notes in `notes/`, a key in `.env`.
- Nothing personal ships with the skill. Say where each input goes.

## Steps

1. First mechanical step, with the exact command (`python3 scripts/<name>.py --help` for options).
2. Next step.
3. Decision points: say what the user decides and what the default is.

## Verify

- A file that must exist, for example `workspace/out/<name>.mp4`.
- A number that must be in range, for example duration within 2 seconds of the target.
- A command that must exit 0.

## Will not do

- Publish, post or send anything to anyone.
- Spend money or call a paid service without the user saying so.
- Delete or overwrite input files.
