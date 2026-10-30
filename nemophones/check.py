"""Gate every take on what a listener would object to, rank survivors by closeness to the references,
and write the best one per sound into the library."""
import json
from functools import cache

from . import ROOT, audio, recognize, refs
from .generate import MODEL, SYSTEM, VOICE, prompt, take_dir
from .sounds import HOLD, STOP, VOWEL

LIBRARY = ROOT / "sounds" / "en-us" / VOICE
FINISHED = ROOT / "build" / "finished"
VOWEL_TOKENS = set("aeiouæɑɛɪʌəɔʊøɜɐ")
HEARD_AS = {"/k/": {"k", "kh"}, "/p/": {"p", "ph"}, "/t/": {"t", "th"}, "/h/": {"h", "ħ"}, "/ɡ/": {"ɡ", "g"},
            "/dʒ/": {"dʒ"}, "/b/": {"b"}, "/d/": {"d"}}
MAX_MS = {"f": 550, "s": 550}


def _max_ms(s):
    return MAX_MS.get(s.letter, 700) if s.kind == HOLD else 500 if s.kind == VOWEL else None


@cache
def _ref_posts(letter):
    return {k: recognize.posteriors(audio.read(p, recognize.RATE)[1]) for k, p in refs.paths(letter).items()}


def problems(s, m, heard):
    """Why a listener would reject this take; empty means it passes."""
    out = []
    if m["preroll_ms"] > (150 if s.kind == HOLD else 80):
        out.append("breath or pause before the sound")
    has_vowel = any(set(h) & VOWEL_TOKENS for h in heard)
    if s.kind == STOP:
        if m["loud_ms"] > 300:
            out.append("noise, not a crisp release")
        if s.voiced and m["voiced_ms"] < 30:
            out.append("unvoiced, sounds like its partner")
        if (heard or s.letter != "h") and (not heard or heard[0] not in HEARD_AS[s.ipa]):
            out.append(f"heard as '{' '.join(heard) or 'nothing'}'")
        if has_vowel and m["voiced_ms"] > 100:
            out.append("added 'uh'")
    elif s.kind == HOLD:
        if m["sound_ms"] < 450:
            out.append("too short to hold")
        if s.voiced and m["voiced_ms"] < 0.6 * m["loud_ms"]:
            out.append("buzz not steady")
        if not s.voiced and m["voiced_ms"] > 40:
            out.append("voiced, should be breath only")
        if len(heard) > 2:
            out.append("wobbles")
    elif s.kind == VOWEL:
        if not 150 <= m["loud_ms"] <= 700:
            out.append(f"length {m['loud_ms']} ms")
    elif m["loud_ms"] > 600:
        out.append("noise or too long")
    return out


def check(sound):
    rows = []
    for path in sorted(take_dir(sound).glob("*.wav")):
        sr, x = audio.read(path)
        post = recognize.posteriors(audio.read(path, recognize.RATE)[1])
        heard = recognize.heard(post)
        m = audio.measure(x, sr)
        dist = {k: round(recognize.distance(post, rp), 3) for k, rp in _ref_posts(sound.letter).items()}
        row = dict(take=path.stem, heard=" ".join(heard), **m, ref_distance=dist,
                   similarity=round(sorted(dist.values())[len(dist) // 2], 3) if dist else None,
                   problems=problems(sound, m, heard))
        if not row["problems"]:
            fin = FINISHED / sound.letter / f"{path.stem}.wav"
            audio.write(fin, audio.finish(x, sr, _max_ms(sound)), sr)
            row["finished"] = str(fin.relative_to(ROOT))
        rows.append(row)
    rows.sort(key=lambda r: (bool(r["problems"]), r["similarity"] if r["similarity"] is not None else 9))
    return rows


def publish(sound, rows):
    """Best passing take becomes the library clip, with everything needed to reproduce it."""
    best = next((r for r in rows if not r["problems"]), None)
    if best is None:
        return None
    dst = LIBRARY / f"{sound.letter}.wav"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes((ROOT / best["finished"]).read_bytes())
    return dict(letter=sound.letter, ipa=sound.ipa, kind=sound.kind, keywords=list(sound.keywords), file=dst.name,
                reviewed=False, generator=dict(model=MODEL, voice=VOICE, system=SYSTEM, prompt=prompt(sound),
                                               take=f"{take_dir(sound).name}/{best['take']}"))


REPORT = ROOT / "build" / "report.json"


def run(sounds):
    meta_path = LIBRARY / "sounds.json"
    library = {e["letter"]: e for e in json.loads(meta_path.read_text())} if meta_path.exists() else {}
    report = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    for s in sounds:
        report[s.letter] = check(s)
        entry = publish(s, report[s.letter])
        passed = sum(not r["problems"] for r in report[s.letter])
        print(f"{s.letter}: {passed}/{len(report[s.letter])} pass" + ("" if entry else "  NO PICK"))
        if entry:
            library[s.letter] = entry
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(sorted(library.values(), key=lambda e: e["letter"]), indent=1, ensure_ascii=False))
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    return report
