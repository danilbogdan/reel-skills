#!/usr/bin/env bash
# Run the whole pipeline on the synthetic sample clip: analysis -> pause-cut -> render -> hook check.
# Everything is written to workspace/demo (git-ignored). Use it to confirm your machine can reproduce the steps.
set -euo pipefail

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: scripts/run_demo.sh"
  echo "Makes samples/sample.mp4 if needed, then runs video-analysis, pause-cut, reel-render and hook-lint on it."
  exit 0
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
[ -f samples/sample.mp4 ] || scripts/make_sample.sh

out=workspace/demo
rm -rf "$out"
mkdir -p "$out"

echo "== 1. video-analysis (study a video)"
python3 skills/video-analysis/scripts/analyze.py run samples/sample.mp4 --out "$out/analysis"

echo "== 2. pause-cut (plan the cut)"
python3 skills/pause-cut/scripts/pause_cut.py samples/sample.mp4 --out "$out/cuts.json"

echo "== 3. render (build the reel)"
python3 skills/reel-render/scripts/render.py "$out/cuts.json" --out "$out/reel.mp4"

echo "== 4. hook-lint (check the hook)"
python3 skills/hook-lint/scripts/hook_lint.py "A clean kitchen in 15 minutes" --spoken "It used to take me a whole evening."

size="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$out/reel.mp4")"
dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out/reel.mp4")"
if [ "$size" != "1080x1920" ]; then
  echo "FAIL: expected 1080x1920, got $size"; exit 1
fi
echo
echo "demo ok: $out/reel.mp4 is $size, ${dur%.*} s"
