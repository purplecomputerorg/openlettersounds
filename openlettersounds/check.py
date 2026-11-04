"""Gate every take on what a listener would object to, rank survivors by closeness to the references,
and write the best one per sound into the library."""
import json
from functools import cache

from . import ROOT, audio, judge, recognize, refs
from .generate import MODEL, SYSTEM, VOICE, prompt, take_dir
from .sounds import HOLD, SOUNDS, STOP, VOWEL

LIBRARY = ROOT / "sounds" / "en-us" / VOICE
FINISHED = ROOT / "build" / "finished"
VOWEL_TOKENS = set("aeiouæɑɛɪʌəɔʊøɜɐ")
HEARD_AS = {"/k/": {"k", "kh"}, "/p/": {"p", "ph"}, "/t/": {"t", "th"}, "/h/": {"h", "ħ"}, "/ɡ/": {"ɡ", "g"},
            "/dʒ/": {"dʒ"}, "/b/": {"b"}, "/d/": {"d"}, "/w/": {"w"}, "/j/": {"j"}, "/kw/": {"k", "kh"},
            "/ks/": {"k", "kh", "s"}}
MAX_MS = {"f": 550, "s": 550}
RUMBLE_FREE = set("fs")


def _max_ms(s):
    return MAX_MS.get(s.letter, 700) if s.kind == HOLD else 500 if s.kind == VOWEL else None


@cache
def _ref_posts(letter):
    return {k: recognize.posteriors(audio.read(p, recognize.RATE)[1]) for k, p in refs.paths(letter).items()}


def _to_refs(post, letter, skip=None):
    """Median distance from a clip to a letter's references (lower is closer)."""
    d = sorted(recognize.distance(post, p) for k, p in _ref_posts(letter).items() if k != skip)
    return d[len(d) // 2]


@cache
def _separable(x, y):
    """Most of x's own references sit closer to x than to y, so comparing a take against y can be trusted."""
    own = _ref_posts(x)
    return sum(_to_refs(p, x, skip=k) < _to_refs(p, y) for k, p in own.items()) > len(own) / 2


def _rivals(sound):
    """Only held sounds: the recognizer hears clipped stops as near-silence and most vowels as 'a', and a
    voicing partner (S/Z, F/V) is already caught by the voicing check."""
    if sound.kind != HOLD:
        return []
    return [s.letter for s in SOUNDS if s.kind == HOLD and s.voiced == sound.voiced and s.ipa != sound.ipa
            and _separable(sound.letter, s.letter)]


def _clean(s, heard):
    """The recognizer heard the sound itself and no vowel (or, for a vowel, a vowel)."""
    has_vowel = any(set(h) & VOWEL_TOKENS for h in heard)
    if s.kind == VOWEL:
        return has_vowel
    return not has_vowel and (s.ipa not in HEARD_AS or (bool(heard) and heard[0] in HEARD_AS[s.ipa]))


def problems(s, m, heard):
    """Why a listener would reject this take; empty means it passes."""
    out = []
    if m["preroll_ms"] > (150 if s.kind == HOLD else 80):
        out.append("breath or pause before the sound")
    has_vowel = any(set(h) & VOWEL_TOKENS for h in heard)
    if s.kind == STOP:
        if m["loud_ms"] > 300:
            out.append("noise, not a crisp release")
        if m["sound_ms"] > 400:
            out.append("trailing sound after the release")
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
        if s.letter in RUMBLE_FREE and (m["low"] > 0.2 or (s.letter == "s" and m["high"] < 0.6)):
            out.append("rumble or static, not a clean hiss")
    elif s.kind == VOWEL:
        if not 150 <= m["loud_ms"] <= 700:
            out.append(f"length {m['loud_ms']} ms")
        if m["voiced_ms"] < 0.6 * m["loud_ms"]:
            out.append("breathy or static, not a voiced vowel")
    else:
        if m["loud_ms"] > 600 or m["sound_ms"] > 700:
            out.append("noise or too long")
        if s.voiced and m["voiced_ms"] < 100:
            out.append("whispered, not voiced")
        if s.voiced and m["voiced_ms"] > 320:
            out.append("vowel after the glide")
    return out


def check(sound):
    rows, rivals = [], _rivals(sound)
    for path in sorted(take_dir(sound).glob("*.wav")):
        sr, x = audio.read(path)
        post = recognize.posteriors(audio.read(path, recognize.RATE)[1])
        heard = recognize.heard(post)
        m = audio.measure(x, sr)
        own = _to_refs(post, sound.letter)
        closer = [r.upper() for r in rivals if _to_refs(post, r) < own]
        row = dict(take=path.stem, heard=" ".join(heard), **m, similarity=round(own, 3),
                   problems=problems(sound, m, heard) + ([f"sounds closer to {', '.join(closer)}"] if closer else []))
        if not row["problems"]:
            fin = FINISHED / path.parent.name / f"{path.stem}.wav"
            audio.write(fin, audio.finish(x, sr, _max_ms(sound)), sr)
            row["finished"] = str(fin.relative_to(ROOT))
        rows.append(row)
    # a clip the recognizer hears nothing in sits close to everything, so it ranks after ones it can hear
    rows.sort(key=lambda r: (bool(r["problems"]), not r["heard"], not _clean(sound, r["heard"].split()), r["similarity"]))
    return rows


def _clip(sound, row, name):
    """Copy a take's finished clip into the library as name; return its provenance."""
    dst = LIBRARY / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes((ROOT / row["finished"]).read_bytes())
    return dict(file=name, generator=dict(model=MODEL, voice=VOICE, system=SYSTEM, prompt=prompt(sound),
                                          take=f"{take_dir(sound).name}/{row['take']}"),
                judge=dict(model=judge.MODEL, wins=row["judge"]) if "judge" in row else None)


def publish(sound, row, entry=None, reviewed=False):
    """Make row the library clip, keeping any alternates already picked."""
    return dict(letter=sound.letter, ipa=sound.ipa, kind=sound.kind, keywords=list(sound.keywords), reviewed=reviewed,
                **_clip(sound, row, f"{sound.letter}.wav"), alts=(entry or {}).get("alts", []))


REPORT = ROOT / "build" / "report.json"
META = LIBRARY / "sounds.json"


def _load(path):
    return json.loads(path.read_text()) if path.exists() else None


def _save_library(library):
    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(sorted(library.values(), key=lambda e: e["letter"]), indent=1, ensure_ascii=False))


