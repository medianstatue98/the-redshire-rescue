#!/usr/bin/env python3
"""Assemble THE REDSHIRE RESCUE final film.
- Normalizes all 9 clips to 1280x720p24, strips native audio (MUX RULE: never
  trust baked-in clip audio), trims/pads each shot to narration end + 0.9s.
- Mixes narration (0.3s lead-in) + per-shot ambience bed, -16 LUFS.
- Burns karaoke ASS captions (DejaVu Sans Bold 44, white -> yellow sweep).
- Appends a 3s title end card. Explicit -map on final mux + audio verification.
"""
import json, os, subprocess, sys
import numpy as np

P = os.path.dirname(os.path.abspath(__file__))
CLIPS = os.path.join(P, "clips")
AUDIO = os.path.join(P, "audio")
TMP = os.path.join(P, "build_tmp")
os.makedirs(TMP, exist_ok=True)

# shot -> clip file stem (set after re-staged shots 4/6 land)
SHOT_CLIP = {
    1: "media-generation-shot1-0-c8b3c465-7d84-4a43-bb36-6045e648593d.mp4",
    2: "media-generation-shot2-0-ea5d6e45-b81e-469e-af98-c4398ca7cc8f.mp4",
    3: "media-generation-shot3-0-11b4086a-19d8-4f39-b6f8-ee31f98f6b2a.mp4",
    4: "media-generation-shot4-restage-0-3536f26a-9cab-4d63-9544-c6658af8471e.mp4",
    5: "media-generation-shot5-0-ca5105eb-c1a6-4e6a-8a51-414efe1e7c0f.mp4",
    6: "media-generation-shot6-restage-0-025ffd4b-014b-48b9-81da-8fdc0cf50314.mp4",
    7: "media-generation-shot7-0-52f8629c-2da0-42e3-9e84-5355147fac1c.mp4",
    8: "media-generation-shot8-0-3e27e533-033f-4f7e-8280-4836d74691bf.mp4",
    9: "media-generation-shot9-0-56be9c15-e193-4670-94b5-d6512fb922c4.mp4",
}
SHOT_BED = {1: ["city_night.wav", "rotors.wav"], 2: ["console.wav"], 3: ["tension.wav", "rotors.wav"],
            4: ["console.wav"], 5: ["strobe.wav", "rotors.wav"],
            6: ["fire.wav", "boom.wav"], 7: ["rotors.wav"], 8: ["sea.wav"],
            9: ["dawn.wav"]}
SHOT_SFX = {3: [("audio/sfx/gunfire_close_seq.wav", 2.2)],
            5: [("audio/sfx/gunfire_distant_seq.wav", 1.4)]}
BED_GAIN = {"rotors.wav": 1.0}
NARR_DELAY = 0.3
TAIL = 0.9
W, H, FPS = 1280, 720, 24

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED:", " ".join(cmd[:10]), "\n", r.stderr[-2000:])
        sys.exit(1)
    return r

def run_bytes(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print("FAILED:", " ".join(cmd[:10]))
        sys.exit(1)
    return r

def probe_dur(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path])
    return float(r.stdout.strip())

timing = json.load(open(os.path.join(AUDIO, "caption_timing.json")))
missing = [s for s, c in SHOT_CLIP.items() if not c]
if missing:
    print("missing clips for shots", missing, "- generate re-staged shots first")
    sys.exit(2)

shot_durs, seg_files = [], []
for i in range(1, 10):
    clip = os.path.join(CLIPS, SHOT_CLIP[i])
    narr = os.path.join(AUDIO, "narr_shot%d.mp3" % i)
    words = timing["shot%d" % i]
    narr_end = (words[-1]["e"] if words else probe_dur(narr)) + NARR_DELAY
    dur = max(10.0, narr_end + TAIL)
    shot_durs.append(dur)

    v = os.path.join(TMP, "v%d.mp4" % i)
    loop_args = ["-stream_loop", "2"] if dur > 10.0 else []
    run(["ffmpeg", "-y", "-v", "error"] + loop_args +
        ["-i", clip, "-an",
         "-vf", "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=%d,format=yuv420p" % (W, H, W, H, FPS),
         "-t", "%.2f" % dur, "-c:v", "libx264", "-preset", "medium", "-crf", "18", v])

    bed_inputs, bed_fc = [], []
    for b, bed in enumerate(SHOT_BED[i]):
        bed_inputs += ["-stream_loop", "2", "-i", os.path.join(AUDIO, "beds", bed)]
        bed_fc.append("[%d:a]volume=%.2f,atrim=0:%.2f[b%d]" % (1 + b, BED_GAIN.get(bed, 0.35), dur, b))
    sfx_inputs, sfx_fc, sfx_labels = [], [], []
    for s_idx, (f, gain) in enumerate(SHOT_SFX.get(i, [])):
        inp_idx = 1 + len(SHOT_BED[i]) + s_idx
        sfx_inputs += ["-i", os.path.join(P, f)]
        sfx_fc.append("[%d:a]volume=%.2f,atrim=0:%.2f[s%d]" % (inp_idx, gain, dur, s_idx))
        sfx_labels.append("[s%d]" % s_idx)
    # cinematic duck: the narration dips under each gunshot so transients punch through
    narr_label, duck_fc, mix_sfx = "[n]", "", sfx_labels
    if sfx_labels:
        duck_fc = (";%sasetnsamples=n=1024:p=0,asplit[skey][smix];" % sfx_labels[0]
                   + "[n][skey]sidechaincompress=threshold=0.08:ratio=4:attack=8:release=250[nd]")
        mix_sfx = ["[smix]"] + sfx_labels[1:]
        narr_label = "[nd]"
    amix = "".join("[b%d]" % b for b in range(len(SHOT_BED[i]))) + "".join(mix_sfx)
    n_inputs = 1 + len(SHOT_BED[i]) + len(mix_sfx)
    a = os.path.join(TMP, "a%d.m4a" % i)
    fc = ("[0:a]adelay=%d|%d,atrim=0:%.2f,volume=1.6[n];" % (int(NARR_DELAY*1000), int(NARR_DELAY*1000), dur)
          + ";".join(bed_fc + sfx_fc) + duck_fc
          + ";%s%samix=inputs=%d:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,atrim=0:%.2f[out]"
          % (narr_label, amix, n_inputs, dur))
    run(["ffmpeg", "-y", "-v", "error", "-i", narr] + bed_inputs + sfx_inputs +
        ["-filter_complex", fc, "-map", "[out]", "-t", "%.2f" % dur,
         "-c:a", "aac", "-b:a", "160k", a])
    seg_files.append((v, a))

