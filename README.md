# THE REDSHIRE RESCUE — a Snowmoon story

A 98-second 2D animated short adapting the rescue-heist sequence from
**Chapter 26** of *Snowmoon* by Vitalik Buterin (GPL v3).

Submitted to the poidh bounty **"Bring Snowmoon to Life"**.

## The film

A teenager named Zei remotely pilots a drone squad to extract the president's
son from occupied Redshire. The plan collapses mid-air — so the team
improvises: they hack the city's streetlights, crash a decoy drone as cover,
and fly two cloaked figures out clinging to drone backs.

- Format: 16:9, 1280x720, 24fps, ~98 seconds, 9 shots
- Narration: original script (written for this film, not quoted from the novel),
  single narrator voice, with burned-in karaoke captions
- Sound: fully procedural ambience beds (synthesized, no recorded sources)

## License

This adaptation is a derivative of *Snowmoon* (GPL v3) and is released under
the **GNU General Public License v3** — see `LICENSE`. In the spirit of the
bounty's open-source requirement, everything meaningful from the production
process is published here: script, prompts, code, and pipeline docs.

## Reproduce it

1. Generate the 9 shot stills with any image model using `prompts.md`
   (each prompt includes the shared STYLE LOCK).
2. Animate each still (image-to-video) with the matching animate prompt.
3. Synthesize the 9 narration segments from `script.md`
   (any TTS voice; the original used a somber male narrator at ~140 wpm).
4. Generate word-level caption timings (`gen_captions.py`, faster-whisper).
5. Synthesize the ambience beds (`gen_beds.py` — pure Python/numpy, no samples).
6. Assemble everything (`build_film.py` — ffmpeg: normalize, mix, karaoke
   ASS burn-in, end card, explicit stream mapping).

See `PIPELINE.md` for the full step-by-step with the exact tools used.

## Production notes

- Shots 4 and 6 were re-staged after the image generator refused the original
  framings (midair drone explosion / drone impacting a wall). The re-stages —
  the loss landing on Zei's tactical screen, and the crash seen as street-level
  aftermath — are documented in `prompts.md` and were the stronger choice
  anyway.
- Generated video clips ship with baked-in audio of unknown provenance; the
  build strips it entirely (`-an`) and mixes only the narration + procedural
  beds, with an explicit `-map` and a correlation check (target ~1.0) before
  delivery.
