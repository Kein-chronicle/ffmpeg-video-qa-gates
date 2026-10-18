---
name: video-qa-gates
description: Machine-check rendered videos (shorts, long-form, social clips) with ffmpeg instead of eyeballing - frozen/still stretches, dead air, loudness and true peak, duration/size/audio-presence, subtitle format and reading speed, and a "flat opening" visual-density measure. Use when producing videos with an AI/automated pipeline, when you need objective publish gates, or when a video "passes" review but feels like a slideshow. Exit code 3 = could not measure, never a pass.
---

# video-qa-gates

Judge by measurement. Looking at a video and saying "seems fine" is how 4-second freezes ship.

| Script | Measures | Fails when |
|---|---|---|
| `scripts/qa_video.py` | audio stream present; size; duration (+-tol or max); **longest near-still stretch** (on a 10 fps copy so slow background drift doesn't hide a stall); **dead air** (-50 dB, >=0.3 s); integrated loudness (default -14 LUFS +-1.5); true peak (<= -1 dBFS) | any limit exceeded |
| `scripts/opening_density.py` | fraction of "flat" 8x8 grid cells (brightness stddev < 5) in the first seconds, median and max | opening is mostly empty background; fewer than N usable frames (= unmeasured) |
| `scripts/subtitle_lint.py` | lines per cue, chars per line, minimum display time, chars/second, overlaps | any violation; zero cues parsed = unmeasured |

```bash
python3 scripts/qa_video.py out.mp4 --expect-size 1080x1920 --max-duration 30
python3 scripts/opening_density.py out.mp4 --seconds 3
python3 scripts/subtitle_lint.py out.vtt --max-chars 20
bash tests/run.sh          # builds synthetic clips with ffmpeg and checks every defect is caught for the right reason
```

## Design notes (why it is built this way)

- **Exit 3 is "could not measure".** Missing ffmpeg, unreadable file or <N usable frames must not turn green.
- **Measure a 10 fps downscaled copy for freezes.** Rotating light rays or glow in the background make a frozen
  scene look "alive" at full precision; the cheap copy drops that noise. The limit is `--max-freeze` (default 4 s); a freeze that runs to the end of the clip counts too.
- **Flash/blackout frames are skipped** in density (mean luminance <8 or >247): they say nothing about the scene.
- **Calibrate thresholds from your own good and bad examples, and record them.** Measure a few openings you consider good and a few you consider flat,
  and set the limits between them. The defaults are starting points; your numbers will differ.
- **The test input can be wrong, not the gate.** A `testsrc2` pattern is big colour blocks and measured as "empty";
  a noise video was the honest control. When a gate and its test input disagree, find out which is wrong.
- These are **proxies** for "feels like a real short". Passing does not guarantee it's fun or attractive; a human's
  complaint ("looks like a slide deck", "subtitle duplicates on-screen text") should become a new measurable gate.

## Pair it with

- [`cold-read-comprehension-review`](https://github.com/Kein-chronicle/cold-read-comprehension-review) for "does a viewer understand it" (the thing numbers can't measure).
- [`llm-adaptation-fidelity-check`](https://github.com/Kein-chronicle/llm-adaptation-fidelity-check) when the script is adapted from a source text.
- [`llm-verdict-gate`](https://github.com/Kein-chronicle/llm-verdict-gate) + [`ci-gate-forgery-test`](https://github.com/Kein-chronicle/ci-gate-forgery-test) for the surrounding process.

## Extra gates worth adding (not implemented here)

Screen audit (every on-screen text box: overlaps, platform-UI safe areas, subtitle-band intrusion); allow-list of
on-screen strings (anti-fabrication); text-size floor as % of frame width; cut-rhythm (avg/max cut length);
subtitle-vs-speech character error rate via STT (<= 0.08); emoji ban in rendered DOM; subtitle/on-screen text
duplication ratio. These need your renderer's DOM/timeline, so they can't be generic.

Runtime dependency: install `requirements.txt` with `python3 -m pip install -r requirements.txt`. Pillow must be at least 12.3.0; optional model dependencies listed above are separate.
