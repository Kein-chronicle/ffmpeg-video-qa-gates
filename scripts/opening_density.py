#!/usr/bin/env python3
"""Opening visual-density gate: fraction of 'flat' 8x8 cells per sampled frame.
A flat cell has brightness stddev < 5. Blank/flash frames are skipped. 0 frames measured => fail (exit 3).
usage: opening_density.py video.mp4 [--seconds 3.0] [--median-max 0.70] [--max-max 0.85] [--min-frames 6]"""
import argparse, os, shutil, statistics, subprocess, sys, tempfile
try:
    from PIL import Image, ImageStat
except ImportError:
    print("UNMEASURED: Pillow missing"); sys.exit(3)

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--seconds", type=float, default=3.0)
ap.add_argument("--median-max", type=float, default=0.70); ap.add_argument("--max-max", type=float, default=0.85)
ap.add_argument("--min-frames", type=int, default=6)
a = ap.parse_args()
if not os.path.isfile(a.video) or not shutil.which("ffmpeg"):
    print("UNMEASURED: video or ffmpeg missing"); sys.exit(3)
tmp = tempfile.mkdtemp()
subprocess.run(["ffmpeg", "-y", "-ss", "0.3", "-t", str(a.seconds - 0.4), "-i", a.video,
                "-vf", "fps=2,scale=480:270,format=gray", os.path.join(tmp, "f%03d.png")], capture_output=True)
ratios = []
for f in sorted(os.listdir(tmp)):
    im = Image.open(os.path.join(tmp, f)).convert("L")
    mean = ImageStat.Stat(im).mean[0]
    if mean < 8 or mean > 247:                       # flash / blackout frame: not informative
        continue
    w, h = im.size; cw, ch = w // 8, h // 8; flat = 0
    for gy in range(8):
        for gx in range(8):
            cell = im.crop((gx * cw, gy * ch, (gx + 1) * cw, (gy + 1) * ch))
            if ImageStat.Stat(cell).stddev[0] < 5: flat += 1
    ratios.append(flat / 64)
shutil.rmtree(tmp, ignore_errors=True)
if len(ratios) < a.min_frames:
    print(f"UNMEASURED/FAIL: only {len(ratios)} usable frames (need {a.min_frames}) - measuring nothing is not a pass"); sys.exit(3)
med, mx = statistics.median(ratios), max(ratios)
ok = med <= a.median_max and mx <= a.max_max
print(f"{'PASS' if ok else 'FAIL'} opening density: median flat-cell ratio {med:.2f} (<= {a.median_max}), max {mx:.2f} (<= {a.max_max}), frames {len(ratios)}")
sys.exit(0 if ok else 1)
