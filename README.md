# nemophones

Open phonics sounds: one clean clip per letter sound, free for any use.

`sounds/en-us/marin/` has the 26 letter sounds of US English phonics (short vowels, hard C and G, X as /ks/, Q as /kw/), with `sounds.json` giving each clip's IPA, example words, and the exact prompt and take that produced it. Clips are mono 16-bit WAV, trimmed and level-matched. Entries with `"reviewed": false` passed the automatic checks but have not yet had a final listen.

## How the sounds are made

1. **Generate.** OpenAI's `gpt-audio-1.5` (voice `marin`) is prompted as a phonics teacher, from a text spec per sound in `nemophones/sounds.py`: example words, how it is made, what it is not ("short A as in apple, not 'ah'"). Each sound gets 20 to 40 takes. Once a person has picked a take they like, `like` makes it that sound's exemplar (`exemplars/marin/`), and later takes are generated with it attached as audio and asked to sound like it. Only our own takes are ever given to the generator; third-party reference audio never is.
2. **Check.** Every take is measured and rejected if a listener would object: a breath or pause before the sound, noise instead of a crisp release, a voiced stop that came out unvoiced (B sounding like P), an added "uh", a hold that wobbles, static in place of a hiss. A wav2vec2 phoneme recognizer reports what it hears.
3. **Rank.** Takes the recognizer hears cleanly come first, then by how close they are to reference recordings of the same sound, compared frame by frame on the recognizer's output. That closeness separates held sounds well but barely separates clipped stops, so with `--judge` a second listener re-ranks the top six: `gpt-audio-1.5` hears the teachers' reference recordings, then two of our takes, and says which one a child should hear (clearly the sound, natural and warm, not harsh or spitty). Every pair is played in both orders, takes are re-ranked by wins, and every verdict with its reason is cached under `build/judge/`.
4. **Finish.** The best take is trimmed to the sound, long holds are capped with a fade, and every clip is set to the same loudness.
5. **Listen.** `build/review.html` shows references, passing takes and rejected takes with reasons, for a final human pass.

### Why an audio language model, not text to speech

Text to speech engines (Piper, Kokoro, ElevenLabs and the like) speak whatever text they are given. A pure sound has no spelling they can read: "b" comes out as "bee", "buh" keeps the "uh" phonics teachers avoid, and a description of the sound is read aloud. Cutting the sound out of a spoken word leaves clicks and pieces of the next vowel. An audio language model like `gpt-audio-1.5` instead takes the description as instructions for how to speak ("clipped, voiced, no vowel after it"), so the sound can be specified in words. TTS can still do well on sounds that spell easily ("mmm", "sss") and on vowels; the checks below do not care where a take comes from, so another generator could be added as a second voice and compared on the same terms.

### Worked example: B

**The spec.** One line in `nemophones/sounds.py`:

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
| Glide | Q W X Y | the sound alone, stopped before any vowel (X is the /ks/ at the end of 'fox') | Letter W: produce the /w/ sound heard at the start of 'web', 'wet', 'wig': tightly rounded lips gliding open, stopping the instant the lips open, before your mouth settles into any vowel: 'wet' with the 'et' removed, about a fifth of a second. NOT 'wuh'. |

`python -m nemophones prompts` prints the system message and all 26 user messages exactly as sent.

**[Listen and pick](https://tavinathanson.github.io/nemophones/)**: every passing take per letter. Star the best ones and send your picks as a GitHub issue.

## Run it

```bash
pip install -e .                     # numpy, onnxruntime, httpx; ffmpeg on PATH
python -m nemophones refs            # download references to refs/ (not redistributed)
python -m nemophones prompts [letters] # print the exact messages sent to the model
cp .env.example .env                 # then put your OpenAI key in .env
python -m nemophones generate [letters] --takes 10
python -m nemophones check [letters] [--judge] # gate, rank (--judge: audio model re-ranks the top, needs the key), write the best take to sounds/
python -m nemophones like b 37       # make take 37 of B its exemplar; generate again to get takes like it
python -m nemophones page            # build/review.html
python -m nemophones site            # docs/: the public picking page (GitHub Pages, main /docs)
```

Takes are cached by a hash of the model, voice and prompt, so editing a sound's spec starts a fresh set and rerunning is free.

## Licenses

- **Sounds** (`sounds/`): [CC0 1.0](sounds/LICENSE). The voice is synthetic (OpenAI `gpt-audio-1.5`, `marin`).
- **Code**: [MIT](LICENSE).
- **References** are only compared against (by the recognizer, and by the judge model when `--judge` is on) and are never shipped or given to the generator: [Feed the Monster](https://github.com/curiouslearning/FeedTheMonsterJS) by Curious Learning (CC BY) and Wikipedia's IPA recordings on Wikimedia Commons (CC BY-SA, CC0, public domain).
- **Recognizer**: [wav2vec2-lv-60-espeak-cv-ft](https://huggingface.co/facebook/wav2vec2-lv-60-espeak-cv-ft) (Apache-2.0), downloaded to `models/` on first use.
