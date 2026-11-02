"""A second listener for the takes that pass the checks: an audio language model hears teachers' reference
recordings, then two of our takes, and says which one it would rather a child hear. The top takes play every
other top take in both orders (so it cannot just favour whichever plays first) and are re-ranked by wins.
Verdicts are cached by everything that shapes them, so rerunning check is free."""
import hashlib
import json
from functools import cache
from itertools import permutations

from . import ROOT, api, audio, refs

MODEL = "gpt-audio-1.5"
TOP = 6
CACHE = ROOT / "build" / "judge"

SYSTEM = ("You are an expert early-literacy phonics teacher and audio engineer choosing pure-sound recordings for a "
          "children's reading app. You listen closely and reply only with JSON.")


def _ask_text(s):
    words = ", ".join(f"'{w}'" for w in s.keywords)
    return (f"Which candidate, A or B, should a child hear as the model of the {s.ipa} sound in {words}? In order of "
            f"importance: it is clearly {s.ipa} and nothing else (no 'uh' or other vowel added, not a different sound); "
            "it sounds natural and warm, like the teachers (their accents may differ, judge the sound); it is not "
            "harsh, spitty, clicky, hissy, distorted, or noisy; it is not breathy or whispered. "
            'Reply as {"better": "A" or "B", "why": "<one short sentence>"}.')


@cache
def _ref_wavs(letter):
    """Teachers' recordings (not the phonetician's, who says each sound several times) as wav for the model."""
    out = []
    for k, p in refs.paths(letter).items():
        if k.startswith("ftm"):
            dst = CACHE / "refs" / f"{letter}-{k}.wav"
            if not dst.exists():
                sr, x = audio.read(p)
                audio.write(dst, x, sr)
            out.append(dst)
    return tuple(out)


def _verdict(job):
    """'A' or 'B' for one ordered pair, from the cache when this exact question was asked before."""
    s, a, b = job
    clips = [*_ref_wavs(s.letter), a, b]
    key = hashlib.sha1(json.dumps([MODEL, SYSTEM, _ask_text(s)] + [hashlib.sha1(p.read_bytes()).hexdigest() for p in clips])
                       .encode()).hexdigest()[:16]
    hit = CACHE / f"{s.letter}-{key}.json"
    if not hit.exists():
        content = [{"type": "text", "text": "Teachers saying the target sound:"}, *map(api.audio_part, clips[:-2]),
                   {"type": "text", "text": "Candidate A:"}, api.audio_part(a),
                   {"type": "text", "text": "Candidate B:"}, api.audio_part(b),
                   {"type": "text", "text": _ask_text(s)}]
        msg = api.chat({"model": MODEL, "modalities": ["text"],
                        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]})
        text = msg["content"].strip().removeprefix("```json").strip("`\n ")
        verdict = json.loads(text)
        if verdict.get("better") not in ("A", "B"):
            raise ValueError(f"no verdict in {text!r}")
        hit.parent.mkdir(parents=True, exist_ok=True)
        hit.write_text(json.dumps(dict(a=str(a.relative_to(ROOT)), b=str(b.relative_to(ROOT)), **verdict)))
    return json.loads(hit.read_text())["better"]


def rank(s, rows):
    """Re-rank the top passing takes by how many head-to-heads they win; the rest keep their order after them."""
    top = [r for r in rows if not r["problems"]][:TOP]
    pairs = list(permutations(top, 2))
    verdicts = api.pmap(_verdict, [(s, ROOT / a["finished"], ROOT / b["finished"]) for a, b in pairs],
                        name=lambda j: f"{s.letter} judge {j[1].stem} vs {j[2].stem}")
    for r in top:
        r["judge"] = 0
    for (a, b), v in zip(pairs, verdicts):
        if v:
            (a if v == "A" else b)["judge"] += 1
    order = {id(r): i for i, r in enumerate(rows)}
    rows.sort(key=lambda r: (bool(r["problems"]), -r.get("judge", -1), order[id(r)]))
    return rows
