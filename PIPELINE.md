# Production pipeline — THE REDSHIRE RESCUE

Every step below is reproducible from the files in this repo. Nothing here
depends on a proprietary account except the generative steps (image / video /
TTS), which list the exact prompts and can be run on any equivalent model.

## 0. Source material

- Novel text: *Snowmoon* by Vitalik Buterin, GPL v3, fetched 2026-10-13 from
  the official HTML edition (one file per chapter). Only Chapter 26 was used,
  and only as a story reference — the narration script is original.
- Scene selection: all 32 chapters were skimmed for a self-contained,
  visually striking sequence. Chapter 26's Redshire rescue won: a four-beat
  heist arc (setup / ambush / improvisation / escape), drone-carried action
  (minimal character animation), one night-city environment, no crowds.

## 1. Script (`script.md`)

9 shots x ~10s. Narration written fresh (~200 words, ~140 wpm), one narrator.
Each shot entry carries its narration line and a visual description.

## 2. Stills (`prompts.md`, `stills/`)

For each shot: generate a 16:9 still from the shot's still prompt, copied
verbatim. Every prompt starts with the shared STYLE LOCK:

> Cinematic 2D animation, painterly night palette (indigo / amber / teal),
> geometric quadcopter drones with glowing rotor rings, film grain.
> No photorealism, no 3D-render look, no text, no watermarks.

Each still was viewed and frame-checked against its prompt before animation.
Two framings were refused by the image model and re-staged (documented in
`prompts.md`): shot 4 became the loss landing on Zei's tactical screen,
shot 6 became the crash seen as street-level aftermath.

## 3. Animation

Each approved still was animated image-to-video (~10s, 16:9) with the shot's
animate prompt + a shared MOTION LOCK (slow cinematic move, no morphing,
no text). 9 clips total.

## 4. Narration

9 segments synthesized separately (one per shot) with a TTS engine,
somber male narrator, speed 100. Kept per-shot (not one file) so each shot's
video tail can be trimmed to its narration. One segment mis-rendered at 60s
and was re-synthesized after slightly rewording the line (TTS cache note).

## 5. Caption timing (`gen_captions.py`)

Word-level timestamps via faster-whisper (`small` model, offline):
decode to 16kHz mono with ffmpeg, pass a numpy float32 array to
`transcribe(..., word_timestamps=True)`. Output: `caption_timing.json`.

## 6. Ambience beds (`gen_beds.py`)

All beds are synthesized in numpy (44.1kHz stereo) — brown/pink noise,
filtered hums, rotor harmonics, sea swell LFO, fire crackle transients.
No recorded sources, so no voice/breath artifacts are possible by
construction. Per-shot mapping lives in `build_film.py` (SHOT_BED).

## 6b. Discrete SFX (`gen_sfx.py`)

Gunshots and extra rotor presence are synthesized the same way as the beds
(no recorded sources). `gunfire_close_seq.wav` (shot 3, the balcony ambush)
and `gunfire_distant_seq.wav` (shot 5, the street chase) are timed sequences
of single synthesized cracks; rotors are layered under shots 1 and 3.
Discrete SFX are mixed single-play at higher gain than the looped beds,
ducked under the narration, then through the same -16 LUFS chain.

## 7. Assembly (`build_film.py`)

For each shot:
- clip normalized to 1280x720p24, native audio stripped (`-an`) — generated
  clips ship baked-in audio of unknown provenance and it is never trusted;
- shot length = max(10s, narration end + 0.9s); overruns loop the clip;
- narration delayed 0.3s + bed(s) at low level, mixed to -16 LUFS;
- karaoke captions: word timings -> ASS `\k` tags (DejaVu Sans Bold 44,
  white sweep to yellow), burned in with libass;
- 3s title end card appended;
- final mux uses explicit `-map 0:v:0 -map 1:a:0`, then verifies the output
  audio correlates ~1.0 with the intended mix (guards against silently
  keeping the wrong audio track) and checks peak headroom.

## 8. QC

- Frame grabs reviewed at 7 timestamps (captions, style, end card).
- Audio: correlation 1.000 vs intended mix, peak -1.3 dB, modulation-spectrum
  check for rhythmic tonal pulsing: clean.

## Tools / models

- Image + video: generative media pipeline (prompts in `prompts.md`)
- TTS: `tts` CLI, voice `avocado_v2:qvd_01700`, speed 100, English
- Captions: faster-whisper `small`, int8, CPU
- Everything else: Python 3.12, numpy, scipy, ffmpeg 6+/7+ (libx264, aac, libass), DejaVu fonts
