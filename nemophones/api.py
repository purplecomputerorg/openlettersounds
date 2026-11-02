"""Model API calls shared by the generator and the judge: OpenAI Chat Completions, and Gemini for listening."""
import base64
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from . import ROOT


def env(name):
    """A key from the environment, else from the repo's .env."""
    path = ROOT / ".env"
    lines = path.read_text().splitlines() if path.exists() else []
    found = dict(l.split("=", 1) for l in lines if "=" in l and not l.startswith("#"))
    return os.environ.get(name) or found.get(name, "").strip().strip("'\"")


def _post(url, body, headers):
    r = httpx.post(url, json=body, timeout=180, headers=headers)
    r.raise_for_status()
    return r.json()


def chat(body):
    return _post("https://api.openai.com/v1/chat/completions", body,
                 {"Authorization": f"Bearer {env('OPENAI_API_KEY')}"})["choices"][0]["message"]


def _b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def audio_part(path):
    """A wav or mp3 file as an OpenAI message content part the model listens to."""
    return {"type": "input_audio", "input_audio": {"data": _b64(path), "format": Path(path).suffix.lstrip(".")}}


def listen(model, system, items):
    """Text reply from a model that hears items: a list of strings and audio file paths, in order."""
    if model.startswith("gemini"):
        parts = [{"inline_data": {"mime_type": f"audio/{i.suffix.lstrip('.')}", "data": _b64(i)}} if isinstance(i, Path)
                 else {"text": i} for i in items]
        out = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    {"system_instruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": parts}],
                     "generationConfig": {"responseMimeType": "application/json"}},
                    {"x-goog-api-key": env("GEMINI_API_KEY")})
        return "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"])
    content = [audio_part(i) if isinstance(i, Path) else {"type": "text", "text": i} for i in items]
    return chat({"model": model, "modalities": ["text"],
                 "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}]})["content"]


def pmap(fn, jobs, name=str):
    """Run fn over jobs 8 at a time; print failures instead of stopping, return results (None where it failed)."""
    def safe(job):
        try:
            return fn(job)
        except (httpx.HTTPError, ValueError, KeyError) as e:
            print(f"{name(job)}: {e}")
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(safe, jobs))
