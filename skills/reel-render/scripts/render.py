#!/usr/bin/env python3
"""Render a vertical reel (1080x1920 by default) from a cut list: trim, crop to 9:16, hide the jump cuts with a
small punch-in, join, clean and level the voice, and optionally burn in quiet captions.

Usage:
  render.py CUTS.json --out reel.mp4 [--srt captions.srt|whisper.json] [--audio auto|light|full|none]
            [--zoom 0.07] [--zoom-style punch|alternate|in|out|none] [--grade warm|none] [--size 1080x1920]
            [--fps 30] [--caption-style clean|bold] [--caption-font "Inter Light"] [--fonts-dir DIR]
            [--lufs -14] [--transcribe [--language ru] [--whisper-model medium]] [--dry-run]

Cut list (what pause_cut.py writes; you can edit it by hand):
  {"source": "take.mov",
   "segments": [{"start": 0.0, "end": 4.2},
                {"start": 6.0, "end": 9.5, "zoom": 0.1, "zoom_style": "out", "grade": "none",
                 "source": "other.mp4"}]}

Per-segment keys override the command-line defaults. Needs ffmpeg and ffprobe (libass for captions).

Audio is rebuilt from the original files, not re-encoded piece by piece: every piece gets 8 ms fades (no clicks at the
joins), the pieces are joined as PCM, the whole track is cleaned and set to --lufs, and only then encoded once.
--transcribe runs Whisper on the finished voice track and burns the result in, so one command gives a reel with
captions; the transcript is also saved next to the reel (.srt) for a quick read-through. Prints a check at the end (resolution, loudness, peak, shortest piece, cuts, captions). Warnings are not errors.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audio_polish  # noqa: E402
import captions  # noqa: E402

WARM = "colorbalance=rs=0.05:gs=0.01:bs=-0.06:rm=0.04:bm=-0.04,eq=saturation=1.05"
EDGE_FADE = 0.008          # seconds, fade at both ends of each audio piece


def probe_stream(path, kind):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", kind, "-show_entries",
                          "stream=width,height,codec_type", "-of", "json", str(path)], capture_output=True, text=True)
    streams = json.loads(out.stdout or "{}").get("streams", [])
    return streams[0] if streams else None


def has_audio(path):
    return probe_stream(path, "a") is not None


def video_filter(seg, args, width, height, fps, frames):
    chain = [f"fps={fps}"]
    z = float(seg.get("zoom", args.zoom))
    style = seg.get("zoom_style", args.zoom_style)
    if style == "alternate":
        style = "in" if seg["_i"] % 2 == 0 else "out"
    if style == "punch":
        # a still 1.0x / 1.07x alternation: the cut reads as a change of shot, nothing moves
        scale = 1 + z if seg["_i"] % 2 == 1 else 1.0
        chain += [f"scale={round(width * scale / 2) * 2}:{round(height * scale / 2) * 2}:"
                  "force_original_aspect_ratio=increase:flags=lanczos",
                  f"crop={width}:{height}"]
    else:
        chain += [f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos",
                  f"crop={width}:{height}"]
        if z > 0 and style in ("in", "out"):
            expr = f"1+{z}*on/{frames}" if style == "in" else f"{1 + z}-{z}*on/{frames}"
            chain.append(f"zoompan=z='{expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps={fps}")
    chain.append("setsar=1")
    if seg.get("grade", args.grade) == "warm":
        chain.append(WARM)
    return ",".join(chain)


def font_family_present(family, fonts_dir):
    if fonts_dir:
        return True
    if not shutil.which("fc-match"):
        return True  # cannot tell; libass will do its best
    out = subprocess.run(["fc-match", "-f", "%{family}|%{style}", family], capture_output=True, text=True).stdout
    return out.lower().startswith(family.lower().split()[0])


def run_whisper(wav, workdir, language, model):
    """Transcribe WAV with the whisper CLI; returns the path of the JSON with word times."""
    cmd = ["whisper", str(wav), "--model", model, "--word_timestamps", "True", "--output_format", "json",
           "--output_dir", str(workdir), "--condition_on_previous_text", "False", "--fp16", "False"]
    if language:
        cmd += ["--language", language]
    print("transcribing with whisper (" + model + ") ...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    result = Path(workdir) / (Path(wav).stem + ".json")
    if not result.is_file():
        sys.exit("error: whisper did not write a transcript")
    return result


def qc(out, segs, cap_count, audio_info, width, height, notes):
    """Print the pre-post check. Returns the number of warnings."""
    warn = 0
    rows = []

    def row(ok, label, value, hint=""):
        nonlocal warn
        if not ok:
            warn += 1
        rows.append(f"  {'ok  ' if ok else 'WARN'}  {label:<16}{value}" + (f"   <- {hint}" if hint and not ok else ""))

    v = probe_stream(out, "v")
    row(bool(v) and (v["width"], v["height"]) == (width, height), "frame", f"{v['width']}x{v['height']}" if v else "none")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                               capture_output=True, text=True).stdout.strip())
    row(5 <= dur <= 90, "length", f"{dur:.1f} s", "reels work best between 5 and 90 s")
    if audio_info:
        row(abs(audio_info["lufs_after"] - audio_info["target"]) <= 1.0,
            "loudness", f"{audio_info['lufs_after']:.1f} LUFS, peak {audio_info['true_peak']:.1f} dBFS",
            "far from the target; check the source audio")
        row(audio_info["true_peak"] <= -1.0, "peak", f"{audio_info['true_peak']:.1f} dBFS", "would clip after the platform re-encode")
    lengths = [float(s["end"]) - float(s["start"]) for s in segs]
    if len(segs) > 1:
        row(min(lengths) >= 2.0, "shortest piece", f"{min(lengths):.1f} s ({len(segs) - 1} cuts)",
            "two cuts close together read as a stutter; raise --min-piece in pause-cut")
    else:
        rows.append(f"  ok    {'cuts':<16}none")
    if cap_count is not None:
        rows.append(f"  ok    {'captions':<16}{cap_count} (read them once: the transcript can mishear names)")
    for n in notes:
        warn += 1
        rows.append(f"  WARN  {n}")
    print("check:\n" + "\n".join(rows))
    return warn


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cuts")
    ap.add_argument("--out", required=True)
    ap.add_argument("--srt", help="captions: an .srt or a Whisper .json (word times); times are on the FINAL timeline")
    ap.add_argument("--zoom", type=float, default=0.07, help="zoom amount, 0.07 = 7 percent (0 disables)")
    ap.add_argument("--zoom-style", default="punch", choices=["punch", "alternate", "in", "out", "none"],
                    help="punch = still 1.0x/1.07x alternation (default); alternate/in/out = slow push")
    ap.add_argument("--grade", default="warm", choices=["warm", "none"])
    ap.add_argument("--audio", default="auto", choices=["auto", "light", "full", "none"],
                    help="voice clean-up: auto picks light or full from the room noise; none = untouched")
    ap.add_argument("--lufs", type=float, default=-14.0, help="loudness target (default -14)")
    ap.add_argument("--caption-style", default="clean", choices=sorted(captions.STYLES))
    ap.add_argument("--caption-font", default="Inter Light", help="font family as libass sees it")
    ap.add_argument("--caption-size", type=int, default=52)
    ap.add_argument("--fonts-dir", help="folder with extra fonts for libass (when the font is not installed)")
    ap.add_argument("--transcribe", action="store_true",
                    help="caption the reel automatically with the whisper command-line tool")
    ap.add_argument("--language", default=None, help="spoken language for --transcribe, e.g. ru (default: detect)")
    ap.add_argument("--whisper-model", default="medium", help="whisper model for --transcribe (default medium)")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true", help="print the ffmpeg commands and stop")
    args = ap.parse_args()

    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        sys.exit("error: ffmpeg and ffprobe are required (see docs/setup.md)")
    if args.transcribe and not shutil.which("whisper"):
        sys.exit("error: --transcribe needs the whisper command (pip install openai-whisper); see docs/setup.md")
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
    notes, cmds, vparts, aparts = [], [], [], []
    warned = set()
    for i, seg in enumerate(segs):
        seg["_i"] = i
        src = resolve(seg.get("source") or cuts.get("source", ""))
        if not src.is_file():
            sys.exit(f"error: segment {i + 1}: source {src} not found")
        dur = float(seg["end"]) - float(seg["start"])
        if dur <= 0:
            sys.exit(f"error: segment {i + 1}: end must be after start")
        dur = max(1, round(dur * args.fps)) / args.fps   # whole frames, so picture and sound stay in step across joins
        vs = probe_stream(src, "v")
        if vs and str(src) not in warned and (vs["width"] < width or vs["height"] < height):
            warned.add(str(src))
            notes.append(f"{src.name} is {vs['width']}x{vs['height']}, below {width}x{height}: the picture will be soft "
                         "(shoot with the back camera)")
        frames = max(1, round(dur * args.fps))
        vout, aout = tmp / f"v_{i:03d}.mp4", tmp / f"a_{i:03d}.wav"
        start = f"{float(seg['start']):.3f}"
        cmds.append(["ffmpeg", "-v", "error", "-y", "-ss", start, "-t", f"{dur:.3f}", "-i", str(src), "-an",
                     "-vf", video_filter(seg, args, width, height, args.fps, frames),
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                     "-r", str(args.fps), str(vout)])
        fade = f"afade=t=in:st=0:d={EDGE_FADE},afade=t=out:st={max(0.0, dur - EDGE_FADE):.3f}:d={EDGE_FADE}"
        if has_audio(src):
            cmds.append(["ffmpeg", "-v", "error", "-y", "-ss", start, "-t", f"{dur:.3f}", "-i", str(src), "-vn",
                         "-af", fade, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s24le", str(aout)])
        else:
            cmds.append(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", f"{dur:.3f}", "-i",
                         "anullsrc=r=48000:cl=mono", "-c:a", "pcm_s24le", str(aout)])
        vparts.append(vout)
        aparts.append(aout)

    vlist, alist = tmp / "v.txt", tmp / "a.txt"
    vjoin, ajoin, apol = tmp / "joined_v.mp4", tmp / "joined_a.wav", tmp / "voice.wav"
    joined = tmp / "joined.mp4"
    join_cmds = [
        ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(vlist), "-c", "copy", str(vjoin)],
        ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(alist), "-c", "copy", str(ajoin)],
    ]
    mux_cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(vjoin), "-i", str(apol), "-map", "0:v", "-map", "1:a",
               "-c:v", "copy", "-c:a", "aac", "-ac", "2", "-b:a", "192k", "-movflags", "+faststart", str(joined)]
    final_cmd = None
    ass = tmp / "cap.ass"
    if args.srt or args.transcribe:
        if args.srt and not Path(args.srt).is_file():
            sys.exit(f"error: {args.srt} not found")
        vf = f"ass=cap.ass:fontsdir={Path(args.fonts_dir).resolve()}" if args.fonts_dir else "ass=cap.ass"
        final_cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(joined), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
                     "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                     str(Path(args.out).resolve())]
        if args.caption_style == "clean" and not font_family_present(args.caption_font, args.fonts_dir):
            notes.append(f"font '{args.caption_font}' is not installed: captions fall back to a heavier default font "
                         "(install Inter, or pass --fonts-dir)")

    if args.dry_run:
        for c in cmds + join_cmds + [["(audio polish: audio_polish.py joined_a.wav voice.wav)"], mux_cmd] + ([final_cmd] if final_cmd else []):
            print(" ".join(c))
        shutil.rmtree(tmp, ignore_errors=True)
        return

    for c in cmds:
        subprocess.run(c, check=True)
    vlist.write_text("".join(f"file '{p}'\n" for p in vparts), encoding="utf-8")
    alist.write_text("".join(f"file '{p}'\n" for p in aparts), encoding="utf-8")
    for c in join_cmds:
        subprocess.run(c, check=True)
    audio_info = None
    if args.audio == "none":
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ajoin), "-c", "copy", str(apol)], check=True)
    else:
        audio_info = audio_polish.polish(ajoin, apol, args.audio, args.lufs)
        audio_info["target"] = args.lufs
    subprocess.run(mux_cmd, check=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    cap_count = None
    if final_cmd:
        transcript = args.srt
        if args.transcribe:
            transcript = run_whisper(apol, tmp, args.language, args.whisper_model)
        words = captions.load_words(transcript)
        pages = captions.paginate(words)
        if args.transcribe:   # never overwrite a transcript the user passed in with --srt
            Path(args.out).with_suffix(".srt").write_text(captions.pages_to_srt(pages), encoding="utf-8")
        cap_count = captions.make_ass(transcript, ass, args.caption_font, args.caption_size, style=args.caption_style)
        subprocess.run(final_cmd, check=True, cwd=tmp)
    else:
        shutil.copy(joined, args.out)
    shutil.rmtree(tmp, ignore_errors=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", args.out],
                         capture_output=True, text=True).stdout.strip()
    print(f"wrote {args.out}  ({len(segs)} segments, {float(dur):.1f} s, {width}x{height})")
    qc(args.out, segs, cap_count, audio_info, width, height, notes)


if __name__ == "__main__":
    main()
