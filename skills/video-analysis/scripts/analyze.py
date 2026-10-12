#!/usr/bin/env python3
"""Analyze a YouTube video, Short or Instagram reel (link or local file): numbers, edit rhythm, sound, hook.

Usage:
  analyze.py run SOURCE --out DIR [--transcribe] [--hook-seconds 5] [--max-seconds 600]
                        [--cookies cookies.txt] [--threshold 0.3] [--allow-long]
  analyze.py compare DIR [DIR ...]

SOURCE is a link (downloaded with yt-dlp) or a video file on disk.
`run` writes DIR/report.md, DIR/analysis.json, DIR/frames/ (one frame per shot) and, for links, DIR/source.mp4.
`compare` prints one table for several finished analyses, so you look for a pattern across videos, not in one.

Needs ffmpeg and ffprobe; links need yt-dlp; --transcribe needs the `whisper` command (openai-whisper).
Only use this on videos for private study. Platforms restrict downloading in their terms: check them.
"""
import argparse
import json
import re
import shutil
import statistics
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


def run(cmd, check=True, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=timeout)


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------- download and metadata (yt-dlp) ----------

def ytdlp_cmd(args_extra, cookies):
    exe = shutil.which("yt-dlp")
    if not exe:
        die("yt-dlp is not installed (pip install yt-dlp, or your package manager); see docs/setup.md")
    cmd = [exe, "--no-playlist", "--no-warnings"]
    if cookies:
        cmd += ["--cookies", cookies]
    return cmd + args_extra


def fetch_metadata(url, cookies):
    res = run(ytdlp_cmd(["--dump-single-json", "--skip-download", url], cookies), check=False, timeout=120)
    if res.returncode != 0:
        die(f"could not read the link: {res.stderr.strip()[-300:]}\n"
            "hint: YouTube and Instagram often need cookies (--cookies cookies.txt) from a logged-in browser")
    d = json.loads(res.stdout)
    return {
        "title": d.get("title"), "channel": d.get("channel") or d.get("uploader"),
        "followers": d.get("channel_follower_count"), "views": d.get("view_count"),
        "likes": d.get("like_count"), "comments": d.get("comment_count"),
        "duration": d.get("duration"), "upload_date": d.get("upload_date"),
        "url": d.get("webpage_url") or url, "id": d.get("id"), "platform": d.get("extractor_key"),
        "description": (d.get("description") or "")[:300],
    }


def download(url, out_dir, cookies):
    template = str(out_dir / "source.%(ext)s")
    cmd = ytdlp_cmd(["-f", "bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b", "--merge-output-format", "mp4",
                     "-o", template, url], cookies)
    res = run(cmd, check=False, timeout=900)
    if res.returncode != 0:
        die(f"download failed: {res.stderr.strip()[-300:]}")
    found = sorted(out_dir.glob("source.*"))
    if not found:
        die("download finished but no file was written")
    return found[0]


# ---------- measuring ----------

def probe(video):
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "format=duration:stream=codec_type,width,height,r_frame_rate", "-of", "json", str(video)]).stdout
    data = json.loads(out)
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    num, _, den = v.get("r_frame_rate", "0/1").partition("/")
    fps = round(float(num) / float(den), 2) if float(den or 1) else 0.0
    return {"duration": float(data["format"]["duration"]), "width": v.get("width"), "height": v.get("height"),
            "fps": fps, "has_audio": any(s.get("codec_type") == "audio" for s in streams)}


def find_cuts(video, threshold):
    res = run(["ffmpeg", "-hide_banner", "-i", str(video), "-an", "-vf",
               f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"], check=False)
    return sorted({round(float(m.group(1)), 3) for m in re.finditer(r"pts_time:([0-9.]+)", res.stderr)})


def build_shots(cuts, duration, min_shot=0.2):
    edges = [0.0]
    for c in cuts:
        if c - edges[-1] >= min_shot and duration - c >= min_shot:
            edges.append(c)
    edges.append(duration)
    return [{"index": i + 1, "start": round(a, 3), "end": round(b, 3), "length": round(b - a, 3)}
            for i, (a, b) in enumerate(zip(edges, edges[1:]))]


def shot_frame_and_color(video, shot, frames_dir):
    t = shot["start"] + min(0.5, shot["length"] / 2)
    name = f"shot_{shot['index']:02d}_t{shot['start']:06.2f}.jpg"
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
         "-vf", "scale=360:-2", str(frames_dir / name)], check=False)
    shot["frame"] = f"frames/{name}"
    px = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                         "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                        capture_output=True).stdout
    shot["avg_color"] = "#%02x%02x%02x" % tuple(px[:3]) if len(px) >= 3 else None


