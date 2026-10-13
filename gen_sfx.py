#!/usr/bin/env python3
"""Discrete SFX for THE REDSHIRE RESCUE — all synthesized, no recorded sources.
gunshot_close.wav  - single sharp crack (1s)
gunfire_close_seq.wav - 10s sequence for shot 3 (balcony ambush)
gunfire_distant_seq.wav - 12s sequence for shot 5 (street chase)
"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
import os

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", "sfx")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(21)

def save(name, x, peak_db=-12):
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (peak_db / 20)
    st = np.stack([x, x], axis=1)
    wavfile.write(os.path.join(OUT, name), SR, (np.clip(st, -1, 1) * 32767).astype(np.int16))
    print(name, f"{len(x)/SR:.1f}s")

def gunshot(distant=False):
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    # crack: broadband burst, very fast decay
    crack = rng.standard_normal(n) * np.exp(-t / 0.045)
    sos = butter(4, 2500 / (SR / 2), btype="high", output="sos")
    crack = sosfilt(sos, crack) * 0.8
    # slap: midrange punch that survives phone speakers (800-2500Hz)
    slap = rng.standard_normal(n) * np.exp(-t / 0.09)
    sos = butter(4, [800 / (SR / 2), 2500 / (SR / 2)], btype="band", output="sos")
    slap = sosfilt(sos, slap) * 0.9
    # body: midrange thump
    body = rng.standard_normal(n) * np.exp(-t / 0.16)
    sos = butter(4, [300 / (SR / 2), 3000 / (SR / 2)], btype="band", output="sos")
    body = sosfilt(sos, body) * 0.7
    # chest punch + sub thump
    punch = np.sin(2 * np.pi * 120 * t) * np.exp(-t / 0.15) * 0.5
    thump = np.sin(2 * np.pi * 58 * t) * np.exp(-t / 0.22) * 0.7
    s = crack + slap + body + punch + thump
    if distant:
        sos = butter(4, 900 / (SR / 2), btype="low", output="sos")
        s = sosfilt(sos, s)
        # longer tail for distance
        tail = rng.standard_normal(n) * np.exp(-t / 0.5) * 0.15
        sos = butter(4, 400 / (SR / 2), btype="low", output="sos")
        s = s + sosfilt(sos, tail)
    return s / (np.max(np.abs(s)) + 1e-9)

def sequence(dur, times, distant=False, gain_var=0.25):
    n = int(SR * dur)
    s = np.zeros(n)
    g = gunshot(distant)
    for t0 in times:
        i = int(t0 * SR)
        L = min(len(g), n - i)
        if L <= 0:
            continue
        s[i:i+L] += g[:L] * rng.uniform(1 - gain_var, 1 + gain_var)
    return s

save("gunshot_close.wav", gunshot(False))
# shot 3: balcony ambush — sharp close cracks as tracers rip overhead
save("gunfire_close_seq.wav", sequence(10.0, [1.6, 3.6, 5.7, 7.5, 9.0], distant=False), -10)  # pause-aligned to narration gaps
# shot 5: street chase — distant rolling fire, hunters spraying wild
save("gunfire_distant_seq.wav", sequence(12.0, [1.0, 2.7, 4.4, 7.1, 8.9, 10.6], distant=True), -14)
print("done ->", OUT)
