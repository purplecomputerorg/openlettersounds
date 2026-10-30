"""Single-file review page: references, then passing takes ranked, then rejected takes with the reason."""
import base64
import html
import json
import subprocess

from . import ROOT, refs
from .check import LIBRARY, REPORT
from .generate import take_dir
from .sounds import SOUNDS

OUT = ROOT / "build" / "review.html"
OGG = ROOT / "build" / "ogg"
REF_LABEL = {"ftm-us": "US", "ftm-au": "Australian", "ftm-za": "S. African", "wiki": "Phonetician"}


def ogg(path):
    """Small Vorbis copy of a clip, so hundreds of them fit in a page."""
    dst = OGG / path.relative_to(ROOT).with_suffix(".ogg")
    if not dst.exists() or dst.stat().st_mtime < path.stat().st_mtime:
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ac", "1", "-c:a", "libvorbis", "-q:a", "4", str(dst)],
                       check=True)
    return dst


def _uri(path):
    return "data:audio/ogg;base64," + base64.b64encode(ogg(path).read_bytes()).decode()


def _btn(label, path, note, cls=""):
    return (f'<button class="clip {cls}" data-src="{_uri(path)}">{html.escape(label)}'
            f'<small>{html.escape(note)}</small></button>')


def _row(s, rows):
    ref_btns = "".join(_btn(REF_LABEL[k], p, "reference") for k, p in refs.paths(s.letter).items())
    passing = [r for r in rows if not r["problems"]]
    picks = "".join(_btn(f"take {int(r['take']) + 1}", ROOT / r["finished"], f"sim {r['similarity']}", "pick" if i == 0 else "")
                    for i, r in enumerate(passing))
    rejected = "".join(_btn(f"take {int(r['take']) + 1}", take_dir(s) / f"{r['take']}.wav", "; ".join(r["problems"]), "rej")
                       for r in rows if r["problems"])
    return (f'<tr><th><span class="L">{s.letter.upper()}</span><span class="ipa">{s.ipa}</span>'
            f'<span class="ex">{", ".join(s.keywords)}</span></th><td class="alts">{ref_btns}</td>'
            f'<td class="alts">{picks or "<em>none passed</em>"}</td><td class="alts">{rejected}</td></tr>')


def build():
    report = json.loads(REPORT.read_text())
    body = "\n".join(_row(s, report[s.letter]) for s in SOUNDS if s.letter in report)
    final = "".join(_btn(e["letter"].upper(), LIBRARY / e["file"], e["ipa"])
                    for e in json.loads((LIBRARY / "sounds.json").read_text()))
    OUT.write_text((ROOT / "nemophones" / "page.html").read_text().replace("{{ROWS}}", body).replace("{{FINAL}}", final))
    print(OUT, OUT.stat().st_size // 1024, "KB")
