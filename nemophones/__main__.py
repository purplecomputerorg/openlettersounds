"""python -m nemophones {refs | prompts | generate | check | like | page | site | all} [letters] [--takes N] [--judge]"""
import argparse

import json

from . import check, generate, page, refs, site
from .sounds import BY_LETTER, SOUNDS


def main():
    ap = argparse.ArgumentParser(prog="nemophones")
    ap.add_argument("step", choices=("refs", "prompts", "generate", "check", "like", "page", "site", "all"))
    ap.add_argument("letters", nargs="?", default="", help="e.g. bdg; default all")
    ap.add_argument("take", nargs="?", type=int, help="like: the take number shown on the pages")
    ap.add_argument("--takes", type=int, default=10)
    ap.add_argument("--judge", action="store_true", help="check: re-rank the top passing takes with an audio model")
    a = ap.parse_args()
    sounds = [BY_LETTER[c] for c in a.letters] if a.letters else list(SOUNDS)
    if a.step in ("refs", "all"):
        refs.fetch()
    if a.step == "prompts":
        print(f"SYSTEM: {generate.SYSTEM}\n")
        for s in sounds:
            ex = generate.exemplar(s)
            print(f"{generate.prompt(s)} {generate.LIKE} [audio: {ex.relative_to(check.ROOT)}]" if ex else generate.prompt(s))
    if a.step in ("generate", "all"):
        generate.generate(sounds, a.takes)
    if a.step in ("check", "all"):
        check.run(sounds, a.judge)
    if a.step == "like":
        (s,) = sounds
        row = next(r for r in json.loads(check.REPORT.read_text())[s.letter] if int(r["take"]) + 1 == a.take)
        generate.like(s, check.ROOT / row["finished"])
        print(f"{s.letter}: take {a.take} is the exemplar; new takes go to {generate.take_dir(s).name}")
    if a.step in ("page", "all"):
        page.build()
    if a.step in ("site", "all"):
        site.build()


main()
