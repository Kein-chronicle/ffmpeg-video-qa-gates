#!/usr/bin/env python3
"""Subtitle (WebVTT/SRT) lint: lines per cue, chars per line, min display time, reading speed, overlaps.
usage: subtitle_lint.py subs.vtt [--max-lines 2] [--max-chars 20] [--min-dur 0.85] [--max-cps 9]"""
import argparse, re, sys

ap = argparse.ArgumentParser()
ap.add_argument("file"); ap.add_argument("--max-lines", type=int, default=2); ap.add_argument("--max-chars", type=int, default=20)
ap.add_argument("--min-dur", type=float, default=0.85); ap.add_argument("--max-cps", type=float, default=9.0)
a = ap.parse_args()
try:
    txt = open(a.file, encoding="utf-8").read()
except (OSError, UnicodeError) as e:
    print(f"UNMEASURED: cannot read {a.file} as UTF-8 text ({type(e).__name__})"); sys.exit(3)
T = r"(\d+):(\d{2}):(\d{2})[.,](\d{3})|(\d{2}):(\d{2})[.,](\d{3})"
def sec(m):
    g = m.groups()
    return int(g[0])*3600 + int(g[1])*60 + int(g[2]) + int(g[3])/1000 if g[0] is not None else int(g[4])*60 + int(g[5]) + int(g[6])/1000
cues = []
for block in re.split(r"\n\s*\n", txt.replace("\r\n", "\n")):
    lines = block.strip().split("\n")
    for i, l in enumerate(lines):
        m = re.match(rf"\s*({T})\s*-->\s*({T})", l)
        if m:
            ts = list(re.finditer(T, l)); cues.append((sec(ts[0]), sec(ts[1]), [x for x in lines[i+1:] if x.strip()])); break
if not cues:
    print("UNMEASURED/FAIL: no cues parsed - empty subtitles are not a pass"); sys.exit(3)
bad = []; prev_end = -1
for n, (s, e, ls) in enumerate(cues, 1):
    text = "".join(ls)
    if len(ls) > a.max_lines: bad.append(f"cue {n}: {len(ls)} lines (max {a.max_lines})")
    if any(len(x) > a.max_chars for x in ls): bad.append(f"cue {n}: line longer than {a.max_chars} chars")
    if e - s < a.min_dur: bad.append(f"cue {n}: shown {e-s:.2f}s (min {a.min_dur}s)")
    if (e - s) > 0 and len(text) / (e - s) > a.max_cps: bad.append(f"cue {n}: {len(text)/(e-s):.1f} chars/s (max {a.max_cps})")
    if s < prev_end - 1e-6: bad.append(f"cue {n}: overlaps the previous cue")
    prev_end = e
print("\n".join(bad) if bad else f"PASS {len(cues)} cues")
sys.exit(1 if bad else 0)
