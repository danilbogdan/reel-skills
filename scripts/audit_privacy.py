#!/usr/bin/env python3
"""Scan the repo for secrets and personal data before sharing.

Checks: key/token patterns, private keys, emails, IPv4 addresses, absolute home paths,
and every term in .privacy-denylist.local (gitignored, one term per line, case-insensitive).
Lines containing 'privacy-ok' are ignored. Exit code 1 on any finding.

Usage: audit_privacy.py [--root DIR]
"""
import re, sys, argparse
from pathlib import Path

PATTERNS = {
    "api-key": re.compile(r"\b(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,})"),
    "private-key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "secret-assign": re.compile(r"(?i)\b(secret|token|password|passwd|api[_-]?key|client[_-]?secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-/+=]{16,}"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.(com|org)|users\.noreply)[A-Za-z0-9.-]+\.[a-z]{2,}\b"),
    "ipv4": re.compile(r"\b(?!(?:127|0|10)\.)(?!192\.168\.)(?!255\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    "home-path": re.compile(r"/home/[a-z][a-z0-9_-]+/|/Users/[A-Za-z][A-Za-z0-9_-]+/"),
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".private"}
SKIP_FILES = {".privacy-denylist.local", "audit_privacy.py"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    root = Path(ap.parse_args().root)
    deny = []
    dl = root / ".privacy-denylist.local"
    if dl.exists():
        deny = [l.strip().lower() for l in dl.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
    else:
        print("note: no .privacy-denylist.local found; only generic patterns are checked")
    findings = 0
    for p in sorted(root.rglob("*")):
        if not p.is_file() or set(p.parts) & SKIP_DIRS or p.name in SKIP_FILES:
            continue
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov", ".woff", ".woff2", ".pdf"}:
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            if "privacy-ok" in line:
                continue
            low = line.lower()
            for kind, rx in PATTERNS.items():
                if rx.search(line):
                    print(f"{p.relative_to(root)}:{i}: [{kind}] {line.strip()[:120]}"); findings += 1
            for term in deny:
                if term in low:
                    print(f"{p.relative_to(root)}:{i}: [denylist:{term}] {line.strip()[:120]}"); findings += 1
    print(f"{findings} finding(s)")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
