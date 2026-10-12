#!/usr/bin/env python3
"""Render a vertical reel (1080x1920 by default) from a cut list: trim, crop to 9:16, gentle zoom, warm
grade, join, and optionally burn in captions from an SRT file.

Usage:
  render.py CUTS.json --out reel.mp4 [--srt captions.srt] [--zoom 0.06]
            [--zoom-style alternate|in|out|none] [--grade warm|none] [--size 1080x1920] [--fps 30] [--dry-run]

Cut list (what pause_cut.py writes; you can edit it by hand):
  {"source": "take.mov",
   "segments": [{"start": 0.0, "end": 4.2},
                {"start": 6.0, "end": 9.5, "zoom": 0.1, "zoom_style": "out", "grade": "none",
                 "source": "other.mp4"}]}

Per-segment keys override the command-line defaults. Needs ffmpeg and ffprobe (libass for --srt).
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WARM = "colorbalance=rs=0.05:gs=0.01:bs=-0.06:rm=0.04:bm=-0.04,eq=saturation=1.05"
SUB_STYLE = "Alignment=2,Fontsize=14,Outline=2,Shadow=0,MarginV=60"


def has_audio(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                          "stream=codec_type", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return bool(out.stdout.strip())


def video_filter(seg, args, width, height, fps, frames):
    chain = [f"fps={fps}", f"scale={width}:{height}:force_original_aspect_ratio=increase",
             f"crop={width}:{height}", "setsar=1"]
    z = float(seg.get("zoom", args.zoom))
    style = seg.get("zoom_style", args.zoom_style)
    if style == "alternate":
        style = "in" if seg["_i"] % 2 == 0 else "out"
    if z > 0 and style in ("in", "out"):
        expr = f"1+{z}*on/{frames}" if style == "in" else f"{1 + z}-{z}*on/{frames}"
        chain.append(f"zoompan=z='{expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps={fps}")
    if seg.get("grade", args.grade) == "warm":
        chain.append(WARM)
    return ",".join(chain)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cuts")
    ap.add_argument("--out", required=True)
    ap.add_argument("--srt", help="captions to burn in; times are on the FINAL timeline")
    ap.add_argument("--zoom", type=float, default=0.06, help="zoom amount, 0.06 = 6 percent (0 disables)")
    ap.add_argument("--zoom-style", default="alternate", choices=["alternate", "in", "out", "none"])
    ap.add_argument("--grade", default="warm", choices=["warm", "none"])
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true", help="print the ffmpeg commands and stop")
    args = ap.parse_args()

    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        sys.exit("error: ffmpeg and ffprobe are required (see docs/setup.md)")
    cuts_path = Path(args.cuts)
    cuts = json.loads(cuts_path.read_text(encoding="utf-8"))
    segs = cuts.get("segments", [])
    if not segs:
        sys.exit("error: the cut list has no segments")
    width, height = (int(x) for x in args.size.lower().split("x"))
    base = cuts_path.parent

    def resolve(p):
        q = Path(p)
        return q if q.is_absolute() or q.exists() else (base / q)

    tmp = Path(tempfile.mkdtemp(prefix="reel-render-"))
    cmds, parts = [], []
    for i, seg in enumerate(segs):
        seg["_i"] = i
        src = resolve(seg.get("source") or cuts.get("source", ""))
        if not src.is_file():
            sys.exit(f"error: segment {i + 1}: source {src} not found")
        dur = float(seg["end"]) - float(seg["start"])
        if dur <= 0:
            sys.exit(f"error: segment {i + 1}: end must be after start")
        frames = max(1, round(dur * args.fps))
        out = tmp / f"seg_{i:03d}.mp4"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{float(seg['start']):.3f}", "-t", f"{dur:.3f}", "-i", str(src)]
        if has_audio(src):
            cmd += ["-vf", video_filter(seg, args, width, height, args.fps, frames),
                    "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "160k"]
        else:
            cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
                    "-vf", video_filter(seg, args, width, height, args.fps, frames),
                    "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-shortest"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(args.fps), str(out)]
        cmds.append(cmd)
        parts.append(out)

    listing = tmp / "list.txt"
    joined = tmp / "joined.mp4"
    join_cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined)]
    final_cmd = None
    if args.srt:
        srt = Path(args.srt)
        if not srt.is_file():
            sys.exit(f"error: {srt} not found")
        final_cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(joined), "-vf",
                     f"subtitles=cap.srt:force_style='{SUB_STYLE}'", "-c:v", "libx264", "-preset", "veryfast",
                     "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", str(Path(args.out).resolve())]

    if args.dry_run:
        for c in cmds + [join_cmd] + ([final_cmd] if final_cmd else []):
            print(" ".join(c))
        shutil.rmtree(tmp, ignore_errors=True)
        return

    for c in cmds:
        subprocess.run(c, check=True)
    listing.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    subprocess.run(join_cmd, check=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    if final_cmd:
        shutil.copy(args.srt, tmp / "cap.srt")
        subprocess.run(final_cmd, check=True, cwd=tmp)
    else:
        shutil.copy(joined, args.out)
    shutil.rmtree(tmp, ignore_errors=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", args.out],
                         capture_output=True, text=True).stdout.strip()
    print(f"wrote {args.out}  ({len(segs)} segments, {float(dur):.1f} s, {width}x{height})")


if __name__ == "__main__":
    main()