with open(os.path.join(TMP, "list.txt"), "w") as fh:
    for v, a in seg_files:
        fh.write("file '%s'\n" % v)
vv = os.path.join(TMP, "video.mp4")
run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
     "-i", os.path.join(TMP, "list.txt"), "-c", "copy", vv])
with open(os.path.join(TMP, "alista.txt"), "w") as fh:
    for v, a in seg_files:
        fh.write("file '%s'\n" % a)
aa = os.path.join(TMP, "audio.m4a")
run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
     "-i", os.path.join(TMP, "alista.txt"), "-c", "copy", aa])

def ass_time(s):
    h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return "%d:%02d:%05.2f" % (int(h), int(m), s)

lines = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1280", "PlayResY: 720",
         "ScaledBorderAndShadow: yes", "",
         "[V4+ Styles]",
         "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
         "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
         "Alignment, MarginL, MarginR, MarginV, Encoding",
         "Style: Narr,DejaVu Sans,44,&H00FFFFFF,&H0000FFFF,&H80000000,&H80000000,"
         "-1,0,0,0,100,100,0,0,1,2,1,2,20,20,60,1", "",
         "[Events]",
         "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
cur = 0.0
for i in range(1, 10):
    words = timing["shot%d" % i]
    chunk, chunks = [], []
    for w in words:
        chunk.append(w)
        if len(chunk) >= 6:
            chunks.append(chunk); chunk = []
    if chunk:
        chunks.append(chunk)
    for ch in chunks:
        s = cur + NARR_DELAY + ch[0]["s"]
        e = cur + NARR_DELAY + ch[-1]["e"] + 0.25
        k = "".join("{\\k%d}%s " % (max(1, int((w["e"]-w["s"])*100)), w["w"]) for w in ch)
        lines.append("Dialogue: 0,%s,%s,Narr,,0,0,0,,%s" % (ass_time(s), ass_time(e), k.strip()))
    cur += shot_durs[i-1]
ass_path = os.path.join(TMP, "film.ass")
open(ass_path, "w").write("\n".join(lines))

ec = os.path.join(TMP, "endcard.mp4")
run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
     "-i", "color=c=black:s=%dx%d:d=3:r=%d" % (W, H, FPS),
     "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:d=3",
     "-vf", "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
     "text='THE REDSHIRE RESCUE':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2-40,"
     "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
     "text='a Snowmoon story - adapted from Chapter 26 by Vitalik Buterin (GPL v3)':"
     "fontcolor=gray:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+40,"
     "format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
     "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "128k",
     "-shortest", ec])

film_nosub = os.path.join(TMP, "film_nosub.mp4")
run(["ffmpeg", "-y", "-v", "error", "-i", vv, "-i", aa,
     "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
     "-shortest", film_nosub])
final = os.path.join(P, "the_redshire_rescue_final.mp4")
run(["ffmpeg", "-y", "-v", "error", "-i", film_nosub, "-i", ec,
     "-filter_complex",
     "[0:v]subtitles='%s':fontsdir='/usr/share/fonts'[v];" % ass_path +
     "[v][1:v]concat=n=2:v=1:a=0[vout];[0:a][1:a]concat=n=2:v=0:a=1[aout]",
     "-map", "[vout]", "-map", "[aout]",
     "-c:v", "libx264", "-preset", "medium", "-crf", "18",
     "-c:a", "aac", "-b:a", "160k", final])

def wav_bytes(path, stream="0:a:0"):
    r = run_bytes(["ffmpeg", "-v", "error", "-i", path, "-map", stream,
                   "-f", "f32le", "-ac", "1", "-ar", "44100", "-"])
    return np.frombuffer(r.stdout, dtype=np.float32)

a_final, a_mix = wav_bytes(final), wav_bytes(aa)
n = min(len(a_final), len(a_mix))
corr = float(np.corrcoef(a_final[:n], a_mix[:n])[0, 1])
peak = float(np.max(np.abs(a_final)))
print("final:", final)
print("duration: %.1fs  audio_corr_vs_mix: %.3f  peak: %.1fdB"
      % (probe_dur(final), corr, 20*np.log10(peak)))
assert corr > 0.9, "audio correlation too low - mux may have kept wrong audio!"
print("OK: explicit -map verified, clean mix confirmed.")
