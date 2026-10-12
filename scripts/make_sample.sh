#!/usr/bin/env bash
# Make a synthetic test clip (test pattern and a tone) in samples/. Contains no people and no personal media.
set -euo pipefail

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: scripts/make_sample.sh [seconds]"
  echo "Writes samples/sample.mp4 (1080x1920, 30 fps, default 10 s) and prints its duration."
  exit 0
fi

secs="${1:-10}"
root="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$root/samples"
out="$root/samples/sample.mp4"

ffmpeg -v error -y \
  -f lavfi -i "testsrc2=size=1080x1920:rate=30" \
  -f lavfi -i "sine=frequency=440:sample_rate=48000" \
  -t "$secs" -c:v libx264 -preset veryfast -pix_fmt yuv420p \
  -c:a aac -b:a 128k -shortest "$out"

echo "wrote $out"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$out"
