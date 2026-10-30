"""Takes from OpenAI's audio model, prompted from the text spec only (no reference audio goes in)."""
import base64
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor

import httpx

from . import ROOT
from .sounds import VOWEL

MODEL, VOICE = "gpt-audio-1.5", "marin"
TAKES_DIR = ROOT / "takes"

SYSTEM = ("You are an expert early-literacy phonics teacher recording audio for a children's reading app. "
          "You model 'pure sounds' the way Jolly Phonics, UFLI and Letters and Sounds teach them: stop sounds are "
          "clipped with no added schwa, continuous sounds are held, vowels are short. When asked for a sound, your "
          "entire spoken reply is ONLY that one sound, said once, warm and clear, at normal speaking volume. "
          "Begin the sound instantly, with no breath, click or pause before it, and stop cleanly with no breath after. "
          "It must sound like a clean studio recording: no static, rumble, hiss or background noise. Never whisper "
          "and never sound breathy. Never say the letter name, the example word, or any other words.")


def prompt(s):
    words = ", ".join(f"'{w}'" for w in s.keywords)
    where = "at the end of" if s.letter == "x" else "at the start of"
    text = f"Letter {s.letter.upper()}: produce the {s.ipa} sound heard {where} {words}: {s.how}."
    if s.kind == VOWEL:
        text = f"Letter {s.letter.upper()}: produce the short {s.letter.upper()} vowel {s.ipa}, as in {words}: {s.how}."
    return text + (f" NOT {s.not_like}." if s.not_like else "")


def take_dir(s):
    """Takes are keyed by everything that shapes them, so editing a prompt starts a fresh set."""
    key = hashlib.sha1(json.dumps([MODEL, VOICE, SYSTEM, prompt(s)]).encode()).hexdigest()[:8]
    return TAKES_DIR / VOICE / f"{s.letter}-{key}"


def _one(job):
    s, n = job
    dst = take_dir(s) / f"{n:02d}.wav"
    if dst.exists():
        return
    body = {"model": MODEL, "modalities": ["text", "audio"], "audio": {"voice": VOICE, "format": "wav"},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt(s)}]}
    r = httpx.post("https://api.openai.com/v1/chat/completions", json=body, timeout=120,
                   headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
    r.raise_for_status()
    audio = r.json()["choices"][0]["message"]["audio"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(base64.b64decode(audio["data"]))
    dst.with_suffix(".txt").write_text(audio.get("transcript", ""))


def generate(sounds, takes):
    jobs = [(s, n) for s in sounds for n in range(takes)]
    with ThreadPoolExecutor(8) as ex:
        for err in ex.map(_safe, jobs):
            if err:
                print(err)
    (TAKES_DIR / VOICE).mkdir(parents=True, exist_ok=True)
    (TAKES_DIR / VOICE / "prompts.json").write_text(json.dumps(
        {s.letter: {"dir": take_dir(s).name, "system": SYSTEM, "prompt": prompt(s)} for s in sounds}, indent=1, ensure_ascii=False))


def _safe(job):
    try:
        _one(job)
    except httpx.HTTPError as e:
        return f"{job[0].letter} take {job[1]}: {e}"
