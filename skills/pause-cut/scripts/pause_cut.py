#!/usr/bin/env python3
"""Plan the removal of dead pauses from a talking-head clip and write a cut list (JSON).

Usage:
  pause_cut.py VIDEO --out cuts.json [--noise -30] [--min-pause 0.4] [--keep-pause 0.3] [--min-piece 1.0]

How it decides:
  * a pause is silence of at least --min-pause seconds below --noise dB;
  * a pause is shortened to --keep-pause seconds (a small breath stays, so speech does not sound clipped);
  * a pause is NOT cut when that would leave a piece shorter than --min-piece seconds: the short piece keeps
    its pause, so you do not end up with one-second fragments.

Writes the cut list (see skills/reel-render) and prints how much time was removed. Needs ffmpeg and ffprobe.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def duration_of(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(video)], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def detect_silences(video, noise_db, min_pause, duration):
    res = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af",
                          f"silencedetect=noise={noise_db}dB:d={min_pause}", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", res.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", res.stderr)]
    silences = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else duration
        silences.append((s, e))
    return silences


def speech_blocks(silences, duration):
    blocks, cursor = [], 0.0
    for s, e in silences:
        if s - cursor > 0.05:
            blocks.append((cursor, s))
        cursor = e
    if duration - cursor > 0.05:
        blocks.append((cursor, duration))
    return blocks


def plan_pieces(blocks, duration, keep_pause, min_piece):
    half = keep_pause / 2
    cur_start = max(0.0, blocks[0][0] - half)
    pieces = []
    for i in range(len(blocks) - 1):
        gap = blocks[i + 1][0] - blocks[i][1]
        piece_len = blocks[i][1] - cur_start
        if gap > keep_pause and piece_len >= min_piece:
            pieces.append([cur_start, min(duration, blocks[i][1] + half)])
            cur_start = max(0.0, blocks[i + 1][0] - half)
    last_end = min(duration, blocks[-1][1] + half)
    if pieces and last_end - cur_start < min_piece:
        pieces[-1][1] = last_end          # tail too short: restore the pause before it
    else:
        pieces.append([cur_start, last_end])
    return pieces


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", required=True, help="cut list to write, e.g. workspace/out/cuts.json")
    ap.add_argument("--noise", type=float, default=-30.0, help="silence threshold in dB (default -30)")
    ap.add_argument("--min-pause", type=float, default=0.4, help="shortest silence counted as a pause, seconds")
    ap.add_argument("--keep-pause", type=float, default=0.3, help="pause length to keep at each cut, seconds")
    ap.add_argument("--min-piece", type=float, default=1.0, help="never leave a piece shorter than this, seconds")
    args = ap.parse_args()

    video = Path(args.video)
    if not video.is_file():
        sys.exit(f"error: {video} not found")
    duration = duration_of(video)
    silences = detect_silences(video, args.noise, args.min_pause, duration)
    blocks = speech_blocks(silences, duration)
    if not blocks:
        sys.exit("error: no speech found; try a lower --noise such as -40")

    pieces = plan_pieces(blocks, duration, args.keep_pause, args.min_piece)
    kept = sum(e - s for s, e in pieces)
    cuts = {
        "source": str(video),
        "duration": round(duration, 3),
        "params": {"noise_db": args.noise, "min_pause": args.min_pause,
                   "keep_pause": args.keep_pause, "min_piece": args.min_piece},
        "segments": [{"start": round(s, 3), "end": round(e, 3)} for s, e in pieces],
        "kept_seconds": round(kept, 2),
        "removed_seconds": round(duration - kept, 2),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(cuts, indent=1) + "\n", encoding="utf-8")
    print(f"{len(silences)} pauses found, {len(pieces)} pieces kept")
    print(f"{duration:.1f} s -> {kept:.1f} s (removed {duration - kept:.1f} s)")
    for i, (s, e) in enumerate(pieces, 1):
        print(f"  {i:2d}  {s:7.2f} - {e:7.2f}  ({e - s:.2f} s)")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
