# Publishing from the flow: what it needs

Status: **not built, on purpose.** Nothing in this repo uploads or publishes. This page lists what has to exist
before a `publish` step can be added, so you can decide and prepare it once. Facts about the platform APIs are from
the vendors' documentation (linked) and change; check them when you start.

The target: `scripts/make_reel.py` writes `reel.mp4` plus the caption text, and a separate, explicit command
(`publish --confirm`) posts it. A dry run prints exactly what would be sent. Publishing is public and cannot be
undone quietly, so it is never part of the default run.

## Instagram (Reels)

Official route: the [Instagram Platform content publishing API](https://developers.facebook.com/docs/instagram-platform/content-publishing).
Two calls: create a container (`POST /<IG_ID>/media` with `media_type=REELS`, `video_url`, `caption`), wait until its
status is `FINISHED`, then `POST /<IG_ID>/media_publish`.

What you need to provide:

| Need | Detail |
|---|---|
| Account type | A Professional account (Business or Creator). A personal account cannot publish through the API. |
| Meta developer app | Created once at developers.facebook.com, with the Instagram product added. Your own account is added as a role (admin, developer or tester), so the app can stay in development mode: no App Review is needed to post to your own account. |
| Permission on the token | `instagram_business_content_publish` (plus `instagram_business_basic`) for Instagram Login. The token used today for insights usually carries only the read permissions: it has to be issued again with the publish permission and exchanged for a long-lived token (about 60 days; it must be refreshed). With Facebook Login the permission is `instagram_content_publish` and the account must be linked to a Facebook Page. |
| A public URL for the file | The API fetches `video_url` itself, so the mp4 must be reachable over HTTPS when you publish. Either a temporary file on your own server (deleted after the post goes live), or a resumable upload if your login route supports it (check Meta's page for your route before relying on it). |
| Where the token lives | A gitignored `.env` (`IG_ACCESS_TOKEN`, `IG_USER_ID`), the same as the insights script. Never in the repo or in a chat. |

Limits to design around (check the current numbers): a quota of API posts per 24 hours, a maximum reel length,
MP4/MOV with H.264 video and AAC audio, 9:16. The API cannot attach trending audio from the app. Our output already
meets the format; the length check is in the `check:` block of `render.py`.

## YouTube Shorts (optional)

Route: [`videos.insert`](https://developers.google.com/youtube/v3/docs/videos/insert) in the YouTube Data API.

| Need | Detail |
|---|---|
| Google Cloud project | With the YouTube Data API enabled and an OAuth client (desktop app type). One browser sign-in on your channel gives a refresh token, kept in `.env`. |
| Scope | `https://www.googleapis.com/auth/youtube.upload`. |
| The audit | Google documents that videos uploaded through an **unverified** API project created after 28 July 2020 are locked to private. The call succeeds and returns a video ID, but nobody else can see the video until the project passes Google's API compliance audit. Plan for the audit form, or accept private uploads and switch them to public by hand. |
| Quota | The cost of an upload is listed differently across versions of the documentation (older guides say 1 600 units of 10 000 per day). Read the quota page of your project before scheduling several uploads a day. |

## What you do, in order

1. Decide where reels go: Instagram only, or Instagram and YouTube.
2. Check that the Instagram account is Professional (Settings, Account type).
3. In the Meta developer app: add yourself as a role, add the Instagram product, generate a token with the publish
   permission. Put it in `.env`. Check its scopes with a read-only call before the first post.
4. Decide where the temporary public file lives (your server path, or a resumable upload).
5. For YouTube: create the Google Cloud project and OAuth client, sign in once, decide whether to file the audit.

After that the publish step is a small script with a dry run and an explicit confirmation flag; it posts the reel,
prints the permalink, and writes it to your tracker.
