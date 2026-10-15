#!/usr/bin/env python3
"""Plan the removal of dead pauses from a talking-head clip and write a cut list (JSON).

Usage:
  pause_cut.py VIDEO --out cuts.json [--noise auto] [--min-pause 0.4] [--keep-pause 0.3] [--min-piece 3.0]
               [--head 0.15] [--tail 0.4] [--drop A-B ...]

How it decides:
  * the speech level is measured from the audio itself (10 ms loudness envelope); with --noise auto the
    silence threshold sits between the room noise and the speech, so a quiet voice is not mistaken for silence;
  * a pause is silence of at least --min-pause seconds; a cut shortens it to --keep-pause seconds (a breath stays);
  * RHYTHM RULE: two cuts are never closer than --min-piece seconds. Among cuts that would break the rule, the
    plan keeps the ones that remove the most dead air and leaves the shorter pauses as they were. This is what
    stops "one word, two jump cuts in three seconds";
  * --drop A-B removes a range you name (source seconds, e.g. a stumble). The range is widened to the pauses on
    both sides, so it costs ONE cut, not three; it always wins over the automatic cuts it overlaps.

Writes the cut list (see skills/reel-render) and prints how much time was removed. Needs ffmpeg and ffprobe.
"""
import argparse
import array
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

RATE = 16000
HOP = 0.010           # envelope step, seconds
WIN = 0.020           # envelope window, seconds
SPEECH_PAD = 0.06     # consonant onsets and decays are quieter than the threshold; protect them
MIN_SPEECH = 0.06     # shorter bursts are clicks, not words
MIN_SAVING = 0.20     # a cut must remove at least this much, or it is not worth a visible join
CUT_PENALTY = 0.12    # in the plan, each cut also "costs" this much, so ties go to fewer cuts
FORCED = 1e6


def duration_of(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(video)], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def envelope_db(video):
    """Loudness envelope in dBFS, one value per HOP seconds."""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", str(RATE),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    hop, win = int(HOP * RATE), int(WIN * RATE)
    env = []
    for i in range(0, max(0, len(samples) - win), hop):
        chunk = samples[i:i + win]
        power = sum(s * s for s in chunk) / (len(chunk) * 32768.0 ** 2)
        env.append(10 * math.log10(power) if power > 1e-12 else -120.0)
    return env


def auto_threshold(env):
    """Between the room noise (10th percentile) and the speech level (90th percentile), 30 percent of the way up."""
    ordered = sorted(env)
    floor = ordered[int(0.10 * (len(ordered) - 1))]
    speech = ordered[int(0.90 * (len(ordered) - 1))]
    return min(-25.0, max(-55.0, floor + 0.30 * (speech - floor))), floor, speech


def speech_runs(env, threshold, min_pause, duration):
    """Speech intervals (seconds), padded, bridged over gaps shorter than min_pause."""
    runs, start = [], None
    for i, db in enumerate(env):
        if db > threshold and start is None:
            start = i
        elif db <= threshold and start is not None:
            runs.append([start * HOP, i * HOP])
            start = None
    if start is not None:
        runs.append([start * HOP, len(env) * HOP])
    runs = [r for r in runs if r[1] - r[0] >= MIN_SPEECH]
    padded = [[max(0.0, s - SPEECH_PAD), min(duration, e + SPEECH_PAD)] for s, e in runs]
    merged = []
    for s, e in padded:
        if merged and s - merged[-1][1] < min_pause:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged


def pauses_between(runs):
    return [(runs[i][1], runs[i + 1][0]) for i in range(len(runs) - 1)]


def build_candidates(pauses, keep_pause, min_pause, drops):
    """Cut candidates {start, end, saving, forced}: remove [start, end], keeping keep_pause/2 of silence each side."""
    half = keep_pause / 2
    cands = []
    for a, b in pauses:
        if b - a >= max(min_pause, keep_pause + MIN_SAVING):
            cands.append({"start": a + half, "end": b - half, "forced": False})
    for da, db in drops:
        start, end = da, db
        for a, b in pauses:            # widen to the pause that touches the range, one cut instead of three
            if a - 0.3 <= da <= b + 0.3:
                start = min(start, a + half)
            if a - 0.3 <= db <= b + 0.3:
                end = max(end, b - half)
        cands = [c for c in cands if c["end"] <= start or c["start"] >= end]
        cands.append({"start": start, "end": end, "forced": True})
    cands.sort(key=lambda c: c["start"])
    for c in cands:
        c["saving"] = c["end"] - c["start"]
    return cands


def select_cuts(cands, head_start, tail_end, min_piece):
    """Pick the subset of candidates that removes the most time while every kept piece is >= min_piece long.

    Weighted interval selection by dynamic programming; forced cuts weigh FORCED, so they are always kept
    and the automatic cuts that conflict with them are the ones given up."""
    n = len(cands)
    weight = [c["saving"] - CUT_PENALTY + (FORCED if c["forced"] else 0.0) for c in cands]
    best = [None] * n      # best total weight of a plan whose LAST cut is j
    prev = [None] * n
    for j in range(n):
        head_ok = cands[j]["start"] - head_start >= min_piece
        top, link = (weight[j], -1) if head_ok else (None, -1)
        for i in range(j):
            if best[i] is None or cands[j]["start"] - cands[i]["end"] < min_piece:
                continue
            if top is None or best[i] + weight[j] > top:
                top, link = best[i] + weight[j], i
        best[j], prev[j] = top, link
    end_j, end_score = -1, 0.0
    for j in range(n):
        if best[j] is not None and tail_end - cands[j]["end"] >= min_piece and best[j] > end_score:
            end_j, end_score = j, best[j]
    # a forced cut is kept even when it breaks the rule: the human asked for it
    for j, c in enumerate(cands):
        if c["forced"] and not _contains(end_j, prev, j):
            return _forced_fallback(cands, head_start, tail_end, min_piece)
    chosen, j = [], end_j
    while j >= 0:
        chosen.append(cands[j])
        j = prev[j]
    return chosen[::-1]


