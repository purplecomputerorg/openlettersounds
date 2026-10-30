"""Public picking page for GitHub Pages: every passing take per letter, served from docs/."""
import json
import shutil

from . import ROOT
from .check import LIBRARY, REPORT
from .page import ogg
from .sounds import SOUNDS

OUT = ROOT / "docs"
AUDIO = OUT / "audio"


def _letter(s, rows, pick):
    takes = []
    for r in (r for r in rows if not r["problems"]):
        n = int(r["take"]) + 1
        name = f"{s.letter}-{n:02d}.ogg"
        shutil.copyfile(ogg(ROOT / r["finished"]), AUDIO / name)
        takes.append(dict(n=n, file=f"audio/{name}", pick=r["take"] == pick))
    return dict(letter=s.letter, ipa=s.ipa, keywords=list(s.keywords), takes=takes)


def build():
    report = json.loads(REPORT.read_text())
    picks = {e["letter"]: e["generator"]["take"].split("/")[-1] for e in json.loads((LIBRARY / "sounds.json").read_text())}
    AUDIO.mkdir(parents=True, exist_ok=True)
    letters = [_letter(s, report[s.letter], picks.get(s.letter)) for s in SOUNDS if s.letter in report]
    keep = {t["file"].split("/")[-1] for e in letters for t in e["takes"]}
    for f in AUDIO.glob("*.ogg"):
        if f.name not in keep:
            f.unlink()
    (OUT / "takes.json").write_text(json.dumps(letters, ensure_ascii=False))
    shutil.copyfile(ROOT / "nemophones" / "site.html", OUT / "index.html")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(OUT, len(keep), "clips", size // 1024, "KB")
