"""Public page for GitHub Pages, served from docs/: the library to play and download (one clip per letter sound,
plus alternates), and each letter's latest passing takes for visitors to suggest as alternates, or to download
with the library as their own alternates (the page zips that in the browser, from the files served here)."""
import json
import shutil
import zipfile

from . import ROOT
from .check import LIBRARY, META, REPORT
from .generate import take_dir
from .sounds import SOUNDS

OUT = ROOT / "docs"
AUDIO = OUT / "audio"  # candidate takes, as finished WAVs
CLIPS = OUT / "sounds"  # the library as shipped: WAVs, metadata, license
ZIP = f"openlettersounds-{LIBRARY.parent.name}-{LIBRARY.name}.zip"


def _sync(folder, wanted):
    """Remove files a previous build left that this one no longer serves."""
    for f in folder.glob("*.*"):
        if f.name not in wanted:
            f.unlink()


def _letter(s, rows, entry):
    clips = [entry, *entry.get("alts", [])] if entry else []
    library = [dict(label="main" if i == 0 else f"alt {i}", file=f"sounds/{c['file']}") for i, c in enumerate(clips)]
    candidates = []
    for r in rows:
        if not r["problems"] and not r.get("kept"):
            n = int(r["take"]) + 1
            shutil.copyfile(ROOT / r["finished"], AUDIO / f"{s.letter}-{n:02d}.wav")
            candidates.append(dict(n=n, file=f"audio/{s.letter}-{n:02d}.wav"))
    return dict(letter=s.letter, ipa=s.ipa, keywords=list(s.keywords), round=take_dir(s).name, library=library,
                candidates=candidates)


def _zip(files):
    """Every library clip with its metadata and license; fixed timestamps so an unchanged library zips identically."""
    with zipfile.ZipFile(OUT / ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.writestr(zipfile.ZipInfo(f"openlettersounds/{f.name}", (1980, 1, 1, 0, 0, 0)), f.read_bytes())


def build():
    report = json.loads(REPORT.read_text())
    library = {e["letter"]: e for e in json.loads(META.read_text())}
    AUDIO.mkdir(parents=True, exist_ok=True)
    CLIPS.mkdir(parents=True, exist_ok=True)
    letters = [_letter(s, report.get(s.letter, []), library.get(s.letter)) for s in SOUNDS]
    wavs = [LIBRARY / c["file"].split("/")[-1] for e in letters for c in e["library"]]
    files = [*wavs, META, LIBRARY.parent.parent / "LICENSE"]
    for f in files:
        shutil.copyfile(f, CLIPS / f.name)
    _sync(CLIPS, {f.name for f in files})
    _sync(AUDIO, {c["file"].split("/")[-1] for e in letters for c in e["candidates"]})
    _zip(files)
    (OUT / "takes.json").write_text(json.dumps(dict(zip=ZIP, extras=[f"sounds/{f.name}" for f in files[len(wavs):]],
                                                    letters=letters), ensure_ascii=False))
    shutil.copyfile(ROOT / "openlettersounds" / "site.html", OUT / "index.html")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(OUT, len(wavs), "library clips,", sum(len(e["candidates"]) for e in letters), "candidates,", size // 1024, "KB")
