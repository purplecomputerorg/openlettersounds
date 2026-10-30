"""wav2vec2 IPA phoneme recognizer (Apache-2.0, ONNX): what a listener hears, and how close a take is to a reference."""
import json
import urllib.request
from functools import cache
from pathlib import Path

import numpy as np

from . import ROOT

REPO = "https://huggingface.co/onnx-community/wav2vec2-lv-60-espeak-cv-ft-ONNX/resolve/main"
DIR = ROOT / "models" / "wav2vec2-espeak"
RATE = 16000
SPECIAL = ("<pad>", "<s>", "</s>", "<unk>")


def _fetch():
    DIR.mkdir(parents=True, exist_ok=True)
    for remote, local in (("onnx/model_int8.onnx", "model.onnx"), ("vocab.json", "vocab.json")):
        if not (DIR / local).exists():
            urllib.request.urlretrieve(f"{REPO}/{remote}", DIR / local)


@cache
def _model():
    import onnxruntime as ort
    _fetch()
    vocab = json.loads((DIR / "vocab.json").read_text())
    return ort.InferenceSession(str(DIR / "model.onnx")), {v: k for k, v in vocab.items()}


def posteriors(x16):
    sess, _ = _model()
    x = (x16 - x16.mean()) / (x16.std() + 1e-7)
    x = np.concatenate([np.zeros(4000, np.float32), x.astype(np.float32), np.zeros(4000, np.float32)])
    logits = sess.run(None, {sess.get_inputs()[0].name: x[None, :]})[0][0]
    e = np.exp(logits - logits.max(-1, keepdims=True))
    return e / e.sum(-1, keepdims=True)


def heard(post):
    _, inv = _model()
    out, prev = [], None
    for i in post.argmax(-1):
        if i != prev and inv[i] not in SPECIAL:
            out.append(inv[i])
        prev = i
    return out


def _speech(post):
    """Frames where the model hears something other than silence."""
    blank = post[:, 0]
    keep = post[blank < 0.5]
    return keep if len(keep) else post[[int(blank.argmin())]]


def distance(a, b):
    """DTW over speech frames with -log(p.q) cost; 0 is identical, larger is less alike."""
    a, b = _speech(a), _speech(b)
    cost = -np.log(np.clip(a @ b.T, 1e-6, None))
    n, m = cost.shape
    d = np.full((n + 1, m + 1), np.inf)
    d[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i, j] = cost[i - 1, j - 1] + min(d[i - 1, j], d[i, j - 1], d[i - 1, j - 1])
    return float(d[n, m] / (n + m))
