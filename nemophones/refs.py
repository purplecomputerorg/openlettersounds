"""Reference recordings, used only to check takes against. Never fed to a generator, never redistributed."""
import json
import urllib.parse
import urllib.request

from . import ROOT
from .sounds import SOUNDS

DIR = ROOT / "refs"
UA = {"User-Agent": "nemophones/0.1 (https://github.com/tavinathanson/nemophones)"}

# Feed the Monster (Curious Learning), audio CC BY: github.com/curiouslearning/FeedTheMonsterJS
FTM = "https://raw.githubusercontent.com/curiouslearning/FeedTheMonsterJS/main/lang/{lang}/audios/{name}.mp3"
FTM_ACCENTS = {"us": "english", "au": "australianenglish", "za": "southafricanenglish"}

# Wikipedia IPA demo recordings (CC BY-SA / CC0 / public domain) on Wikimedia Commons
WIKI = dict(a="Near-open front unrounded vowel.ogg", b="Voiced bilabial plosive.ogg", c="Voiceless velar plosive.ogg",
            d="Voiced alveolar plosive.ogg", e="Open-mid front unrounded vowel.ogg", f="Voiceless dentolabial fricative.ogg",
            g="Voiced velar plosive 02.ogg", h="Voiceless glottal approximant.wav", i="Near-close near-front unrounded vowel.ogg",
            j="Voiced palato-alveolar affricate.ogg", k="Voiceless velar plosive.ogg", l="Alveolar lateral approximant.ogg",
            m="Bilabial nasal.ogg", n="Alveolar nasal.ogg", o="Open back unrounded vowel.ogg", p="Voiceless bilabial plosive.ogg",
            q="Voiceless velar plosive.ogg", r="Alveolar approximant.ogg", s="Voiceless alveolar sibilant.ogg",
            t="Voiceless alveolar plosive.ogg", u="PR-open-mid back unrounded vowel2.ogg", v="Voiced labio-dental fricative.ogg",
            w="Voiced labio-velar approximant.ogg", y="Palatal approximant.ogg", z="Voiced alveolar sibilant.ogg")


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def _wiki_url(title):
    q = urllib.parse.urlencode(dict(action="query", titles=f"File:{title}", prop="imageinfo", iiprop="url", format="json"))
    page = next(iter(json.loads(_get(f"https://commons.wikimedia.org/w/api.php?{q}"))["query"]["pages"].values()))
    return page["imageinfo"][0]["url"]


def _sources(letter):
    """{label: (local path, url thunk)} for every reference a letter has."""
    found = {f"ftm-{a}": (DIR / f"ftm-{a}" / f"{letter}.mp3",
                          lambda lang=lang: FTM.format(lang=lang, name="qu" if letter == "q" else letter))
             for a, lang in FTM_ACCENTS.items()}
    if letter in WIKI:
        found["wiki"] = (DIR / "wiki" / f"{letter}{'.wav' if WIKI[letter].endswith('.wav') else '.ogg'}",
                         lambda: _wiki_url(WIKI[letter]))
    return found


def paths(letter):
    """Every reference on disk for a letter, as {label: path}."""
    return {k: p for k, (p, _) in _sources(letter).items() if p.exists()}


def fetch():
    for s in SOUNDS:
        for dst, url in _sources(s.letter).values():
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(_get(url()))
        print(s.letter, ", ".join(paths(s.letter)))
