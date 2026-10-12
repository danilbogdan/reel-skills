#!/usr/bin/env bash
# Make a synthetic test clip in samples/: four 3-second scenes (3 cuts) and a tone that "speaks" for 1.5 s
# then pauses for 1.5 s (pauses to cut). No people and no personal media; the whole demo runs on it.
set -euo pipefail

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: scripts/make_sample.sh"
  echo "Writes samples/sample.mp4 (1080x1920, 30 fps, 12 s: 4 scenes, tone with pauses)."
  exit 0
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$root/samples"
out="$root/samples/sample.mp4"

ffmpeg -v error -y \
  -f lavfi -i "testsrc2=size=1080x1920:rate=30:duration=3" \
  -f lavfi -i "smptebars=size=1080x1920:rate=30:duration=3" \
  -f lavfi -i "color=c=0x3a6ea5:size=1080x1920:rate=30:duration=3" \
  -f lavfi -i "rgbtestsrc=size=1080x1920:rate=30:duration=3" \
  -f lavfi -i "aevalsrc='if(lt(mod(t,3),1.5),0.5*sin(2*PI*440*t),0)':s=48000:d=12" \
  -filter_complex "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0,format=yuv420p[v]" \
  -map "[v]" -map 4:a -c:v libx264 -preset veryfast -c:a aac -b:a 128k -shortest "$out"

echo "wrote $out"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$out"
