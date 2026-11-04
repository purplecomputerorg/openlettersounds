# Open Letter Sounds

Free phonics sounds for US English: one clean, short clip for each of the 26 letter sounds, plus alternates. [CC0](sounds/LICENSE), so you can use them in anything, with no credit needed.

Made by [Purple Computer](https://purplecomputer.org).

**[▶ Listen and download](https://purplecomputerorg.github.io/openlettersounds/)**

## Use the sounds

1. **Download** [the zip](https://purplecomputerorg.github.io/openlettersounds/openlettersounds-en-us-marin.zip), or grab single clips from the [library page](https://purplecomputerorg.github.io/openlettersounds/) or [`sounds/en-us/marin/`](sounds/en-us/marin/).
2. **Play** `a.wav` through `z.wav`. Every clip is mono 16-bit WAV, trimmed to the sound and set to the same loudness, so they sit well side by side.
3. **Optional:** read `sounds.json` for each clip's IPA, example words and alternate takes.

What each letter says:

- **Short vowels:** A as in apple, E as in egg, I as in itch, O as in octopus, U as in up.
- **Hard C and G:** C as in cat, G as in goat.
- **Q as /kw/** (queen) and **X as /ks/** (the end of fox).
- Stops are clipped with no added "uh" (say "b", never "buh"); sounds like M and S are held.

### `sounds.json`

One entry per letter:

```json
{
  "letter": "b",
  "ipa": "/b/",
  "kind": "stop",
  "keywords": ["ball", "bat", "bed"],
  "reviewed": true,
  "file": "b.wav",
  "alts": []
}
```

- `reviewed: true` means a person listened and picked it. `false` means it passed the automatic checks but has not had a final listen yet.
- `alts` lists alternate takes of the same sound (`b-alt1.wav` and so on), also picked by a person, for apps that want some variety.
- `generator` and `judge` (not shown) record the exact prompt and take that produced the clip, so every sound can be traced back to its source.

### Suggest alternates

On the [library page](https://purplecomputerorg.github.io/openlettersounds/), turn on **Show new takes to suggest as alternates**, star the takes you like, and press **Send**. That opens a GitHub issue with your picks filled in.

## Make the sounds yourself

You need Python 3.11+, `ffmpeg` on your PATH, and an OpenAI API key. A Gemini key is optional (it makes the judge step better).

```bash
pip install -e .
cp .env.example .env                           # add your OpenAI key (and GEMINI_API_KEY if you have one)
python -m openlettersounds refs                # download reference recordings to refs/
python -m openlettersounds generate b --takes 10
python -m openlettersounds check b --judge     # reject bad takes, rank the rest, write the best to sounds/
python -m openlettersounds page                # open build/review.html to listen
```

Leave off the letters (`b` above) to run all 26. Takes are cached by a hash of the model, voice and prompt, so rerunning is free, and editing a sound's spec starts a fresh set.

| Command | What it does |
|---|---|
| `refs` | Download reference recordings to `refs/` (compared against, never shipped) |
| `prompts [letters]` | Print the exact messages sent to the model |
| `generate [letters] --takes N` | Record N new takes per sound |
| `check [letters] [--judge]` | Gate and rank takes; `--judge` has an audio model re-rank the top six |
| `pick < picks.txt` | Keep picks pasted from the page (`b: take 37` lines): a letter's first pick becomes its clip, later ones alternates |
| `page` | Build `build/review.html`: references, passing takes, and rejected takes with reasons |
| `site` | Build `docs/`: the public library page and zip (GitHub Pages serves `main /docs`) |
| `all` | `refs`, `generate`, `check`, `page` and `site` in one go |

## How the sounds are made

1. **Generate.** OpenAI's `gpt-audio-1.5` (voice `marin`) is prompted as a phonics teacher, from a text spec per sound in `openlettersounds/sounds.py`: example words, how it is made, what it is not ("short A as in apple, not 'ah'"). Each sound gets 20 to 40 takes. No audio is given to the model. Attaching a take a person had picked, and asking for more like it, was tried and made later takes shorter, noisier and buzzier for almost every sound, so picks guide the judge instead (below).
2. **Check.** Every take is measured and rejected if a listener would object: a breath or pause before the sound, noise instead of a crisp release, a voiced stop that came out unvoiced (B sounding like P), an added "uh", a hold that wobbles, static in place of a hiss. A wav2vec2 phoneme recognizer reports what it hears.
3. **Rank.** Takes the recognizer hears cleanly come first, then by how close they are to reference recordings of the same sound, compared frame by frame on the recognizer's output. That closeness separates held sounds well but barely separates clipped stops, so with `--judge` a second listener re-ranks the top six: Gemini (its latest Pro model) when `GEMINI_API_KEY` is set, else `gpt-audio-1.5`, hears the teachers' reference recordings, then two of our takes, and says which one a child should hear (clearly the sound, natural and warm, not harsh or spitty). Once a person has picked a take for a sound (`exemplars/marin/`), the judge hears it too, as the sound and feel they want. Every pair is played in both orders, takes are re-ranked by wins, and every verdict with its reason is cached under `build/judge/`.
4. **Finish.** The best take is trimmed to the sound, long holds are capped with a fade, and every clip is set to the same loudness.
5. **Listen and pick.** `build/review.html` shows references, passing takes and rejected takes with reasons; the public page shows each letter's kept clips, then the new takes to star. `pick` takes the starred list: a letter's first pick becomes its library clip, which later runs never replace, and every later pick becomes an alternate.

### Why an audio language model, not text to speech

Text to speech engines (Piper, Kokoro, ElevenLabs and the like) speak whatever text they are given. A pure sound has no spelling they can read: "b" comes out as "bee", "buh" keeps the "uh" phonics teachers avoid, and a description of the sound is read aloud. Cutting the sound out of a spoken word leaves clicks and pieces of the next vowel. An audio language model like `gpt-audio-1.5` instead takes the description as instructions for how to speak ("clipped, voiced, no vowel after it"), so the sound can be specified in words. TTS can still do well on sounds that spell easily ("mmm", "sss") and on vowels; the checks below do not care where a take comes from, so another generator could be added as a second voice and compared on the same terms.

### Worked example: B

**The spec.** One line in `openlettersounds/sounds.py`:

```python
_stop("b", "/b/", ("ball", "bat", "bed"), True, "p")   # letter, IPA, example words, voiced, voiceless partner
```

`_stop` fills in the wording every stop shares (crisp, no "uh") and, because B is voiced, a line about the buzz and the partner it must not turn into.

**The prompt.** Each take is one Chat Completions request with two messages. This is the complete text the model sees for B:

> **System:** You are an expert early-literacy phonics teacher recording audio for a children's reading app. You model 'pure sounds' the way Jolly Phonics, UFLI and Letters and Sounds teach them: stop sounds are clipped with no added schwa, continuous sounds are held, vowels are short. When asked for a sound, your entire spoken reply is ONLY that one sound, said once, warm and clear, at normal speaking volume. Begin the sound instantly, with no breath, click or pause before it, and stop cleanly with no breath after. It must sound like a clean studio recording: no static, rumble, hiss or background noise. Never whisper and never sound breathy. Never say the letter name, the example word, or any other words.
>
> **User:** Letter B: produce the /b/ sound heard at the start of 'ball', 'bat', 'bed': a clear, crisp b with a light release and no 'uh' vowel after it (say 'b', never 'buh'). It is VOICED: your voice buzzes as it releases, like the start of 'ball'. It must not sound like 'p'.

```json
{"model": "gpt-audio-1.5", "modalities": ["text", "audio"], "audio": {"voice": "marin", "format": "wav"},
 "messages": [{"role": "system", "content": "<system above>"}, {"role": "user", "content": "<user above>"}]}
```

The same request is sent 40 times; the model varies on its own, so each reply is a different take. Takes are saved under `takes/marin/b-<hash>/`, where the hash covers the model, voice and both messages.

**The checks.** B is a stop, so a take fails if it has more than 80 ms of breath or silence before the sound, is loud for more than 300 ms (noise, not a release), runs past 400 ms (something trails the release), has under 30 ms of voicing (it came out as P), has more than 100 ms of voicing plus a vowel the recognizer hears (an added "uh"), or the recognizer's first sound is not "b". Of the 40 B takes, 9 passed. The most common failures were the recognizer hearing something else (29), sound trailing the release (20) and noise (15); 10 came out unvoiced.

**The pick.** Take 9 ranked first: the recognizer heard exactly "b", the sound lasts 230 ms with 210 ms of voicing and no breath before it. It was trimmed with 40 ms of room on each side and set to the library loudness (main part at -20 dBFS RMS, peaks at most -0.5 dBFS), then written to `sounds/en-us/marin/b.wav`. `sounds.json` records both messages and the take, so the clip can be traced back to exactly what produced it.

### How the other kinds differ

The system message is the same for every sound. The user message changes with the kind of sound:

| Kind | Letters | What the prompt asks for | Example (user message) |
|---|---|---|---|
| Stop | B C D G H J K P T | clipped, no "uh"; voiced ones name their partner, unvoiced ones ask for a soft puff, not a spitty burst (H is one gentle puff) | the B prompt above |
| Hold | F L M N R S V Z | held for about two thirds of a second (F and S half a second), no vowel around it | Letter S: produce the /s/ sound heard at the start of 'sun', 'sit', 'sock': a clean, sharp, high-pitched snake hiss 'sss' made with the tongue just behind the top teeth, unvoiced, held steadily for about half a second, no vowel before or after it. NOT breathy air, static or a low rumble. |
| Vowel | A E I O U | short, steady, fully voiced, about a third of a second | Letter A: produce the short A vowel /æ/, as in 'apple', 'cat', 'hat': a short, steady, fully voiced vowel with a pure clear tone, never breathy, about a third of a second. NOT 'ah' as in 'father', or 'ay' as in 'cake'. |
| Glide | Q W X Y | the sound alone, stopped before any vowel (X is the /ks/ at the end of 'fox'); W and Y fully voiced, with only the faintest hint of a vowel | Letter W: produce the /w/ sound heard at the start of 'web', 'wet', 'wig': lips tightly rounded as for 'oo', voice on from the very start, gliding open into only the faintest clipped hint of a vowel, the way a teacher says it at the start of 'wet', about a quarter of a second. Fully voiced and clearly audible, never whispered or breathy. NOT a long 'wuh', or the letter name 'double-u'. |

`python -m openlettersounds prompts` prints the system message and all 26 user messages exactly as sent.

## Licenses

- **Sounds** (`sounds/`): [CC0 1.0](sounds/LICENSE). The voice is synthetic (OpenAI `gpt-audio-1.5`, `marin`).
- **Code**: [MIT](LICENSE).
- **References** are only compared against (by the recognizer, and by the judge model when `--judge` is on) and are never shipped or given to the generator: [Feed the Monster](https://github.com/curiouslearning/FeedTheMonsterJS) by Curious Learning (CC BY) and Wikipedia's IPA recordings on Wikimedia Commons (CC BY-SA, CC0, public domain).
- **Recognizer**: [wav2vec2-lv-60-espeak-cv-ft](https://huggingface.co/facebook/wav2vec2-lv-60-espeak-cv-ft) (Apache-2.0), downloaded to `models/` on first use.
