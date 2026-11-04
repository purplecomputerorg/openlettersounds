"""python -m openlettersounds {refs | prompts | generate | check | pick | page | site | all} [letters] [--takes N] [--judge]"""
import argparse
import re
import sys

from . import check, generate, page, refs, site
from .sounds import BY_LETTER, SOUNDS


def main():
    ap = argparse.ArgumentParser(prog="openlettersounds")
    ap.add_argument("step", choices=("refs", "prompts", "generate", "check", "pick", "page", "site", "all"))
    ap.add_argument("letters", nargs="?", default="", help="e.g. bdg; default all")
    ap.add_argument("--takes", type=int, default=10)
    ap.add_argument("--judge", action="store_true", help="check: re-rank the top passing takes with an audio model")
    a = ap.parse_args()
    sounds = [BY_LETTER[c] for c in a.letters] if a.letters else list(SOUNDS)
    if a.step in ("refs", "all"):
        refs.fetch()
    if a.step == "prompts":
        print(f"SYSTEM: {generate.SYSTEM}\n")
        for s in sounds:
            print(generate.prompt(s))
    if a.step in ("generate", "all"):
        generate.generate(sounds, a.takes)
    if a.step in ("check", "all"):
        check.run(sounds, a.judge)
    if a.step == "pick":
        # picks as the listening page sends them, e.g. "b: take 37", one per line, on stdin
        found = re.findall(r"\b([a-z]): take (\d+)", sys.stdin.read().lower())
        check.pick([(l, int(n)) for l, n in found if l in {s.letter for s in sounds}])
    if a.step in ("page", "all"):
        page.build()
    if a.step in ("site", "all"):
        site.build()


main()
