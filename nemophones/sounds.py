"""The phoneme set: one entry per letter sound, the single source for prompts, checks and metadata."""
from dataclasses import dataclass

STOP, HOLD, VOWEL, GLIDE = "stop", "hold", "vowel", "glide"


@dataclass(frozen=True)
class Sound:
    letter: str
    ipa: str
    kind: str
    keywords: tuple
    how: str
    voiced: bool
    not_like: str = ""

    @property
    def name(self):
        return self.letter


def _stop(letter, ipa, keywords, voiced, partner=""):
    say = ipa.strip("/")
    how = f"a clear, crisp {say} with a light release and no 'uh' vowel after it (say '{say}', never '{say}uh')"
    if not voiced:
        how += ". It is UNVOICED: a soft, light puff of air, never a hard, spitty or hissy burst"
    if voiced:
        how += f". It is VOICED: your voice buzzes as it releases, like the start of '{keywords[0]}'. It must not sound like '{partner}'"
    return Sound(letter, ipa, STOP, keywords, how, voiced)


def _hold(letter, ipa, keywords, voiced, how, secs="two-thirds of a second", not_like=""):
    return Sound(letter, ipa, HOLD, keywords, f"{how}, held steadily for about {secs}, no vowel before or after it", voiced,
                 not_like)


def _vowel(letter, ipa, keywords, not_like):
    return Sound(letter, ipa, VOWEL, keywords, "a short, steady, fully voiced vowel with a pure clear tone, never breathy, "
                 "about a third of a second", True, not_like)


def _glide(letter, ipa, keywords, how, voiced, not_like=""):
    return Sound(letter, ipa, GLIDE, keywords, how, voiced, not_like)


SOUNDS = (
    _vowel("a", "/æ/", ("apple", "cat", "hat"), "'ah' as in 'father', or 'ay' as in 'cake'"),
    _stop("b", "/b/", ("ball", "bat", "bed"), True, "p"),
    _stop("c", "/k/", ("cat", "cup", "cot"), False),
    _stop("d", "/d/", ("dog", "dig", "dad"), True, "t"),
    _vowel("e", "/ɛ/", ("egg", "bed", "pet"), "'ee' as in 'see'"),
    _hold("f", "/f/", ("fish", "fan", "fun"), False, "top teeth on the lower lip, a soft unvoiced 'fff'", "half a second"),
    _stop("g", "/ɡ/", ("goat", "gum", "gap"), True, "k"),
    Sound("h", "/h/", STOP, ("hat", "hop", "hen"), "one short, gentle, unvoiced breathy puff, about a quarter of a second, no vowel after it", False),
    _vowel("i", "/ɪ/", ("itch", "sit", "pig"), "'eye', or 'ee' as in 'see'"),
    _stop("j", "/dʒ/", ("jam", "jet", "jug"), True, "ch"),
    _stop("k", "/k/", ("kite", "kid", "kit"), False),
    _hold("l", "/l/", ("lip", "leg", "lap"), True,
          "mouth open and lips apart, tongue tip pressed on the ridge just behind the top teeth, voice flowing around "
          "the sides of the tongue: a bright, clear 'lll', never hummed through the nose",
          not_like="'mmm' or 'nnn'"),
    _hold("m", "/m/", ("moon", "map", "mug"), True, "lips closed, humming 'mmm'", not_like="'nnn'"),
    _hold("n", "/n/", ("nest", "nap", "nut"), True, "lips apart, tongue tip on the ridge behind the top teeth, "
          "humming 'nnn' through the nose", not_like="'mmm'"),
    _vowel("o", "/ɑ/", ("octopus", "hot", "pot"), "'oh' as in 'go' (American short O, like 'ah')"),
    _stop("p", "/p/", ("pig", "pan", "pot"), False),
    _glide("q", "/kw/", ("queen", "quick", "quack"),
           "a crisp k gliding straight into w, stopping the instant the lips open, before any vowel, about a quarter of a second", False),
    _hold("r", "/ɹ/", ("red", "run", "rug"), True, "American 'rrr', tongue pulled back, not rolled"),
    _hold("s", "/s/", ("sun", "sit", "sock"), False,
          "a clean, sharp, high-pitched snake hiss 'sss' made with the tongue just behind the top teeth, unvoiced",
          "half a second", not_like="breathy air, static or a low rumble"),
    _stop("t", "/t/", ("top", "ten", "tub"), False),
    _vowel("u", "/ʌ/", ("up", "cup", "bus"), "'oo' as in 'moon', or 'you'"),
    _hold("v", "/v/", ("van", "vet", "vest"), True, "top teeth on the lower lip, a voiced buzz 'vvv'"),
    _glide("w", "/w/", ("web", "wet", "wig"),
           "tightly rounded lips gliding open, stopping the instant the lips open, before your mouth settles into any "
           "vowel: 'wet' with the 'et' removed, about a fifth of a second", True, "'wuh'"),
    _glide("x", "/ks/", ("fox", "box", "six"),
           "a crisp k straight into a short clean hiss, as at the END of the word, about a third of a second", False,
           "the letter name 'ecks'"),
    _glide("y", "/j/", ("yes", "yak", "yum"),
           "tongue high and forward, a short 'yy' glide that stops the instant it is made, before your mouth settles "
           "into any vowel: 'yes' with the 'es' removed, about a fifth of a second", True, "'yuh'"),
    _hold("z", "/z/", ("zoo", "zip", "zap"), True, "a voiced buzzing 'zzz' like a bee, one steady buzz",
          not_like="'sss', or a wobbling buzz"),
)

BY_LETTER = {s.letter: s for s in SOUNDS}
