#!/usr/bin/env bash
# Builds synthetic clips with ffmpeg and checks every gate rejects the forged defect.
set -u; here="$(cd "$(dirname "$0")" && pwd)"; s="$here/../scripts"; d="$(mktemp -d)"; bad=0
F="-hide_banner -loglevel error -y"
# good: moving noise-rich picture + steady tone at about -14 LUFS
ffmpeg $F -f lavfi -i "testsrc2=s=640x360:r=30:d=8" -f lavfi -i "sine=f=440:d=8" -filter:a "volume=2.5" -shortest -pix_fmt yuv420p "$d/good.mp4"
# freeze: first 6s a single colour, then motion
ffmpeg $F -f lavfi -i "color=c=blue:s=640x360:r=30:d=6" -f lavfi -i "testsrc2=s=640x360:r=30:d=2" -f lavfi -i "sine=f=440:d=8" -filter_complex "[0][1]concat=n=2:v=1:a=0[v]" -map "[v]" -map 2:a -filter:a "volume=2.5" -pix_fmt yuv420p "$d/freeze.mp4"
# silent: good picture, 3s of silence in the middle
ffmpeg $F -f lavfi -i "testsrc2=s=640x360:r=30:d=8" -f lavfi -i "sine=f=440:d=8" -filter:a "volume=2.5,volume=enable='between(t,3,6)':volume=0" -shortest -pix_fmt yuv420p "$d/silent.mp4"
# loud: way over target
ffmpeg $F -f lavfi -i "testsrc2=s=640x360:r=30:d=8" -f lavfi -i "sine=f=440:d=8" -filter:a "volume=7" -shortest -pix_fmt yuv420p "$d/loud.mp4"
# noaudio
ffmpeg $F -f lavfi -i "testsrc2=s=640x360:r=30:d=8" -an -pix_fmt yuv420p "$d/noaudio.mp4"
# flat opening vs busy opening (noise)
ffmpeg $F -f lavfi -i "color=c=gray:s=640x360:r=30:d=4" -f lavfi -i "sine=f=440:d=4" -shortest -pix_fmt yuv420p "$d/flat.mp4"
ffmpeg $F -f lavfi -i "nullsrc=s=640x360:r=30:d=4,geq=random(1)*255:128:128" -f lavfi -i "sine=f=440:d=4" -shortest -pix_fmt yuv420p "$d/busy.mp4"

# expect <name> <exit> [reason-regex] -- cmd...   (reason must appear on a FAIL line: it must fail for the RIGHT reason)
expect() { name="$1"; want="$2"; shift 2; reason=""; if [ "$1" != "--" ] && [ "${1#--}" = "$1" ] && ! command -v "$1" >/dev/null 2>&1; then reason="$1"; shift; fi
  out="$("$@" 2>&1)"; got=$?
  if [ "$got" != "$want" ]; then echo "FAIL $name: want $want got $got"; echo "$out" | sed 's/^/     /'; bad=1; return; fi
  if [ -n "$reason" ] && ! echo "$out" | grep -E "FAIL.*($reason)|UNMEASURED.*($reason)" >/dev/null; then echo "FAIL $name: failed, but not for '$reason'"; echo "$out" | sed 's/^/     /'; bad=1; return; fi
  echo "ok   $name (exit $got${reason:+, reason: $reason})"; }
expect "good video passes " 0 python3 "$s/qa_video.py" "$d/good.mp4"
expect "6s freeze is caught"          1 no-long-freeze python3 "$s/qa_video.py" "$d/freeze.mp4"
expect "dead air is caught"           1 no-dead-air python3 "$s/qa_video.py" "$d/silent.mp4"
expect "too loud is caught"           1 loudness python3 "$s/qa_video.py" "$d/loud.mp4"
expect "missing audio is caught"      1 has-audio python3 "$s/qa_video.py" "$d/noaudio.mp4"
# freeze that runs to the END of the clip (freezedetect only reports a freeze when it ends)
ffmpeg $F -f lavfi -i "testsrc2=s=640x360:r=30:d=2" -f lavfi -i "color=c=blue:s=640x360:r=30:d=8" -f lavfi -i "sine=f=440:d=10" -filter_complex "[0][1]concat=n=2:v=1:a=0[v]" -map "[v]" -map 2:a -filter:a "volume=2.5" -pix_fmt yuv420p "$d/tailfreeze.mp4"
expect "a freeze that never ends is caught" 1 no-long-freeze python3 "$s/qa_video.py" "$d/tailfreeze.mp4"
ffmpeg $F -f lavfi -i "sine=f=440:d=3" "$d/audio-only.wav"
expect "audio-only file is unmeasured (3), not a crash" 3 python3 "$s/qa_video.py" "$d/audio-only.wav"
printf 'not a video at all' > "$d/garbage.mp4"
expect "undecodable file is unmeasured (3)" 3 python3 "$s/qa_video.py" "$d/garbage.mp4"
expect "missing file => unmeasured"   3 python3 "$s/qa_video.py" "$d/nope.mp4"
expect "size mismatch is caught"      1 "size:" python3 "$s/qa_video.py" "$d/good.mp4" --expect-size 1080x1920
expect "flat opening fails"           1 python3 "$s/opening_density.py" "$d/flat.mp4" --seconds 4 --min-frames 4
expect "busy opening passes"          0 python3 "$s/opening_density.py" "$d/busy.mp4" --seconds 4 --min-frames 4

cat > "$d/ok.vtt" <<'V'
WEBVTT

00:00:00.000 --> 00:00:02.000
Short and clear

00:00:02.100 --> 00:00:04.000
Second cue here
V
cat > "$d/bad.vtt" <<'V'
WEBVTT

00:00:00.000 --> 00:00:00.400
This line is far too long to read in a flash

00:00:00.300 --> 00:00:02.000
a
b
c
V
: > "$d/empty.vtt"
expect "good subtitles pass"          0 python3 "$s/subtitle_lint.py" "$d/ok.vtt"
expect "bad subtitles fail"           1 python3 "$s/subtitle_lint.py" "$d/bad.vtt"
expect "empty subtitles are not a pass" 3 python3 "$s/subtitle_lint.py" "$d/empty.vtt"
rm -rf "$d"; exit $bad
