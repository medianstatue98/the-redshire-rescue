#!/usr/bin/env python3
"""Word-level caption timing for narration via faster-whisper (cached small model, offline).
Decodes with ffmpeg to 16kHz mono s16le raw, passes numpy float32 to transcribe().
Proxy env vars must be unset (see AGENTS.md)."""
import json, subprocess, numpy as np, os

AUDIO = "audio"
OUT = "audio/caption_timing.json"

def decode(path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000",
                        "-f", "s16le", "-"], capture_output=True)
    a = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return a

from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")

result = {}
for i in range(1, 10):
    f = os.path.join(AUDIO, f"narr_shot{i}.mp3")
    audio = decode(f)
    segments, _ = model.transcribe(audio, language="en", word_timestamps=True,
                                   vad_filter=True)
    words = []
    for seg in segments:
        for w in (seg.words or []):
            words.append({"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)})
    result[f"shot{i}"] = words
    print(f"shot{i}: {len(words)} words, last_end={words[-1]['e'] if words else 0}")

with open(OUT, "w") as fh:
    json.dump(result, fh, indent=1)
print("wrote", OUT)