def run(sounds, use_judge=False):
    """Check every take; a sound nobody has picked yet gets the best passing take as its library clip."""
    library = {e["letter"]: e for e in _load(META) or []}
    report = _load(REPORT) or {}
    if use_judge:
        print(f"judge: {judge.MODEL}" + ("" if judge.MODEL.startswith("gemini") else " (set GEMINI_API_KEY in .env to use Gemini)"))
    for s in sounds:
        rows = check(s)
        for r in rows:
            r["kept"] = f"{take_dir(s).name}/{r['take']}" in kept_takes(library.get(s.letter, {}))
        rows = report[s.letter] = judge.rank(s, rows) if use_judge else rows
        best = next((r for r in rows if not r["problems"]), None)
        kept = library.get(s.letter, {}).get("reviewed")
        print(f"{s.letter}: {sum(not r['problems'] for r in rows)}/{len(rows)} pass"
              + ("  (keeps your pick)" if kept else "" if best else "  NO PICK"))
        if best and not kept:
            library[s.letter] = publish(s, best, library.get(s.letter))
    _save_library(library)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    return report


def kept_clips(entry):
    """The library clip and alternates a person picked, newest last."""
    return [entry, *entry.get("alts", [])] if entry.get("reviewed") else []


def kept_takes(entry):
    return {c["generator"]["take"] for c in kept_clips(entry)}


def pick(picks):
    """Keep a person's picks, [(letter, take number as shown on the pages)]. A letter's first pick becomes its
    library clip, never replaced by later runs, and the exemplar new takes are generated to sound like; every later
    pick is kept as one more alternate beside it."""
    from .generate import like
    from .sounds import BY_LETTER
    library = {e["letter"]: e for e in _load(META) or []}
    report = _load(REPORT)
    for letter, n in picks:
        s, entry = BY_LETTER[letter], library.get(letter, {})
        row = next(r for r in report[letter] if int(r["take"]) + 1 == n and not r["problems"])
        take = f"{take_dir(s).name}/{row['take']}"
        if take in kept_takes(entry):
            continue
        if entry.get("reviewed"):
            entry["alts"].append(_clip(s, row, f"{letter}-alt{len(entry['alts']) + 1}.wav"))
            print(f"{letter}: kept take {n} as alternate {len(entry['alts'])}")
        else:
            library[letter] = publish(s, row, entry, reviewed=True)
            like(s, ROOT / row["finished"])
            print(f"{letter}: kept take {n} as the library clip")
    _save_library(library)
