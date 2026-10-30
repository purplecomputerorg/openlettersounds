"""Reading, measuring and finishing clips. All analysis runs on mono float32."""
import subprocess
import wave
from pathlib import Path

import numpy as np

FRAME_MS = 10
LEVEL_RMS = 0.1  # loud-part RMS every finished clip is matched to (about -20 dBFS)


def read(path, sr=None):
    """Any format ffmpeg reads, as (rate, mono float32); resampled when sr is given."""
    args = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1"] + (["-ar", str(sr)] if sr else []) + ["-f", "f32le", "-"]
    raw = subprocess.run(args, capture_output=True, check=True).stdout
    return sr or _rate(path), np.frombuffer(raw, np.float32).copy()


def _rate(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout
    return int(out.strip())


def write(path, x, sr):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def envelope(x, sr):
    f = sr * FRAME_MS // 1000
    n = len(x) // f
    return np.sqrt((x[:n * f].reshape(n, f) ** 2).mean(axis=1) + 1e-12)


def segments(x, sr):
    """(start, main, end) in frames: sound edge at 6% of peak RMS, main event at 30%."""
    r = envelope(x, sr)
    edge, main = np.nonzero(r > 0.06 * r.max())[0], np.nonzero(r > 0.3 * r.max())[0]
    return edge[0], main[0], edge[-1] + 1


def voiced_ms(x, sr):
    """Longest run of loud frames with a periodic (80-400 Hz) autocorrelation peak."""
    f, peak = sr * 20 // 1000, np.abs(x).max() + 1e-9
    best = run = 0
    for s in range(0, len(x) - f, f // 2):
        w = x[s:s + f] - x[s:s + f].mean()
        ac = np.correlate(w, w, "full")[f - 1:]
        voiced = np.sqrt((w ** 2).mean()) > 0.05 * peak and ac[sr // 400:sr // 80].max() > 0.5 * ac[0]
        run = run + 1 if voiced else 0
        best = max(best, run)
    return best * 10


def measure(x, sr):
    start, main, end = segments(x, sr)
    r = envelope(x, sr)
    return dict(preroll_ms=int(main - start) * FRAME_MS, sound_ms=int(end - start) * FRAME_MS,
                loud_ms=int((r > 0.25 * r.max()).sum()) * FRAME_MS, voiced_ms=voiced_ms(x, sr))


def _fade(y, sr, ms_in, ms_out):
    a, b = sr * ms_in // 1000, sr * ms_out // 1000
    y[:a] *= np.linspace(0, 1, a)
    y[len(y) - b:] *= np.linspace(1, 0, b)
    return y


def finish(x, sr, max_ms=None):
    """Trim to the sound with 40 ms of room, cap held sounds with a gentle fade, match loudness."""
    f = sr * FRAME_MS // 1000
    start, _, end = segments(x, sr)
    pad = sr * 40 // 1000
    y = x[max(0, start * f - pad):min(len(x), end * f + pad)].copy()
    if max_ms and len(y) > sr * max_ms // 1000:
        y = _fade(y[:sr * max_ms // 1000], sr, 5, 150)
    y = _fade(y, sr, 5, 15)
    r = envelope(y, sr)
    loud = r[r > 0.25 * r.max()]
    y *= LEVEL_RMS / np.sqrt((loud ** 2).mean())
    return y / max(1.0, np.abs(y).max() / 0.95)
