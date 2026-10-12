#!/usr/bin/env bash
# Check the tools reel-skills needs. Exit 1 if a required tool is missing; optional tools only print a note.
set -u

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: scripts/doctor.sh"
  echo "Checks python3 (3.10+), ffmpeg and ffprobe (required); whisper and pandoc (optional)."
  exit 0
fi

fail=0
ok()   { printf 'OK       %s\n' "$1"; }
miss() { printf 'MISSING  %s (%s)\n' "$1" "$2"; }

if command -v python3 >/dev/null 2>&1; then
  ver=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    ok "python3 $ver"
  else
    miss "python3 3.10+" "found $ver; see docs/setup.md"; fail=1
  fi
else
  miss "python3" "required; see docs/setup.md"; fail=1
fi

for tool in ffmpeg ffprobe; do
  if command -v "$tool" >/dev/null 2>&1; then
    ok "$tool"
  else
    miss "$tool" "required; see docs/setup.md"; fail=1
  fi
done

for tool in whisper pandoc; do
  if command -v "$tool" >/dev/null 2>&1; then
    ok "$tool (optional)"
  else
    echo "note     $tool not installed (optional; see docs/setup.md)"
  fi
done

exit $fail
