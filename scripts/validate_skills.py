#!/usr/bin/env python3
"""Validate the skills under skills/: frontmatter, naming, required sections, links, script hygiene.

Usage: validate_skills.py [skill ...]     (default: every folder in skills/ whose name does not start with "_")
Exit 1 if any error is found.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
CATEGORIES = {"reflection", "content-research", "content-production", "writing"}
STATUSES = {"draft", "stable", "experimental"}
REQUIRED_SECTIONS = ["## Verify", "## Will not do"]
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def parse_frontmatter(text):
    """Small parser for the subset used here: scalar keys, folded description, one-level metadata map."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    data, section = {}, None
    for line in m.group(1).split("\n"):
        if not line.strip():
            continue
        if not line.startswith(" "):
            key, _, val = line.partition(":")
            section = key.strip()
            if section == "metadata":
                data["metadata"] = {}
            else:
                data[section] = val.strip().lstrip(">-|").strip()
            continue
        if section == "metadata":
            k, _, v = line.strip().partition(":")
            data["metadata"][k.strip()] = v.split("#")[0].strip()
        elif section:
            data[section] = (data[section] + " " + line.strip()).strip()
    return data


def check_skill(folder: Path) -> list[str]:
    errors = []
    skill_md = folder / "SKILL.md"
    if not skill_md.exists():
        return [f"{folder.name}: SKILL.md is missing"]
    text = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        return [f"{folder.name}: SKILL.md has no frontmatter block"]

    name = fm.get("name", "")
    if name != folder.name:
        errors.append(f"{folder.name}: name '{name}' must equal the folder name")
    if not KEBAB.match(folder.name):
        errors.append(f"{folder.name}: folder name must be lowercase kebab-case")

    desc = fm.get("description", "")
    if not 40 <= len(desc) <= 1024:
        errors.append(f"{folder.name}: description must be 40 to 1024 characters (is {len(desc)})")

    meta = fm.get("metadata", {})
    if meta.get("category") not in CATEGORIES:
        errors.append(f"{folder.name}: metadata.category must be one of {sorted(CATEGORIES)}")
    if meta.get("status") not in STATUSES:
        errors.append(f"{folder.name}: metadata.status must be one of {sorted(STATUSES)}")
    if not SEMVER.match(meta.get("version", "")):
        errors.append(f"{folder.name}: metadata.version must be semver, e.g. 0.1.0")
    if "requires" not in meta:
        errors.append(f"{folder.name}: metadata.requires is missing (use [] if none)")

    body = text.split("---\n", 2)[-1]
    for section in REQUIRED_SECTIONS:
        if section not in body:
            errors.append(f"{folder.name}: missing section '{section}'")
    if len(text.splitlines()) > 500:
        errors.append(f"{folder.name}: SKILL.md is longer than 500 lines; move detail to references/")

    for target in re.findall(r"\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        path = target.split("#")[0]
        if path and not (folder / path).exists():
            errors.append(f"{folder.name}: link to missing file '{path}'")

    scripts = folder / "scripts"
    if scripts.is_dir():
        for s in sorted(scripts.iterdir()):
            if s.suffix not in {".py", ".sh"}:
                continue
            first = s.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
            if not first.startswith("#!"):
                errors.append(f"{folder.name}: scripts/{s.name} has no shebang line")
            body_text = s.read_text(encoding="utf-8", errors="replace")
            if "--help" not in body_text and "argparse" not in body_text:
                errors.append(f"{folder.name}: scripts/{s.name} does not handle --help")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skills", nargs="*")
    args = ap.parse_args()
    if args.skills:
        folders = [SKILLS / s for s in args.skills]
    else:
        folders = [p for p in sorted(SKILLS.iterdir()) if p.is_dir() and not p.name.startswith("_")]
    errors = []
    for folder in folders:
        found = check_skill(folder)
        errors += found
        print(f"{'FAIL' if found else 'OK  '} {folder.name}")
    for e in errors:
        print(f"  - {e}")
    print(f"{len(folders)} skill(s) checked, {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
