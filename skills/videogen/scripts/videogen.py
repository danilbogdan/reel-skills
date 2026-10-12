#!/usr/bin/env python3
"""Make a short AI video clip with FLUX 3 video (Black Forest Labs): from a prompt, or from one of your own frames.

Usage:
  videogen.py frame VIDEO --at 8.0 --out frame.png
  videogen.py generate --prompt "..." [--image frame.png] [--seconds 5] [--aspect 9:16]
                       [--resolution hd] [--draft] --out clip.mp4 [--yes]

`frame` grabs one frame from your own video, to use as the starting picture (image-to-video keeps the same
person and place; a prompt alone invents a stranger).

`generate` shows the request and an estimated cost and STOPS, unless you pass --yes. Nothing is spent without it.
Use --draft first: a draft is a fast, cheaper preview. When you pass --yes the script submits once, polls every
6 seconds, downloads the clip (and any draft cache), and prints the cost the API reports.

Key: environment variable BFL_API_KEY (never put it in a file in this repo). Needs ffmpeg for `frame`.
Prices below are rough, last checked 2026-10; the API's `cost` field is the real number.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = os.environ.get("BFL_API_BASE", "https://api.bfl.ai")
ENDPOINT = "/v1/flux-3-video"
ASPECTS = ["auto", "21:9", "2:1", "16:9", "4:3", "1:1", "3:4", "9:16"]
# Rough price per generated second in USD; drafts are billed for at least 5 s.
PRICE = {("hd", True): 0.06, ("hd", False): 0.17, ("fhd", False): 0.29, ("fhd", True): 0.12}
TERMINAL_FAIL = {"Error", "Request Moderated", "Content Moderated", "Task not found"}


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def cmd_frame(args):
    src = Path(args.video)
    if not src.is_file():
        die(f"{src} not found")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(args.at), "-i", str(src),
                          "-frames:v", "1", str(out)], capture_output=True, text=True)
    if res.returncode != 0 or not out.exists():
        die(f"could not extract a frame: {res.stderr.strip()[:200]}")
    print(f"wrote {out}")


def image_size(path):
    res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=s=x:p=0", str(path)], capture_output=True, text=True)
    try:
        w, h = res.stdout.strip().split("x")
        return int(w), int(h)
    except ValueError:
        return None


def build_body(args):
    body = {"mode": "t2v", "prompt": args.prompt, "aspect_ratio": args.aspect, "duration": args.seconds,
            "resolution": args.resolution, "generate_audio": False, "draft": bool(args.draft)}
    if args.image:
        img = Path(args.image)
        if not img.is_file():
            die(f"{img} not found")
        size = image_size(img)
        if size and min(size) < 256:
            die(f"the image is {size[0]}x{size[1]}; keyframes must be at least 256x256")
        mime = "image/jpeg" if img.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        body["mode"] = "i2v"
        body["keyframes"] = f"data:{mime};base64," + base64.b64encode(img.read_bytes()).decode()
    return body


def call(url, key, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={
        "x-key": key, "accept": "application/json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def save(url, path):
    with urllib.request.urlopen(url, timeout=300) as r:
        Path(path).write_bytes(r.read())


def cmd_generate(args):
    if not 5 <= args.seconds <= 20:
        die("--seconds must be between 5 and 20")
    if args.aspect not in ASPECTS:
        die(f"--aspect must be one of {', '.join(ASPECTS)}")
    body = build_body(args)

    billed = max(args.seconds, 5)
    rate = PRICE.get((args.resolution, bool(args.draft)))
    estimate = f"about ${rate * billed:.2f}" if rate else "unknown (check the BFL pricing page)"
    shown = dict(body)
    if "keyframes" in shown:
        shown["keyframes"] = f"<image data, {len(body['keyframes'])} characters>"
    print("request:", json.dumps(shown, indent=1))
    print(f"mode {body['mode']}, {'draft' if args.draft else 'full quality'}, estimated cost {estimate}")
    if not args.yes:
        print("not submitted. Add --yes to spend this and generate the clip.")
        return

    key = os.environ.get("BFL_API_KEY")
    if not key:
        die("set BFL_API_KEY in your shell first (see skills/videogen/SKILL.md)", 2)

    try:
        job = call(API_BASE + ENDPOINT, key, body)
    except urllib.error.HTTPError as e:
        detail = e.read()[:400].decode("utf-8", "replace")
        if e.code == 429:
            die("429 on submit: your account's job limit is full and nothing was created; wait and run again")
        die(f"submit failed, HTTP {e.code}: {detail}")
    print(f"submitted {job.get('id')}, reported cost {job.get('cost')}")

    started = time.time()
    while True:
        try:
            res = call(job["polling_url"], key)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):                # the task exists; back off and keep polling
                time.sleep(args.poll_seconds * 2)
                continue
            die(f"polling failed, HTTP {e.code}")
        status = res.get("status")
        print(f"  {int(time.time() - started):4d}s  {status}")
        if status == "Ready":
            break
        if status in TERMINAL_FAIL:
            die(f"generation ended with '{status}': {json.dumps(res)[:300]}")
        if time.time() - started > args.max_wait:
            die(f"gave up after {args.max_wait} s; the task id is {job.get('id')}")
        time.sleep(args.poll_seconds)

    result = res.get("result", {})
    samples = result.get("samples") or ([result["sample"]] if result.get("sample") else [])
    caches = result.get("draft_caches") or ([result["draft_cache"]] if result.get("draft_cache") else [])
    if not samples:
        die(f"finished but no video URL in the result: {json.dumps(result)[:300]}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(samples):                   # signed URLs expire in about an hour: download now
        target = out if i == 0 else out.with_name(f"{out.stem}-{i}{out.suffix}")
        save(url, target)
        print(f"saved {target}")
    for i, url in enumerate(caches):
        target = out.with_name(f"{out.stem}.cache{i}.bin")
        save(url, target)
        print(f"saved draft cache {target}")
    print("check every frame before you use the clip (hands, fingers and text are the usual failures)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("frame", help="grab one frame from your own video")
    f.add_argument("video")
    f.add_argument("--at", type=float, default=1.0, help="time in seconds")
    f.add_argument("--out", required=True)
    g = sub.add_parser("generate", help="make a clip (shows the cost first)")
    g.add_argument("--prompt", required=True)
    g.add_argument("--image", help="starting frame (image-to-video)")
    g.add_argument("--seconds", type=int, default=5)
    g.add_argument("--aspect", default="9:16")
    g.add_argument("--resolution", default="hd", choices=["hd", "fhd"])
    g.add_argument("--draft", action="store_true", help="cheaper, faster preview")
    g.add_argument("--out", required=True)
    g.add_argument("--yes", action="store_true", help="really submit and spend")
    g.add_argument("--poll-seconds", type=float, default=6.0)
    g.add_argument("--max-wait", type=int, default=900)
    args = ap.parse_args()
    cmd_frame(args) if args.cmd == "frame" else cmd_generate(args)


if __name__ == "__main__":
    main()
