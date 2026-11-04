"""Takes from OpenAI's audio model, prompted from the text spec only. Audio never goes in: attaching a take a person
liked made later takes shorter, noisier and buzzier for almost every sound, so picked takes (exemplars/) guide
only the judge."""
import base64
import hashlib
import json
import shutil

from . import ROOT, api
from .sounds import VOWEL

MODEL, VOICE = "gpt-audio-1.5", "marin"
TAKES_DIR = ROOT / "takes"
EXEMPLARS = ROOT / "exemplars" / VOICE

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


def exemplar(s):
    p = EXEMPLARS / f"{s.letter}.wav"
    return p if p.exists() else None


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
    audio = api.chat(body)["audio"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(base64.b64decode(audio["data"]))
    dst.with_suffix(".txt").write_text(audio.get("transcript", ""))


def generate(sounds, takes):
    api.pmap(_one, [(s, n) for s in sounds for n in range(takes)], name=lambda j: f"{j[0].letter} take {j[1]}")
    index = TAKES_DIR / VOICE / "prompts.json"
    prompts = json.loads(index.read_text()) if index.exists() else {}
    prompts.update({s.letter: {"dir": take_dir(s).name, "system": SYSTEM, "prompt": prompt(s)} for s in sounds})
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps(dict(sorted(prompts.items())), indent=1, ensure_ascii=False))


def like(s, finished):
    """Make a finished take this sound's exemplar, the one the judge hears as what a person wants."""
    EXEMPLARS.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(finished, EXEMPLARS / f"{s.letter}.wav")
