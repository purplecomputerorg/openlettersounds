# nemophones

Open phonics sounds: one clean clip per letter sound, free for any use.

`sounds/en-us/marin/` has the 26 letter sounds of US English phonics (short vowels, hard C and G, X as /ks/, Q as /kw/), with `sounds.json` giving each clip's IPA, example words, and the exact prompt and take that produced it. Clips are mono 16-bit WAV, trimmed and level-matched. Entries with `"reviewed": false` passed the automatic checks but have not yet had a final listen.

## How the sounds are made

1. **Generate.** OpenAI's `gpt-audio-1.5` (voice `marin`) is prompted as a phonics teacher, from a text spec per sound in `nemophones/sounds.py`: example words, how it is made, what it is not ("short A as in apple, not 'ah'"). No reference audio is given to the model.
2. **Check.** Every take is rejected if a listener would object: a breath or pause before the sound, noise instead of a crisp release, a voiced stop that came out unvoiced (B sounding like P), an added "uh", a hold that wobbles. A wav2vec2 phoneme recognizer reports what it hears.
3. **Rank.** Survivors are ranked by how close they are to reference recordings of the same sound, compared frame by frame on the recognizer's output.
4. **Listen.** `build/review.html` shows references, passing takes and rejected takes with reasons, for a final human pass.

**[Listen and pick](https://tavinathanson.github.io/nemophones/)**: every passing take per letter. Star the best ones and send your picks as a GitHub issue.

## Run it

```bash
pip install -e .                     # numpy, onnxruntime, httpx; ffmpeg on PATH
python -m nemophones refs            # download references to refs/ (not redistributed)
OPENAI_API_KEY=... python -m nemophones generate [letters] --takes 10
python -m nemophones check [letters] # gate, rank, write the best take to sounds/
python -m nemophones page            # build/review.html
python -m nemophones site            # docs/: the public picking page (GitHub Pages, main /docs)
```

Takes are cached by a hash of the model, voice and prompt, so editing a sound's spec starts a fresh set and rerunning is free.

## Licenses

- **Sounds** (`sounds/`): [CC0 1.0](sounds/LICENSE). The voice is synthetic (OpenAI `gpt-audio-1.5`, `marin`).
- **Code**: [MIT](LICENSE).
- **References** are only compared against and are never shipped: [Feed the Monster](https://github.com/curiouslearning/FeedTheMonsterJS) by Curious Learning (CC BY) and Wikipedia's IPA recordings on Wikimedia Commons (CC BY-SA, CC0, public domain).
- **Recognizer**: [wav2vec2-lv-60-espeak-cv-ft](https://huggingface.co/facebook/wav2vec2-lv-60-espeak-cv-ft) (Apache-2.0), downloaded to `models/` on first use.
