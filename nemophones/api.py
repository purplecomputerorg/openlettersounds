"""OpenAI Chat Completions calls shared by the generator and the judge."""
import base64
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx


def chat(body):
    r = httpx.post("https://api.openai.com/v1/chat/completions", json=body, timeout=120,
                   headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]


def audio_part(path):
    """A wav or mp3 file as a message content part the model listens to."""
    path = Path(path)
    return {"type": "input_audio", "input_audio": {"data": base64.b64encode(path.read_bytes()).decode(),
                                                   "format": path.suffix.lstrip(".")}}


def pmap(fn, jobs, name=str):
    """Run fn over jobs 8 at a time; print failures instead of stopping, return results (None where it failed)."""
    def safe(job):
        try:
            return fn(job)
        except (httpx.HTTPError, ValueError, KeyError) as e:
            print(f"{name(job)}: {e}")
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(safe, jobs))
