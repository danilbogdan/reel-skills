#!/usr/bin/env python3
"""Index a folder of b-roll clips and search the index by words.

Usage:
  broll.py index FOLDER [--out index.json]
  broll.py search --index index.json WORD [WORD ...] [--min-seconds 2] [--portrait | --landscape]

index: reads every video file under FOLDER with ffprobe (duration, size, fps, orientation) and builds tags
       from the folder and file names (rain, cafe, night ...). Re-running keeps the "description" you added
       by hand to an entry, so you can enrich the index over time.
search: all WORDs must appear in the tags, the description or the path.
Needs ffprobe.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}


def probe(path):
    res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:stream_side_data=rotation:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True)
    if res.returncode != 0:
        return None
    data = json.loads(res.stdout or "{}")
    st = (data.get("streams") or [{}])[0]
    w, h = st.get("width"), st.get("height")
    rot = 0
    for sd in st.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, _, den = st.get("r_frame_rate", "0/1").partition("/")
    fps = round(float(num) / float(den), 2) if float(den or 0) else 0.0
    return {"duration": round(float(data.get("format", {}).get("duration", 0)), 2),
            "width": w, "height": h, "fps": fps,
            "orientation": "portrait" if (h or 0) > (w or 0) else "landscape"}


def tags_from(rel):
    toks = re.split(r"[^A-Za-zА-Яа-яЁё]+", str(rel.with_suffix("")))
    return sorted({t.lower() for t in toks if len(t) >= 3})


def cmd_index(args):
    root = Path(args.folder)
    if not root.is_dir():
        sys.exit(f"error: {root} is not a folder")
    out = Path(args.out)
    old = {}
    if out.exists():
        old = {e["path"]: e for e in json.loads(out.read_text(encoding="utf-8"))}
    entries = []
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() not in VIDEO_EXT or not p.is_file():
            continue
        info = probe(p)
        if not info:
            print(f"skip (unreadable): {p}", file=sys.stderr)
            continue
        rel = p.relative_to(root)
        entry = {"path": str(p), "tags": tags_from(rel), **info,
                 "size_mb": round(p.stat().st_size / 1e6, 1),
                 "description": old.get(str(p), {}).get("description", "")}
        entries.append(entry)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = sum(e["duration"] for e in entries)
    print(f"{len(entries)} clips, {total / 60:.1f} min -> {out}")
    print("add a short \"description\" to entries you will reuse; search looks at it too")


def cmd_search(args):
    idx = Path(args.index)
    if not idx.is_file():
        sys.exit(f"error: {idx} not found; run `broll.py index FOLDER` first")
    entries = json.loads(idx.read_text(encoding="utf-8"))
    words = [w.lower() for w in args.words]
    hits = []
    for e in entries:
        hay = " ".join(e["tags"] + [e.get("description", ""), e["path"]]).lower()
        if not all(w in hay for w in words):
            continue
        if e["duration"] < args.min_seconds:
            continue
        if args.portrait and e["orientation"] != "portrait":
            continue
        if args.landscape and e["orientation"] != "landscape":
            continue
        hits.append(e)
    for e in hits:
        print(f"{e['duration']:6.1f}s  {e['width']}x{e['height']}  {e['path']}")
    print(f"{len(hits)} match(es)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("index")
    a.add_argument("folder")
    a.add_argument("--out", default="index.json")
    b = sub.add_parser("search")
    b.add_argument("words", nargs="+")
    b.add_argument("--index", default="index.json")
    b.add_argument("--min-seconds", type=float, default=0.0)
    b.add_argument("--portrait", action="store_true")
    b.add_argument("--landscape", action="store_true")
    args = ap.parse_args()
    cmd_index(args) if args.cmd == "index" else cmd_search(args)


if __name__ == "__main__":
    main()
