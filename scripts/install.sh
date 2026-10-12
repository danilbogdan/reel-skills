#!/usr/bin/env bash
# Link every skill in skills/ (folders not starting with "_") into a skills folder.
# Only symlinks are replaced by --force; a real folder with the same name is never touched.
#   scripts/install.sh [--force] [DEST]        DEST defaults to ~/.claude/skills
set -euo pipefail

force=0
dest=""
for arg in "$@"; do
  case "$arg" in
    --force) force=1 ;;
    -h|--help)
      echo "Usage: scripts/install.sh [--force] [DEST]   (default DEST: ~/.claude/skills)"
      exit 0 ;;
    *) dest="$arg" ;;
  esac
done
dest="${dest:-$HOME/.claude/skills}"
src="$(cd "$(dirname "$0")/.." && pwd)/skills"

mkdir -p "$dest"
count=0
for d in "$src"/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  case "$name" in _*) continue ;; esac
  target="$dest/$name"
  if [ -L "$target" ]; then
    if [ "$force" = 1 ] || [ "$(readlink "$target")" != "${d%/}" ]; then
      rm "$target"
    else
      count=$((count + 1)); continue
    fi
  elif [ -e "$target" ]; then
    echo "skip (a real folder is already there): $target"; continue
  fi
  ln -s "${d%/}" "$target"
  echo "linked: $name -> $target"
  count=$((count + 1))
done
echo "$count skill(s) in $dest"
