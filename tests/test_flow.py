#!/usr/bin/env python3
"""Unit tests for the pure planning and caption logic (no media needed).

Usage: python3 -m unittest discover -s tests   (or: python3 tests/test_flow.py)
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(rel):
    path = ROOT / rel
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pc = load("skills/pause-cut/scripts/pause_cut.py")
cap = load("skills/reel-render/scripts/captions.py")


def plan(pauses, duration, min_piece=3.0, keep=0.3, head=0.1, tail=0.4, drops=()):
    cands = pc.build_candidates(pauses, keep, 0.4, list(drops))
    cuts = pc.select_cuts(cands, head, duration - tail, min_piece)
    return cuts, pc.pieces_from(cuts, head, duration - tail)


class RhythmRule(unittest.TestCase):
    def test_no_piece_shorter_than_min_piece(self):
        pauses = [(2.0, 2.7), (3.0, 3.8), (8.0, 9.2), (14.0, 14.9)]
        _, pieces = plan(pauses, 20.0)
        self.assertTrue(all(e - s >= 3.0 for s, e in pieces), pieces)

    def test_one_word_between_pauses_is_not_cut_twice(self):
        # a word at 2.7-3.0 between two pauses: only the longer pause may be cut
        cuts, _ = plan([(2.0, 2.7), (3.0, 3.9)], 12.0)
        self.assertEqual(len(cuts), 1)
        self.assertAlmostEqual(cuts[0]["end"] - cuts[0]["start"], 0.9 - 0.3, places=3)

    def test_longest_pauses_win_the_conflict(self):
        cuts, _ = plan([(3.1, 3.7), (4.0, 6.0), (9.0, 9.5)], 14.0)
        starts = [round(c["start"], 2) for c in cuts]
        self.assertIn(4.15, starts)
        self.assertNotIn(3.25, starts)

    def test_widely_spaced_pauses_are_all_cut(self):
        cuts, pieces = plan([(5.0, 5.8), (11.0, 12.0), (18.0, 18.6)], 25.0)
        self.assertEqual(len(cuts), 3)
        self.assertEqual(len(pieces), 4)

    def test_tiny_pauses_are_left_alone(self):
        cuts, _ = plan([(5.0, 5.45)], 12.0)
        self.assertEqual(cuts, [])


class ForcedDrop(unittest.TestCase):
    def test_drop_is_widened_to_one_cut(self):
        # dropping a word at 6.0-6.3 that sits between two pauses costs one cut, not three
        cuts, pieces = plan([(5.5, 6.0), (6.3, 6.8)], 15.0, drops=[(6.0, 6.3)])
        self.assertEqual(len(cuts), 1)
        self.assertLessEqual(cuts[0]["start"], 5.5 + 0.15 + 1e-6)
        self.assertGreaterEqual(cuts[0]["end"], 6.8 - 0.15 - 1e-6)

    def test_drop_beats_a_conflicting_automatic_cut(self):
        cuts, _ = plan([(2.0, 3.0), (7.0, 7.5)], 20.0, drops=[(6.5, 6.9)])
        self.assertTrue(any(c["forced"] for c in cuts))


    def test_drop_near_the_start_keeps_other_cuts_that_fit(self):
        # the dropped word makes the first piece short (the human asked for it); a later, well-spaced pause is still cut
        cuts, _ = plan([(2.0, 2.7), (3.0, 3.8), (8.0, 9.2)], 20.0, drops=[(2.7, 3.0)])
        self.assertEqual(len(cuts), 2)


class Captions(unittest.TestCase):
    def words(self, text, step=0.4):
        return [{"text": t, "start": i * step, "end": i * step + 0.3} for i, t in enumerate(text.split())]

    def test_pages_have_two_lines_at_most(self):
        pages = cap.paginate(self.words("one two three four five six seven eight nine ten eleven twelve thirteen"))
        for p in pages:
            self.assertLessEqual(len(p["text"].split("\\N")), 2)
            for line in p["text"].split("\\N"):
                self.assertLessEqual(len(line), 30)

    def test_sentence_end_breaks_a_page(self):
        pages = cap.paginate(self.words("Hello there. Second sentence here"))
        self.assertEqual(len(pages), 2)

    def test_pages_never_overlap(self):
        pages = cap.paginate(self.words("a b c d e f g h i j k l m n o p q r s t u v w x y z " * 3))
        for a, b in zip(pages, pages[1:]):
            self.assertLessEqual(a["end"], b["start"] + 1e-9)

    def test_srt_round_trip(self):
        srt = "1\n00:00:01,000 --> 00:00:03,000\nПривет, мир\n"
        self.assertEqual(cap.parse_srt(srt), [(1.0, 3.0, "Привет, мир")])

    def test_clean_style_has_no_hard_outline_and_no_animation_tags(self):
        ass = cap.build_ass([{"start": 0, "end": 1, "text": "x"}], "Inter Light", 52, 420, "clean")
        self.assertNotIn("\\fad", ass)
        self.assertNotIn("\\t(", ass)
        self.assertIn("Inter Light", ass)


if __name__ == "__main__":
    unittest.main()
