---
name: media-search
description: >-
  Searches and downloads free images, video clips, sound effects and music from Pixabay, Freesound and Jamendo,
  and saves each file with its license and credit. Use when an edit needs a music bed, a sound effect or a stock
  shot, or when you want to compare free tracks by genre without browsing three websites.
metadata:
  category: content-production
  version: 0.1.0
  status: experimental
  requires: [python3, "PIXABAY_API_KEY, FREESOUND_API_KEY, JAMENDO_CLIENT_ID (the ones you use)"]
  origin: written from scratch
---

# Media search

**Outcome:** a shortlist for a query, and downloaded files, each with a `.json` next to it holding the license,
the credit line and the item page.

## Prepare

Get a free key for each source you want, and export it in your shell (never save a key inside this repo):

| Source | Serves | Key |
|---|---|---|
| Pixabay | images, videos | https://pixabay.com/api/docs/ (`PIXABAY_API_KEY`) |
| Freesound | sound effects | https://freesound.org/apiv2/apply (`FREESOUND_API_KEY`) |
| Jamendo | music | https://devportal.jamendo.com/ (`JAMENDO_CLIENT_ID`) |

Pixabay's API covers images and videos only. Pixabay music has to be downloaded by hand from its website.

## Steps

1. Search:
   ```bash
   python3 skills/media-search/scripts/media.py search jamendo "ambient" --instrumental --limit 10
   python3 skills/media-search/scripts/media.py search freesound "whoosh"
   python3 skills/media-search/scripts/media.py search pixabay-video "ocean waves"
   ```
2. Read the license column. Pick by license first, taste second: if you monetise or take sponsors, avoid NC
   (non-commercial) and ND (no derivatives); CC BY needs a credit in the post.
3. Download:
   ```bash
   python3 skills/media-search/scripts/media.py get jamendo 1234567 --out workspace/music
   ```
4. Keep the `.json` next to the file. Copy the `credit` line into your post when the license asks for it.
5. Put music under the voice: about 12 dB lower while someone speaks.

## Verify

- The saved file plays and its `.json` has a license.
- You can say, for each file you use, which license it is under and where you got it.

## Will not do

- Bulk-download a site. Pixabay forbids systematic mass downloads, and results are cached for 24 hours.
- Decide whether a license suits you; it shows what the source reports.
- Store keys or commit downloaded media.
