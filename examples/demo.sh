#!/usr/bin/env bash
cd "$(dirname "$0")/.."
run() { printf '$ %s\n' "$*"; "$@"; printf '[exit %s]\n\n' "$?"; }
tmp=.demo-tmp; rm -rf "$tmp"; mkdir "$tmp"; trap 'rm -rf "$tmp"' EXIT
F="-hide_banner -loglevel error -y"
ffmpeg $F -f lavfi -i "testsrc2=s=640x360:r=30:d=8" -f lavfi -i "sine=f=440:d=8" -filter:a "volume=2.5" -shortest -pix_fmt yuv420p "$tmp/good.mp4"
ffmpeg $F -f lavfi -i "color=c=blue:s=640x360:r=30:d=6" -f lavfi -i "testsrc2=s=640x360:r=30:d=2" -f lavfi -i "sine=f=440:d=8" -filter_complex "[0][1]concat=n=2:v=1:a=0[v]" -map "[v]" -map 2:a -filter:a "volume=2.5" -pix_fmt yuv420p "$tmp/frozen.mp4"
ffmpeg $F -f lavfi -i "testsrc2=s=640x360:r=30:d=8" -an -pix_fmt yuv420p "$tmp/no-audio.mp4"
printf 'WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nShort and clear\n\n00:00:02.000 --> 00:00:02.300\nThis cue flashes by far too fast to read at all\n' > "$tmp/subs.vtt"
echo "# Test clips are generated with ffmpeg (a real clip, one with a 6 s frozen picture, one with no audio track)"
run python3 scripts/qa_video.py "$tmp/good.mp4"
run python3 scripts/qa_video.py "$tmp/frozen.mp4"
run python3 scripts/qa_video.py "$tmp/no-audio.mp4"
echo "# Wrong size for a vertical short, and a missing file is unmeasured (3)"
run python3 scripts/qa_video.py "$tmp/good.mp4" --expect-size 1080x1920
run python3 scripts/qa_video.py "$tmp/nope.mp4"
echo "# Subtitle timing: a cue that is on screen too briefly to read"
run python3 scripts/subtitle_lint.py "$tmp/subs.vtt"
