#!/usr/bin/env python3
"""Turn a transcript into quiet, readable captions (an ASS file for ffmpeg/libass).

Usage:
  captions.py TRANSCRIPT --out captions.ass [--font "Inter Light"] [--size 52] [--margin 420]
              [--max-chars 30] [--max-lines 2] [--style clean|bold]

TRANSCRIPT is an .srt (any tool), or a Whisper .json written with --word_timestamps True (exact word times).
Times must be on the FINAL timeline (the one after the cuts).

The "clean" style (default) follows the creator's brief: thin font, white, a soft dark halo instead of a hard
outline (contrast stays on any background), no pop, no colour change, no animation; a caption appears and goes.
Two lines at most, placed above the area the app covers with its own buttons. "bold" is the old heavy look
(thick outline), kept for comparison. Pure standard library.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SENTENCE_END = re.compile(r"[.!?…]$")
CLAUSE_END = re.compile(r"[,;:—–-]$")


def srt_time(text):
    h, m, rest = text.strip().split(":")
    s, ms = rest.replace(",", ".").split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000


def parse_srt(text):
    """[(start, end, text)] from an SRT."""
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        for k, ln in enumerate(lines):
            if "-->" in ln:
                a, b = ln.split("-->")
                body = " ".join(x.strip() for x in lines[k + 1:])
                if body:
                    cues.append((srt_time(a), srt_time(b.split()[0]), body))
                break
    return cues


def words_from_srt(cues):
    """Spread each cue's words over its time by character count (no word times in an SRT)."""
    words = []
    for start, end, text in cues:
        parts = text.split()
        total = sum(len(p) + 1 for p in parts) or 1
        t = start
        for p in parts:
            dur = (end - start) * (len(p) + 1) / total
            words.append({"text": p, "start": t, "end": t + dur})
            t += dur
    return words


def words_from_whisper(data):
    words = []
    for seg in data.get("segments", []):
        for w in seg.get("words", []):
            text = w.get("word", w.get("text", "")).strip()
            if text:
                words.append({"text": text, "start": float(w["start"]), "end": float(w["end"])})
    return words


def load_words(path):
    p = Path(path)
    if not p.is_file():
        sys.exit(f"error: {p} not found")
    raw = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        words = words_from_whisper(json.loads(raw))
        if not words:
            sys.exit("error: no word timings in the JSON; run whisper with --word_timestamps True")
        return words
    return words_from_srt(parse_srt(raw))


def paginate(words, max_chars=30, max_lines=2, gap=0.6, hold=0.15):
    """Group words into pages of at most max_lines lines of max_chars. Breaks at sentence ends, at a clause
    end once the page has three words or more, and at pauses longer than gap. A page stays `hold` seconds after
    its last word, never into the next page."""
    limit = max_chars * max_lines
    pages, cur = [], []

    def flush():
        if cur:
            pages.append(list(cur))
            cur.clear()

    for i, w in enumerate(words):
        if cur:
            chars = sum(len(x["text"]) + 1 for x in cur) + len(w["text"])
            prev = cur[-1]
            if (chars > limit or w["start"] - prev["end"] > gap or SENTENCE_END.search(prev["text"])
                    or (CLAUSE_END.search(prev["text"]) and len(cur) >= 3)):
                flush()
        cur.append(w)
    flush()
    out = []
    for k, page in enumerate(pages):
        start, end = page[0]["start"], page[-1]["end"] + hold
        if k + 1 < len(pages):
            end = min(end, pages[k + 1][0]["start"])
        out.append({"start": start, "end": max(end, start + 0.3), "text": wrap([x["text"] for x in page], max_chars, max_lines)})
    return out


def wrap(tokens, max_chars, max_lines):
    """Balanced line breaks: the split that leaves the lines closest in length (ASS \\N)."""
    text = " ".join(tokens)
    if len(text) <= max_chars or max_lines < 2 or len(tokens) < 2:
        return text
    best, best_diff = None, None
    for k in range(1, len(tokens)):
        a, b = " ".join(tokens[:k]), " ".join(tokens[k:])
        if len(a) > max_chars or len(b) > max_chars:
            continue
        diff = abs(len(a) - len(b))
        if best_diff is None or diff < best_diff:
            best, best_diff = f"{a}\\N{b}", diff
    return best or text


def srt_stamp(t):
    ms = int(round(max(0.0, t) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def pages_to_srt(pages):
    """The pages as an SRT, for a read-through and hand fixes (render again with --srt)."""
    return "\n".join(f"{i}\n{srt_stamp(p['start'])} --> {srt_stamp(p['end'])}\n{p['text'].replace(chr(92) + 'N', chr(10))}\n"
                     for i, p in enumerate(pages, 1))


def ass_time(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_escape(text):
    return text.replace("{", "(").replace("}", ")")


STYLES = {
    # white, thin, soft dark halo (border at ~55% transparency, blurred) -> contrast without a hard stroke
    "clean": {"override": r"{\bord3\3c&H000000&\3a&H70&\blur5\shad0}", "outline": 0, "bold": 0},
    # heavy white with a black stroke (the old look)
    "bold": {"override": "", "outline": 4, "bold": -1},
}


def build_ass(pages, font, size, margin, style, width=1080, height=1920):
    s = STYLES[style]
    head = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Cap,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,{s['bold']},0,0,0,100,100,0.4,0,1,"
        f"{s['outline']},0,2,90,90,{margin},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = [f"Dialogue: 0,{ass_time(p['start'])},{ass_time(p['end'])},Cap,,0,0,0,,{s['override']}{ass_escape(p['text'])}"
             for p in pages]
    return head + "\n".join(lines) + "\n"


def make_ass(transcript, out, font="Inter Light", size=52, margin=420, max_chars=30, max_lines=2, style="clean"):
    """Write OUT (.ass) from TRANSCRIPT; returns the number of captions."""
    pages = paginate(load_words(transcript), max_chars, max_lines)
    Path(out).write_text(build_ass(pages, font, size, margin, style), encoding="utf-8")
    return len(pages)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcript")
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", default="Inter Light", help="font family as libass sees it (default 'Inter Light')")
    ap.add_argument("--size", type=int, default=52, help="font size on a 1080 px wide frame (default 52)")
    ap.add_argument("--margin", type=int, default=420, help="distance of the text bottom from the frame bottom")
    ap.add_argument("--max-chars", type=int, default=30, help="characters per line (default 30)")
    ap.add_argument("--max-lines", type=int, default=2)
    ap.add_argument("--style", default="clean", choices=sorted(STYLES))
    args = ap.parse_args()
    n = make_ass(args.transcript, args.out, args.font, args.size, args.margin, args.max_chars, args.max_lines,
                 args.style)
    print(f"wrote {args.out} ({n} captions)")


if __name__ == "__main__":
    main()
