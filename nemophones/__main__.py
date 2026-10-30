"""python -m nemophones {refs | generate | check | page | all} [letters] [--takes N]"""
import argparse

from . import check, generate, page, refs
from .sounds import BY_LETTER, SOUNDS


def main():
    ap = argparse.ArgumentParser(prog="nemophones")
    ap.add_argument("step", choices=("refs", "generate", "check", "page", "all"))
    ap.add_argument("letters", nargs="?", default="", help="e.g. bdg; default all")
    ap.add_argument("--takes", type=int, default=10)
    a = ap.parse_args()
    sounds = [BY_LETTER[c] for c in a.letters] if a.letters else list(SOUNDS)
    if a.step in ("refs", "all"):
        refs.fetch()
    if a.step in ("generate", "all"):
        generate.generate(sounds, a.takes)
    if a.step in ("check", "all"):
        check.run(sounds)
    if a.step in ("page", "all"):
        page.build()


main()
