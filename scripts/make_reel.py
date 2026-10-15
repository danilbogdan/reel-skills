#!/usr/bin/env python3
"""One command from a raw take to a reel ready to post: cut the pauses, render, level the voice, caption, check.

Usage:
  scripts/make_reel.py TAKE --out workspace/out/reel.mp4 [--language ru] [--no-captions]
                       [--min-piece 3.0] [--audio auto|light|full|none] [--drop A-B ...]

Runs skills/pause-cut and skills/reel-render with their defaults (quiet captions, still punch-in at the cuts, voice
at -14 LUFS) and writes next to the reel: cuts.json (the plan, editable), reel.srt (the captions, for a read-through).
Nothing is uploaded. Needs ffmpeg; whisper for captions (--no-captions to skip).
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("take")
    ap.add_argument("--out", required=True, help="the reel to write, e.g. workspace/out/reel.mp4")
    ap.add_argument("--language", help="spoken language for the captions, e.g. ru (default: detect)")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--min-piece", default="3.0", help="shortest stretch between two cuts, seconds")
    ap.add_argument("--audio", default="auto", choices=["auto", "light", "full", "none"])
    ap.add_argument("--drop", action="append", default=[], metavar="A-B", help="also cut this source range (seconds)")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cuts = out.with_name(out.stem + ".cuts.json")
    plan = [sys.executable, str(ROOT / "skills/pause-cut/scripts/pause_cut.py"), args.take, "--out", str(cuts),
            "--min-piece", args.min_piece]
    for d in args.drop:
        plan += ["--drop", d]
    render = [sys.executable, str(ROOT / "skills/reel-render/scripts/render.py"), str(cuts), "--out", str(out),
              "--audio", args.audio]
    if not args.no_captions:
        render += ["--transcribe"] + (["--language", args.language] if args.language else [])
    for cmd in (plan, render):
        if subprocess.run(cmd).returncode:
            sys.exit(1)
    print(f"\nreel: {out}\nplan: {cuts}" + ("" if args.no_captions else f"\ncaptions: {out.with_suffix('.srt')}"))


if __name__ == "__main__":
    main()
