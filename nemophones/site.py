"""Public picking page for GitHub Pages: each letter's kept clips, then every passing take of its latest round,
served from docs/."""
import json
import shutil

from . import ROOT
from .check import LIBRARY, META, REPORT, kept_clips
from .generate import take_dir
from .page import ogg
from .sounds import SOUNDS

OUT = ROOT / "docs"
AUDIO = OUT / "audio"


def _copy(src, name):
    shutil.copyfile(ogg(src), AUDIO / name)
    return f"audio/{name}"


def _letter(s, rows, entry):
    """kept: the library clip and alternates a person picked; takes: this round's candidates to pick from."""
    kept = [dict(label="pick" if i == 0 else f"alt {i}", file=_copy(LIBRARY / c["file"], f"{s.letter}-kept{i}.ogg"))
            for i, c in enumerate(kept_clips(entry))]
    takes = [dict(n=int(r["take"]) + 1, file=_copy(ROOT / r["finished"], f"{s.letter}-{int(r['take']) + 1:02d}.ogg"))
             for r in rows if not r["problems"] and not r.get("kept")]
    return dict(letter=s.letter, ipa=s.ipa, keywords=list(s.keywords), round=take_dir(s).name, kept=kept, takes=takes)


def build():
    report = json.loads(REPORT.read_text())
    library = {e["letter"]: e for e in json.loads(META.read_text())}
    AUDIO.mkdir(parents=True, exist_ok=True)
    letters = [_letter(s, report[s.letter], library.get(s.letter, {})) for s in SOUNDS if s.letter in report]
    keep = {c["file"].split("/")[-1] for e in letters for c in e["kept"] + e["takes"]}
    for f in AUDIO.glob("*.ogg"):
        if f.name not in keep:
            f.unlink()
    (OUT / "takes.json").write_text(json.dumps(letters, ensure_ascii=False))
    shutil.copyfile(ROOT / "nemophones" / "site.html", OUT / "index.html")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(OUT, len(keep), "clips", size // 1024, "KB")
