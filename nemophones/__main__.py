"""python -m nemophones {refs | prompts | generate | check | page | site | all} [letters] [--takes N]"""
import argparse

from . import check, generate, page, refs, site
from .sounds import BY_LETTER, SOUNDS


def main():
    ap = argparse.ArgumentParser(prog="nemophones")
    ap.add_argument("step", choices=("refs", "prompts", "generate", "check", "page", "site", "all"))
    ap.add_argument("letters", nargs="?", default="", help="e.g. bdg; default all")
    ap.add_argument("--takes", type=int, default=10)
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
        check.run(sounds)
    if a.step in ("page", "all"):
        page.build()
    if a.step in ("site", "all"):
        site.build()


main()
