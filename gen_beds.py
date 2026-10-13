#!/usr/bin/env python3
"""Procedural ambience beds for THE REDSHIRE RESCUE.
All beds are synthesized (no recorded sources), so they cannot contain
voice/breathing/mouth artifacts. 44.1kHz stereo 16-bit WAV.
"""
import numpy as np
from scipy.io import wavfile
import os

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", "beds")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)

def stereo(mono, width=0.15):
    l = mono * (1 - width * 0.5) + np.roll(mono, 37) * width * 0.5
    r = mono * (1 - width * 0.5) + np.roll(mono, -41) * width * 0.5
    return np.stack([l, r], axis=1)

def brown(n):
    w = rng.standard_normal(n)
    b = np.cumsum(w)
    b -= np.linspace(b[0], b[-1], n)
    b /= np.max(np.abs(b)) + 1e-9
    return b

def fade(x, f=0.5):
    n = len(x); m = int(SR * f)
    w = np.ones(n); w[:m] = np.linspace(0, 1, m); w[-m:] = np.linspace(1, 0, m)
    return x * w

def save(name, x, peak_db=-20):
    x = x / (np.max(np.abs(x)) + 1e-9)
    x *= 10 ** (peak_db / 20)
    wavfile.write(os.path.join(OUT, name), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    print(name, f"{len(x)/SR:.1f}s")

def lowpass(x, cutoff, order=2):
    from scipy.signal import butter, sosfilt
    sos = butter(order, cutoff / (SR / 2), btype="low", output="sos")
    return sosfilt(sos, x)

def highpass(x, cutoff, order=2):
    from scipy.signal import butter, sosfilt
    sos = butter(order, cutoff / (SR / 2), btype="high", output="sos")
    return sosfilt(sos, x)

# 1. night city — distant urban hum
n = int(SR * 14)
bed = lowpass(brown(n), 320) * 0.7 + lowpass(rng.standard_normal(n), 120) * 0.15
save("city_night.wav", stereo(fade(bed)), -26)

# 2. console room — quiet electronic hum
n = int(SR * 14)
t = np.arange(n) / SR
bed = (np.sin(2*np.pi*55*t) * 0.5 + np.sin(2*np.pi*110*t) * 0.22
       + np.sin(2*np.pi*165*t) * 0.1 + lowpass(rng.standard_normal(n), 800) * 0.06)
save("console.wav", stereo(fade(bed)), -30)

# 3. tension — rising unease
n = int(SR * 12)
t = np.arange(n) / SR
from scipy.signal import butter, sosfilt
sweep = np.empty(n)
f0, f1 = 300, 2400
for i in range(0, n, SR):
    seg = slice(i, min(i + SR, n))
    fc = f0 + (f1 - f0) * (i / n)
    sos = butter(4, [fc*0.7/(SR/2), min(fc*1.4/(SR/2), 0.99)], btype="band", output="sos")
    sweep[seg] = sosfilt(sos, rng.standard_normal(seg.stop - seg.start))
bed = sweep * 0.4 + np.sin(2*np.pi*42*t) * 0.35 * (0.5 + 0.5*t/t[-1])
save("tension.wav", stereo(fade(bed)), -26)

# 4. explosion boom — deep burst + sub thump
n = int(SR * 7)
t = np.arange(n) / SR
decay = np.exp(-t / 1.1)
bed = lowpass(rng.standard_normal(n) * decay, 160) * 0.9 + np.sin(2*np.pi*46*t) * np.exp(-t/0.5) * 0.8
save("boom.wav", stereo(fade(bed, 0.2)), -14)

# 5. fire crackle — random transients over low rumble
n = int(SR * 12)
bed = lowpass(brown(n), 500) * 0.5
n_crack = 260
pos = rng.integers(0, n - 900, n_crack)
for p in pos:
    L = rng.integers(80, 900)
    env = np.exp(-np.arange(L) / (L * 0.25))
    bed[p:p+L] += rng.standard_normal(L) * env * rng.uniform(0.15, 0.6)
save("fire.wav", stereo(fade(bed)), -22)

# 6. drone rotors — blade hum + chop + motor whine (must survive phone speakers)
n = int(SR * 14)
t = np.arange(n) / SR
from scipy.signal import butter as _b, sosfilt as _s
# harmonic stack of the blade fundamental: reaches well into the phone band
harm_f = [86, 172, 258, 344, 430, 516, 688, 860, 1032]
harm_a = [0.40, 0.30, 0.22, 0.20, 0.18, 0.15, 0.12, 0.10, 0.08]
stack = sum(a * np.sin(2*np.pi*f*t + rng.uniform(0, 6.28)) for f, a in zip(harm_f, harm_a))
# blade-pass chop: quadcopter ~8000rpm, 2 blades -> ~266Hz AM + slow wobble
chop = 0.6 + 0.4 * np.sin(2*np.pi*266*t)
wobble = 0.75 + 0.25 * np.sin(2*np.pi*13*t)
bed = stack * chop * wobble
# air whoosh 800-2000Hz
sos = _b(4, [800/(SR/2), 2000/(SR/2)], btype="band", output="sos")
bed += _s(sos, rng.standard_normal(n)) * 0.20 * wobble
# motor/ESC whine around 2.4kHz — the tell-tale drone signature on small speakers
sos = _b(6, [2200/(SR/2), 2600/(SR/2)], btype="band", output="sos")
bed += _s(sos, rng.standard_normal(n)) * 0.10 * wobble
save("rotors.wav", stereo(fade(bed)), -22)

# 7. sea — slow swell LFO on brown noise
n = int(SR * 16)
t = np.arange(n) / SR
lfo = 0.55 + 0.45 * np.sin(2*np.pi*0.12*t + 1.0)
bed = lowpass(brown(n), 480) * lfo
save("sea.wav", stereo(fade(bed, 1.0)), -24)

# 8. dawn — soft airy quiet
n = int(SR * 14)
bed = highpass(lowpass(rng.standard_normal(n), 4000), 900) * 0.25 + np.sin(2*np.pi*320*np.arange(n)/SR) * 0.05
save("dawn.wav", stereo(fade(bed, 1.0)), -32)

# 9. strobe electrical — gated hum for the streetlight chaos
n = int(SR * 14)
t = np.arange(n) / SR
gate = (np.sin(2*np.pi*7*t) > -0.2).astype(float) * 0.8 + 0.2
bed = np.sin(2*np.pi*120*t) * 0.4 * gate + lowpass(rng.standard_normal(n), 1000) * 0.2 * gate
save("strobe.wav", stereo(fade(bed)), -26)

print("done ->", OUT)
