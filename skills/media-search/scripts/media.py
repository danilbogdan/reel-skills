#!/usr/bin/env python3
"""Search and download free media: Pixabay images and videos, Freesound sound effects, Jamendo music.

Usage:
  media.py search SOURCE QUERY [--limit 10] [--instrumental]
  media.py get SOURCE ID --out DIR

SOURCE is one of: pixabay-image, pixabay-video, freesound, jamendo.
Keys come from environment variables (never from files in this repo):
  PIXABAY_API_KEY, FREESOUND_API_KEY (or FREESOUND_API_TOKEN), JAMENDO_CLIENT_ID

Every result shows its license. `get` saves the file plus <file>.json with the license, credit and item page.
Search results are cached for 24 hours (Pixabay requires it); do not run mass downloads.
Standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "reel-skills-media/0.1"
CACHE = Path.home() / ".cache" / "reel-skills-media"
SOURCES = ("pixabay-image", "pixabay-video", "freesound", "jamendo")


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def key_for(source):
    names = {"pixabay-image": ["PIXABAY_API_KEY"], "pixabay-video": ["PIXABAY_API_KEY"],
             "freesound": ["FREESOUND_API_KEY", "FREESOUND_API_TOKEN"], "jamendo": ["JAMENDO_CLIENT_ID"]}[source]
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    die(f"no key for {source}: set {names[0]} (see docs/setup.md)", 2)


def get_json(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    if f.exists() and time.time() - f.stat().st_mtime < 24 * 3600:
        return json.loads(f.read_text(encoding="utf-8"))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        die("rate limited, wait a minute" if e.code == 429 else f"HTTP {e.code}: {e.read()[:200].decode('utf-8', 'replace')}")
    except urllib.error.URLError as e:
        die(f"network error: {e.reason}")
    if data.get("results") != [] and data.get("hits") != []:      # never cache an empty answer
        f.write_text(json.dumps(data), encoding="utf-8")
    return data


def cc(label):
    m = re.search(r"creativecommons\.org/(publicdomain/zero|licenses/(by[-a-z]*)/([0-9.]+))", label or "")
    if not m:
        return label or "unknown"
    return "cc0" if "zero" in m.group(1) else f"cc-{m.group(2)}-{m.group(3)}"


def rows_for(source, query, limit, instrumental, item_id=None):
    k = key_for(source)
    q = urllib.parse.quote_plus
    if source.startswith("pixabay"):
        base = "https://pixabay.com/api/" + ("videos/" if source.endswith("video") else "")
        sel = f"id={item_id}" if item_id else f"q={q(query)}&per_page={max(3, min(limit, 50))}&safesearch=true"
        hits = get_json(f"{base}?key={k}&{sel}").get("hits", [])
        out = []
        for h in hits:
            if source.endswith("video"):
                v = h.get("videos", {})
                url = (v.get("large") or v.get("medium") or v.get("small") or {}).get("url", "")
                ext = ".mp4"
            else:
                url, ext = h.get("largeImageURL", ""), ".jpg"
            out.append({"id": str(h["id"]), "title": h.get("tags", ""), "creator": h.get("user", ""),
                        "duration": h.get("duration"), "license": "pixabay-content-license",
                        "page": h.get("pageURL", ""), "url": url, "ext": ext,
                        "credit": f"By {h.get('user', '?')} on Pixabay"})
        return out
    if source == "freesound":
        fields = "id,name,username,duration,license,url,previews"
        if item_id:
            data = get_json(f"https://freesound.org/apiv2/sounds/{item_id}/?token={k}&fields={fields}")
            results = [data]
        else:
            data = get_json(f"https://freesound.org/apiv2/search/text/?token={k}&query={q(query)}"
                            f"&page_size={limit}&fields={fields}")
            results = data.get("results", [])
        return [{"id": str(s["id"]), "title": s.get("name", ""), "creator": s.get("username", ""),
                 "duration": s.get("duration"), "license": cc(s.get("license")), "page": s.get("url", ""),
                 "url": (s.get("previews") or {}).get("preview-hq-mp3", ""), "ext": ".mp3",
                 "credit": f"{s.get('username', '?')} on Freesound"} for s in results]
    # jamendo
    params = f"client_id={k}&format=json&include=musicinfo"
    params += f"&id={item_id}" if item_id else f"&search={q(query)}&limit={limit}" + \
        ("&vocalinstrumental=instrumental" if instrumental else "")
    data = get_json(f"https://api.jamendo.com/v3.0/tracks/?{params}")
    return [{"id": str(t["id"]), "title": t.get("name", ""), "creator": t.get("artist_name", ""),
             "duration": t.get("duration"), "license": cc(t.get("license_ccurl")), "page": t.get("shareurl", ""),
             "url": t.get("audiodownload", "") if t.get("audiodownload_allowed") else "", "ext": ".mp3",
             "credit": f"{t.get('artist_name', '?')} - {t.get('name', '')} (Jamendo)"}
            for t in data.get("results", [])]


def with_retry(*a, **kw):
    rows = rows_for(*a, **kw)
    if not rows:                       # Jamendo sometimes answers empty once; try again
        time.sleep(2)
        rows = rows_for(*a, **kw)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("source", choices=SOURCES)
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--instrumental", action="store_true", help="Jamendo: no vocals")
    g = sub.add_parser("get")
    g.add_argument("source", choices=SOURCES)
    g.add_argument("id")
    g.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.cmd == "search":
        rows = with_retry(args.source, args.query, args.limit, args.instrumental)
        for r in rows:
            dur = f"{float(r['duration']):.0f}s" if r.get("duration") else "-"
            flag = "" if r["url"] else "  [no download]"
            print(f"{r['id']:>10}  {dur:>5}  {r['license']:<24} {r['creator']} - {r['title'][:60]}{flag}")
            print(f"            {r['page']}")
        print(f"{len(rows)} result(s). Check the license line before you use a file.")
        return

    rows = with_retry(args.source, "", 1, False, item_id=args.id)
    if not rows:
        die(f"{args.source} item {args.id} not found")
    r = rows[0]
    if not r["url"]:
        die("this item has no downloadable file")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{args.source}-{r['id']}") + r["ext"]
    req = urllib.request.Request(r["url"], headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            (out / name).write_bytes(resp.read())
    except urllib.error.URLError as e:
        die(f"download failed: {e}")
    meta = {k: r[k] for k in ("id", "title", "creator", "license", "credit", "page")} | {"source": args.source}
    (out / (name + ".json")).write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"saved {out / name}")
    print(f"license {r['license']} | credit: {r['credit']} | {r['page']}")


if __name__ == "__main__":
    main()
