#!/usr/bin/env python3
"""Clean up a voice track and bring it to a fixed loudness (default -14 LUFS, true peak under -1.5 dBFS).

Usage:
  audio_polish.py IN.wav OUT.wav [--clean auto|light|full|none] [--lufs -14] [--peak -1.5]

What it does, in order:
  1. a chain chosen by --clean: light = high-pass, a little mud removed, a little presence added, gentle
     compression; full = the same plus broadband denoise, de-click and a soft gate in the gaps (for a noisy room);
     auto = full when the room noise is within 35 dB of the speech, light otherwise; none = no chain;
  2. measures the integrated loudness of the result and applies one gain to hit --lufs, then a peak limiter.
     It measures again and corrects once if the limiter cost loudness. loudnorm alone stops short of the target on
     clean, spiky voice recordings, so this is a measured gain instead.

Prints the room/speech levels, the chain used and the loudness before and after. Needs ffmpeg.
"""
import argparse
import array
import math
import re
import subprocess
import sys
from pathlib import Path

LIGHT = ("highpass=f=70,"
         "equalizer=f=250:t=q:w=1:g=-1.5,"
         "equalizer=f=3200:t=q:w=1:g=1.5,"
         "acompressor=threshold=-20dB:ratio=2.2:attack=8:release=160:makeup=1")
FULL = ("highpass=f=70,"
        "afftdn=nr=9:nf=-42:tn=1,"
        "adeclick=w=55:o=75:a=2:t=2:b=2:m=a,"
        "agate=threshold=-38dB:ratio=1.6:attack=6:release=180:knee=6,"
        "equalizer=f=250:t=q:w=1:g=-1.5,"
        "equalizer=f=3200:t=q:w=1:g=1.5,"
        "acompressor=threshold=-18dB:ratio=2:attack=8:release=150:makeup=1.5")
CHAINS = {"light": LIGHT, "full": FULL, "none": "anull"}
SNR_FOR_LIGHT = 35.0   # dB between speech and room noise; below this the room is noisy enough to denoise


def noise_levels(path):
    """(room dBFS, speech dBFS): 10th and 90th percentile of a 20 ms loudness envelope."""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    env = []
    for i in range(0, max(0, len(samples) - 320), 160):
        chunk = samples[i:i + 320]
        power = sum(s * s for s in chunk) / (len(chunk) * 32768.0 ** 2)
        env.append(10 * math.log10(power) if power > 1e-12 else -120.0)
    if len(env) < 10:
        return -120.0, -120.0
    env.sort()
    return env[int(0.10 * (len(env) - 1))], env[int(0.90 * (len(env) - 1))]


def measure(path, chain):
    """Integrated loudness (LUFS) and true peak (dBFS) of PATH after CHAIN."""
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", f"{chain},ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True)
    summary = res.stderr[res.stderr.rfind("Summary:"):]
    loud = re.search(r"I:\s*(-?[0-9.]+)\s*LUFS", summary)
    peak = re.search(r"Peak:\s*(-?[0-9.]+)\s*dBFS", summary)
    if not loud:
        sys.exit("error: could not measure loudness (is there an audio track?)")
    return float(loud.group(1)), float(peak.group(1)) if peak else 0.0


def polish(src, dst, clean="auto", lufs=-14.0, peak=-1.5, verbose=True):
    """Write DST (48 kHz 24-bit wav). Returns a dict with the numbers for QC."""
    room, speech = noise_levels(src)
    if clean == "auto":
        clean = "light" if speech - room >= SNR_FOR_LIGHT else "full"
    chain = CHAINS[clean]
    before, _ = measure(src, "anull")
    after_chain, _ = measure(src, chain)
    ceiling = 10 ** (peak / 20)
    limiter = f"alimiter=limit={ceiling:.3f}:level=false"
    gain = lufs - after_chain
    for _ in range(3):
        tail = f"volume={gain:.2f}dB,{limiter}"
        got, tp = measure(src, f"{chain},{tail}")
        if abs(got - lufs) <= 0.5 or gain > 24:
            break
        gain += lufs - got
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", f"{chain},{tail},afade=t=in:st=0:d=0.02",
                    "-ar", "48000", "-c:a", "pcm_s24le", str(dst)], check=True)
    info = {"clean": clean, "room_db": round(room, 1), "speech_db": round(speech, 1),
            "lufs_before": before, "lufs_after": got, "true_peak": tp, "gain_db": round(gain, 1)}
    if verbose:
        print(f"audio: room {room:.0f} dB, speech {speech:.0f} dB -> chain '{clean}'; "
              f"{before:.1f} LUFS -> {got:.1f} LUFS, peak {tp:.1f} dBFS (gain {gain:+.1f} dB)")
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--clean", default="auto", choices=["auto", "light", "full", "none"])
    ap.add_argument("--lufs", type=float, default=-14.0, help="integrated loudness target (default -14)")
    ap.add_argument("--peak", type=float, default=-1.5, help="peak ceiling in dBFS (default -1.5)")
    args = ap.parse_args()
    if not Path(args.src).is_file():
        sys.exit(f"error: {args.src} not found")
    polish(args.src, args.dst, args.clean, args.lufs, args.peak)
    print(f"wrote {args.dst}")


if __name__ == "__main__":
    main()
