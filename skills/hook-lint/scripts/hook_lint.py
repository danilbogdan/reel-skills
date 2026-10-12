#!/usr/bin/env python3
"""Lint a reel hook: the on-screen caption and, optionally, the first spoken sentence.

Usage:
  hook_lint.py "ON-SCREEN CAPTION" [--spoken "First spoken sentence"]
               [--max-caption-words 8] [--max-spoken-words 16]

Checks are simple and language-neutral on purpose (English and Russian word lists). They catch the common
misses (too long, greeting opener, nothing concrete) and cannot judge whether the hook is good.
Exit 1 if a FAIL line is printed.
"""
import argparse
import re
import sys

FILLER_OPENERS = ("hi", "hello", "hey", "welcome", "today", "in this video", "so ", "привет", "всем привет",
                  "здравствуйте", "сегодня", "в этом видео", "итак")
ADDRESS = {"i", "my", "me", "we", "you", "your", "you're", "я", "мой", "моя", "мне", "меня", "мы", "ты", "тебе",
           "тебя", "твой", "вы", "вам", "ваш"}
TENSION = {"how", "why", "without", "instead", "stop", "never", "only", "easier", "faster", "minutes", "hour",
           "hours", "secret", "mistake", "wrong", "как", "почему", "без", "вместо",
           "перестань", "никогда", "только", "проще", "быстрее", "минут", "час", "часов", "секрет", "ошибка"}


NUMBER_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "один", "два",
                "три", "четыре", "пять", "шесть", "семь", "восемь", "девять", "десять"}


def words(text):
    return re.findall(r"[\w'’-]+", text, flags=re.UNICODE)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("caption", help="the on-screen hook text")
    ap.add_argument("--spoken", help="the first spoken sentence")
    ap.add_argument("--max-caption-words", type=int, default=8)
    ap.add_argument("--max-spoken-words", type=int, default=16)
    args = ap.parse_args()

    fails = warns = 0

    def line(level, msg):
        nonlocal fails, warns
        fails += level == "FAIL"
        warns += level == "WARN"
        print(f"{level:<5} {msg}")

    cap = args.caption.strip()
    w = [x.lower() for x in words(cap)]
    n = len(w)
    print(f"Caption: {cap}")
    if n > args.max_caption_words:
        line("FAIL", f"{n} words; a caption is read in about 2 seconds, keep it to {args.max_caption_words}")
    else:
        line("PASS", f"{n} words")
    low = cap.lower()
    if any(low.startswith(f) for f in FILLER_OPENERS):
        line("FAIL", "opens with a greeting or filler; start with the claim or the problem")
    else:
        line("PASS", "no greeting opener")
    if any(c.isdigit() for c in cap) or NUMBER_WORDS & set(w):
        line("PASS", "contains a number")
    else:
        line("WARN", "no number; a number makes a promise concrete (hours, steps, count)")
    if ADDRESS & set(w):
        line("PASS", "speaks to the viewer or states a personal stake")
    else:
        line("WARN", "no 'I' or 'you'; a personal stake or a direct address holds attention")
    if TENSION & set(w) or "?" in cap:
        line("PASS", "carries a question, a result or a tension word")
    else:
        line("WARN", "no question or result word; what changes for the viewer?")

    if args.spoken:
        sw = words(args.spoken)
        print(f"\nSpoken: {args.spoken.strip()}")
        if len(sw) > args.max_spoken_words:
            line("FAIL", f"{len(sw)} words; the first sentence should fit in about 4 seconds "
                         f"(max {args.max_spoken_words})")
        else:
            line("PASS", f"{len(sw)} words")
        if any(args.spoken.lower().startswith(f) for f in FILLER_OPENERS):
            line("FAIL", "spoken opener is a greeting or filler")
        if args.spoken.strip().lower() == cap.lower():
            line("WARN", "spoken line repeats the caption word for word; let one of them add something")

    print(f"\n{fails} fail(s), {warns} warning(s). The hook is a promise: the video must pay it off.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