def _contains(end_j, prev, target):
    j = end_j
    while j >= 0:
        if j == target:
            return True
        j = prev[j]
    return False


def _forced_fallback(cands, head_start, tail_end, min_piece):
    """Forced cuts break the spacing rule on their own (e.g. a --drop 2 s from the start): keep them all, then
    add automatic cuts only where the pieces on both sides of the new cut respect the rule."""
    chosen = [c for c in cands if c["forced"]]
    for c in cands:
        if c["forced"]:
            continue
        before = [x for x in chosen if x["end"] <= c["start"]]
        after = [x for x in chosen if x["start"] >= c["end"]]
        left = c["start"] - (before[-1]["end"] if before else head_start)
        right = (after[0]["start"] if after else tail_end) - c["end"]
        if left >= min_piece and right >= min_piece:
            chosen = sorted(chosen + [c], key=lambda x: x["start"])
    return sorted(chosen, key=lambda x: x["start"])


def pieces_from(cuts, head_start, tail_end):
    pieces, cursor = [], head_start
    for c in cuts:
        pieces.append([cursor, c["start"]])
        cursor = c["end"]
    pieces.append([cursor, tail_end])
    return pieces


def parse_drop(text):
    try:
        a, b = (float(x) for x in text.split("-", 1))
    except ValueError:
        sys.exit(f"error: --drop wants START-END in seconds, got {text!r}")
    if b <= a:
        sys.exit(f"error: --drop {text}: end must be after start")
    return a, b


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", required=True, help="cut list to write, e.g. workspace/out/cuts.json")
    ap.add_argument("--noise", default="auto",
                    help="silence threshold in dB, or 'auto' to measure it from the clip (default auto)")
    ap.add_argument("--min-pause", type=float, default=0.4, help="shortest silence counted as a pause, seconds")
    ap.add_argument("--keep-pause", type=float, default=0.3, help="pause length to keep at each cut, seconds")
    ap.add_argument("--min-piece", type=float, default=3.0,
                    help="shortest stretch between two cuts, seconds (the rhythm rule; default 3.0)")
    ap.add_argument("--head", type=float, default=0.15, help="silence kept before the first word, seconds")
    ap.add_argument("--tail", type=float, default=0.4, help="silence kept after the last word, seconds")
    ap.add_argument("--drop", action="append", default=[], metavar="A-B",
                    help="also remove this source range (seconds); repeatable")
    args = ap.parse_args()

    video = Path(args.video)
    if not video.is_file():
        sys.exit(f"error: {video} not found")
    duration = duration_of(video)
    env = envelope_db(video)
    if len(env) < 10:
        sys.exit("error: the clip is too short or has no audio")
    if args.noise == "auto":
        threshold, floor, speech = auto_threshold(env)
        print(f"noise threshold {threshold:.1f} dB (room {floor:.1f} dB, speech {speech:.1f} dB)")
    else:
        threshold = float(args.noise)

    runs = speech_runs(env, threshold, args.min_pause, duration)
    if not runs:
        sys.exit("error: no speech found; try --noise -45")
    pauses = pauses_between(runs)
    head_start = max(0.0, runs[0][0] - args.head)
    tail_end = min(duration, runs[-1][1] + args.tail)

    drops = [parse_drop(d) for d in args.drop]
    cands = build_candidates(pauses, args.keep_pause, args.min_pause, drops)
    cuts = select_cuts(cands, head_start, tail_end, args.min_piece)
    pieces = pieces_from(cuts, head_start, tail_end)

    cut_keys = {(round(c["start"], 3), round(c["end"], 3)) for c in cuts}
    kept_pauses = [{"at": round(c["start"], 2), "seconds": round(c["end"] - c["start"] + args.keep_pause, 2)}
                   for c in cands if (round(c["start"], 3), round(c["end"], 3)) not in cut_keys]
    kept = sum(e - s for s, e in pieces)
    lengths = [e - s for s, e in pieces]
    out = {
        "source": str(video),
        "duration": round(duration, 3),
        "params": {"noise_db": round(threshold, 1), "min_pause": args.min_pause, "keep_pause": args.keep_pause,
                   "min_piece": args.min_piece, "head": args.head, "tail": args.tail},
        "segments": [{"start": round(s, 3), "end": round(e, 3)} for s, e in pieces],
        "kept_seconds": round(kept, 2),
        "removed_seconds": round(duration - kept, 2),
        "cuts": len(pieces) - 1,
        "shortest_piece": round(min(lengths), 2),
        "pauses_left_by_rhythm_rule": kept_pauses,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")

    print(f"{len(pauses)} pauses found, {len(cuts)} cut, {len(pieces)} pieces kept")
    print(f"{duration:.1f} s -> {kept:.1f} s (removed {duration - kept:.1f} s); "
          f"median piece {statistics.median(lengths):.1f} s, shortest {min(lengths):.1f} s")
    for i, (s, e) in enumerate(pieces, 1):
        print(f"  {i:2d}  {s:7.2f} - {e:7.2f}  ({e - s:.2f} s)")
    if kept_pauses:
        print(f"{len(kept_pauses)} pause(s) left in place by the rhythm rule (--min-piece {args.min_piece}):")
        for k in kept_pauses:
            print(f"    at {k['at']:.2f} s, {k['seconds']:.2f} s long")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
