---
name: video-analysis
description: >-
  Analyzes a YouTube video, Short or Instagram reel from a link or a file: views and engagement numbers, shots
  and cuts per minute, loudness, speech rate, the transcribed hook, and one frame and colour per shot, then
  compares several videos side by side. Use when you want to study what works in your niche, take a reference
  apart before you make your own, or quote a hook accurately.
metadata:
  category: content-research
  version: 0.1.0
  status: stable
  requires: [ffmpeg, python3, "yt-dlp (for links)", "whisper (optional, for the hook)"]
  origin: written from scratch
---

# Video analysis

**Outcome:** for each video, a folder with `report.md` (numbers, edit rhythm, sound, hook, shot table),
`analysis.json`, one frame per shot, and the downloaded file. For several videos, one comparison table.

This is the "learn from what already works" step. One video is an observation; the pattern shows up when you
put three to ten videos from your niche side by side.

## Prepare

- ffmpeg, and yt-dlp for links: `pip install yt-dlp` (see [docs/setup.md](../../docs/setup.md)).
- Optional, for the hook words and speech rate: `pip install openai-whisper`.
- Public videos you want to study. Downloading is governed by each platform's terms; use this for private
  study and never re-upload what you download.
- If YouTube or Instagram refuses the download, export cookies from a logged-in browser to a `cookies.txt`
  file and pass `--cookies cookies.txt`. Keep that file out of the repo.

## Steps

1. Analyze one video (link or file):
   ```bash
   python3 skills/video-analysis/scripts/analyze.py run "https://www.youtube.com/watch?v=VIDEO_ID" \
     --out workspace/analysis/video-1 --transcribe
   ```
2. Read `workspace/analysis/video-1/report.md`: numbers first, then the shot table, then open the frames.
3. Repeat for at least three videos from your niche, ideally one strong and one weak performer.
4. Compare them:
   ```bash
   python3 skills/video-analysis/scripts/analyze.py compare workspace/analysis/video-1 workspace/analysis/video-2 workspace/analysis/video-3
   ```
5. Fill the "Your notes" section of each report, then write three rules for your own videos (hook shape, shot
   length, how often it cuts).

Notes on the numbers:
- Compare views only between videos of similar channel size; the report shows follower count when the platform gives it.
- Cuts per minute is measured from picture changes; a captions-only change or a zoom is not a cut.
- Instagram downloads are sometimes video only. The report says "NO AUDIO STREAM"; then the hook cannot be
  transcribed and you should say so instead of guessing from the frames.

## Verify

- `report.md` exists, and the shot count matches what you see when you scrub the video.
- The shot lengths add up to the duration.
- The hook line is a quote from the transcript, or says it was not transcribed.

## Will not do

- Download private, paid or age-restricted videos, or work around a platform's restrictions.
- Post, like, follow or otherwise act on any account.
- Explain why a video went viral; it measures, you interpret.