def loudness(video):
    res = run(["ffmpeg", "-hide_banner", "-i", str(video), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
              check=False)
    m = re.findall(r"I:\s+(-?[0-9.]+) LUFS", res.stderr)
    p = re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", res.stderr)
    return {"integrated_lufs": float(m[-1]) if m else None, "true_peak_dbfs": float(p[-1]) if p else None}


def transcribe(video, out_dir, hook_seconds):
    """Return (hook_text, full_text, words_per_second) or (None, None, None) without whisper."""
    exe = shutil.which("whisper")
    if not exe:
        return None, None, None
    wdir = out_dir / "whisper"
    wdir.mkdir(exist_ok=True)
    run([exe, str(video), "--model", "small", "--output_format", "json", "--output_dir", str(wdir),
         "--fp16", "False"], check=False)
    js = wdir / (Path(video).stem + ".json")
    if not js.exists():
        return None, None, None
    segs = json.loads(js.read_text(encoding="utf-8")).get("segments", [])
    hook = " ".join(s["text"].strip() for s in segs if s["start"] < hook_seconds).strip()
    full = " ".join(s["text"].strip() for s in segs).strip()
    speaking = sum(max(0.0, s["end"] - s["start"]) for s in segs)
    wps = round(len(full.split()) / speaking, 2) if speaking > 0 else None
    return hook, full, wps


# ---------- commands ----------

def cmd_run(args):
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        die("ffmpeg and ffprobe are required (see docs/setup.md)")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    meta = {}
    if re.match(r"^https?://", args.source):
        meta = fetch_metadata(args.source, args.cookies)
        dur = meta.get("duration")
        if dur and dur > args.max_seconds and not args.allow_long:
            die(f"the video is {dur:.0f} s, over --max-seconds {args.max_seconds}; add --allow-long to go on")
        video = download(args.source, out, args.cookies)
    else:
        video = Path(args.source)
        if not video.is_file():
            die(f"{video} not found")
        meta = {"title": video.stem, "url": None, "platform": "local file"}

    info = probe(video)
    shots = build_shots(find_cuts(video, args.threshold), info["duration"])
    frames_dir = out / "frames"
    frames_dir.mkdir(exist_ok=True)
    for s in shots:
        shot_frame_and_color(video, s, frames_dir)
    lengths = [s["length"] for s in shots]
    stats = {"shots": len(shots),
             "cuts_per_minute": round((len(shots) - 1) / info["duration"] * 60, 1),
             "mean_shot": round(statistics.mean(lengths), 2), "median_shot": round(statistics.median(lengths), 2),
             "shortest": min(lengths), "longest": max(lengths)}
    sound = loudness(video) if info["has_audio"] else {"integrated_lufs": None, "true_peak_dbfs": None}

    hook = full = wps = None
    if args.transcribe:
        hook, full, wps = transcribe(video, out, args.hook_seconds)
        if full:
            (out / "transcript.txt").write_text(full + "\n", encoding="utf-8")

    numbers = {}
    if meta.get("views") is not None:
        v = meta["views"]
        numbers = {"views": v, "likes": meta.get("likes"), "comments": meta.get("comments"),
                   "like_rate": round(meta["likes"] / v, 4) if meta.get("likes") is not None and v else None,
                   "comment_rate": round(meta["comments"] / v, 5) if meta.get("comments") is not None and v else None}
        ud = meta.get("upload_date")
        if ud and v:
            try:
                age = (date.today() - datetime.strptime(ud, "%Y%m%d").date()).days
                numbers["age_days"] = age
                vpd = v / max(age, 1)
                numbers["views_per_day"] = round(vpd) if vpd >= 10 else round(vpd, 2)
            except ValueError:
                pass
    result = {"source": meta, "numbers": numbers, "video": {**info, "file": video.name}, "edit": stats,
              "sound": {**sound, "words_per_second": wps}, "hook_seconds": args.hook_seconds,
              "hook_text": hook, "shots": shots}
    (out / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_report(out, result, args)
    print(f"{stats['shots']} shots, {stats['cuts_per_minute']} cuts/min, median shot {stats['median_shot']} s")
    print(f"wrote {out / 'report.md'}")


def write_report(out, r, args):
    m, n, v, e, s = r["source"], r["numbers"], r["video"], r["edit"], r["sound"]
    if r["hook_text"] is None:
        why = "whisper is not installed" if args.transcribe else "run with --transcribe"
        hook = f"not transcribed ({why}); do not describe the hook from frames"
    else:
        hook = f"«{r['hook_text']}»" if r["hook_text"] else "no speech in this window"
    L = [f"# Analysis: {m.get('title') or v['file']}", ""]
    src = [f"- Source: {m.get('platform')}" + (f", {m['url']}" if m.get("url") else "")]
    if m.get("channel"):
        src.append(f"- Channel: {m['channel']}" + (f" ({m['followers']:,} followers)" if m.get("followers") else
                                                      " (follower count unknown: numbers are not comparable)"))
    if m.get("upload_date"):
        src.append(f"- Uploaded: {m['upload_date']}")
    L += src + [""]
    if n:
        L += ["## Numbers", f"- Views {n['views']:,}" + (f", likes {n['likes']:,}" if n.get("likes") is not None else "")
              + (f", comments {n['comments']:,}" if n.get("comments") is not None else ""),
              ]
        if n.get("like_rate") is not None:
            L.append(f"- Like rate {n['like_rate'] * 100:.2f}%, comment rate {(n.get('comment_rate') or 0) * 100:.3f}%")
        if n.get("views_per_day") is not None:
            L.append(f"- {n['age_days']} days old, about {n['views_per_day']:,} views per day")
        L.append("")
    L += ["## Edit",
          f"- {v['width']}x{v['height']} at {v['fps']} fps, {v['duration']:.1f} s",
          f"- {e['shots']} shots, {e['cuts_per_minute']} cuts per minute",
          f"- Shot length: mean {e['mean_shot']} s, median {e['median_shot']} s, shortest {e['shortest']} s, "
          f"longest {e['longest']} s", "",
          "## Sound",
          f"- Audio: {'yes' if v['has_audio'] else 'NO AUDIO STREAM (Instagram downloads are often video-only)'}"]
    if s.get("integrated_lufs") is not None:
        L.append(f"- Loudness {s['integrated_lufs']} LUFS, true peak {s['true_peak_dbfs']} dBFS")
    if s.get("words_per_second") is not None:
        L.append(f"- Speech rate about {s['words_per_second']} words per second")
    L += ["", f"## Hook (first {r['hook_seconds']:g} s)", f"- {hook}", "",
          "## Shots", "| # | start | length | average colour | frame |", "|---|---|---|---|---|"]
    L += [f"| {x['index']} | {x['start']:.2f} | {x['length']:.2f} | {x.get('avg_color') or '-'} | {x['frame']} |"
          for x in r["shots"]]
    L += ["", "## Your notes (fill in after watching)",
          "- What the first 3 seconds promise:", "- Where the picture changes without a cut:",
          "- What to repeat in your own video:", "- What to skip:", "",
          "One video is an observation. Compare at least three before calling anything a pattern "
          "(`analyze.py compare DIR DIR DIR`)."]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def cmd_compare(args):
    rows = []
    for d in args.dirs:
        p = Path(d) / "analysis.json"
        if not p.is_file():
            die(f"{p} not found; run `analyze.py run` first")
        r = json.loads(p.read_text(encoding="utf-8"))
        rows.append(r)
    print("| video | length s | shots | cuts/min | median shot s | words/s | LUFS | views | hook |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        title = (r["source"].get("title") or r["video"]["file"])[:32]
        hook = (r.get("hook_text") or "")[:50]
        print(f"| {title} | {r['video']['duration']:.0f} | {r['edit']['shots']} | {r['edit']['cuts_per_minute']} | "
              f"{r['edit']['median_shot']} | {r['sound'].get('words_per_second') or '-'} | "
              f"{r['sound'].get('integrated_lufs') or '-'} | {r['numbers'].get('views') or '-'} | {hook} |")
    if len(rows) >= 2:
        med = statistics.median(r["edit"]["median_shot"] for r in rows)
        cpm = statistics.median(r["edit"]["cuts_per_minute"] for r in rows)
        print(f"\nAcross {len(rows)} videos: median shot {med} s, median {cpm} cuts per minute.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="analyze one video (link or file)")
    r.add_argument("source")
    r.add_argument("--out", required=True)
    r.add_argument("--transcribe", action="store_true")
    r.add_argument("--hook-seconds", type=float, default=5.0)
    r.add_argument("--max-seconds", type=int, default=600)
    r.add_argument("--allow-long", action="store_true")
    r.add_argument("--cookies", help="Netscape cookies.txt for yt-dlp (YouTube and Instagram often need it)")
    r.add_argument("--threshold", type=float, default=0.3, help="scene-change score (lower finds more cuts)")
    c = sub.add_parser("compare", help="one table for several analyses")
    c.add_argument("dirs", nargs="+")
    args = ap.parse_args()
    cmd_run(args) if args.cmd == "run" else cmd_compare(args)


if __name__ == "__main__":
    main()
