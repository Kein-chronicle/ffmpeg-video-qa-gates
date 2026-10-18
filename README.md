# ffmpeg-video-qa-gates

**Machine QA for short videos with ffmpeg: frozen frames, dead air, loudness, true peak, size, a busy opening, and readable subtitle timing.**

[![test](https://github.com/Kein-chronicle/ffmpeg-video-qa-gates/actions/workflows/test.yml/badge.svg)](https://github.com/Kein-chronicle/ffmpeg-video-qa-gates/actions/workflows/test.yml) ![license](https://img.shields.io/badge/license-MIT-blue.svg)

## Why

AI-generated videos fail in ways nobody looks for until upload: a six-second still frame, a silent middle, audio at the wrong level. These gates measure it and exit non-zero.

## Install

**As a Claude Code skill** (Claude uses it when the task matches the skill description):

```sh
git clone https://github.com/Kein-chronicle/ffmpeg-video-qa-gates.git ~/.claude/skills/video-qa-gates
```

For a single project, clone into `<project>/.claude/skills/video-qa-gates` instead, then start a new Claude Code session.

**As plain scripts:**

```sh
git clone https://github.com/Kein-chronicle/ffmpeg-video-qa-gates.git
cd ffmpeg-video-qa-gates
```

**Requires:** Python 3.10+, ffmpeg, Pillow.

Use the security-patched Pillow runtime:

```sh
python3 -m pip install -r requirements.txt
```

## Quick start

Generate test clips and run the gates:

```console
$ bash examples/demo.sh
# Test clips are generated with ffmpeg (a real clip, one with a 6 s frozen picture, one with no audio track)
$ python3 scripts/qa_video.py .demo-tmp/good.mp4
[PASS] has-audio: audio stream present
[PASS] no-long-freeze: longest near-still stretch 0.00s (limit 4.0s)
[PASS] no-dead-air: 0 silent segment(s) (>=0.3s below -50 dB)
[PASS] loudness: -13.8 LUFS (target -14.0+-1.5)
[PASS] true-peak: -9.0 dBFS (limit -1.0)
all measured checks pass
[exit 0]

$ python3 scripts/qa_video.py .demo-tmp/frozen.mp4
[PASS] has-audio: audio stream present
[FAIL] no-long-freeze: longest near-still stretch 6.00s (limit 4.0s)
[PASS] no-dead-air: 0 silent segment(s) (>=0.3s below -50 dB)
[PASS] loudness: -13.8 LUFS (target -14.0+-1.5)
[PASS] true-peak: -9.0 dBFS (limit -1.0)
FAIL: no-long-freeze
[exit 1]

$ python3 scripts/qa_video.py .demo-tmp/no-audio.mp4
[FAIL] has-audio: NO audio stream
[PASS] no-long-freeze: longest near-still stretch 0.00s (limit 4.0s)
FAIL: has-audio
[exit 1]

# Wrong size for a vertical short, and a missing file is unmeasured (3)
$ python3 scripts/qa_video.py .demo-tmp/good.mp4 --expect-size 1080x1920
[PASS] has-audio: audio stream present
[FAIL] size: 640x360 want 1080x1920
[PASS] no-long-freeze: longest near-still stretch 0.00s (limit 4.0s)
[PASS] no-dead-air: 0 silent segment(s) (>=0.3s below -50 dB)
[PASS] loudness: -13.8 LUFS (target -14.0+-1.5)
[PASS] true-peak: -9.0 dBFS (limit -1.0)
FAIL: size
[exit 1]

$ python3 scripts/qa_video.py .demo-tmp/nope.mp4
UNMEASURED: .demo-tmp/nope.mp4 not found
[exit 3]

# Subtitle timing: a cue that is on screen too briefly to read
$ python3 scripts/subtitle_lint.py .demo-tmp/subs.vtt
cue 2: line longer than 20 chars
cue 2: shown 0.30s (min 0.85s)
cue 2: 156.7 chars/s (max 9.0)
[exit 1]
```

The output above is real: it is produced by the files in `examples/`.

## Use it on your own files

```sh
python3 scripts/qa_video.py out.mp4 --expect-size 1080x1920 --max-duration 60
python3 scripts/opening_density.py out.mp4
python3 scripts/subtitle_lint.py captions.vtt
```

Sample inputs for every file format are in `examples/` and `tests/`; the details are in [SKILL.md](SKILL.md).

## What it checks

- `qa_video.py`: has-audio, longest still stretch, silent segments, integrated loudness against a target, true peak, expected size and duration. Exit `3` if the file is missing.
- `opening_density.py`: is the first seconds visually busy or a flat card?
- `subtitle_lint.py`: lines per cue, characters per line, display time, characters per second (VTT).

## Limits

- Needs `ffmpeg` and `ffprobe`.
- Thresholds suit short-form vertical video; tune them for yours.
- It measures, it does not judge whether the video is good.

## Related projects

These solve neighbouring problems; use them when they fit better.

- **ffmpeg `loudnorm`, ffmpeg-normalize**: fix loudness; this checks and reports it

## More from the same collection

Small, tested tools that grew out of running AI agents and game/app pipelines for months:

- [**canvas-render-pixel-gate**](https://github.com/Kein-chronicle/canvas-render-pixel-gate): Detect grey-box screenshots: measure unique colors and flat-fill share of a rendered game canvas, and refuse to pass what it could not measure.
- [**web-game-asset-reality-check**](https://github.com/Kein-chronicle/web-game-asset-reality-check): Catch web-game bugs the type checker can't: fonts that are declared but not shipped, runtime CDN dependencies, and page errors from headless Chromium.
- [**cold-read-comprehension-review**](https://github.com/Kein-chronicle/cold-read-comprehension-review): Grade whether a video or page communicates, using independent cold readers checked against the author's truth file, and flag stale judgements.

## Development

```sh
bash tests/run.sh
```

The tests include inputs that are supposed to be rejected, so a green run also shows the checks can fail. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).

If this saved you a debugging session, a star helps other people find it. Bug reports and failing test cases are even better.

<sub>Keywords: ffmpeg, video, qa, loudness, subtitles, shorts, automation, claude-skills</sub>
