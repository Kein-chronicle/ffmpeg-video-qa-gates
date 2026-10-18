#!/usr/bin/env python3
"""video-qa-gates: measure a rendered video. Judges by measurement, not by looking.
exit 0 pass | 1 fail | 3 could not measure (never a pass)
usage: qa_video.py video.mp4 [--max-freeze 4.0] [--target-lufs -14 --lufs-tol 1.5 --max-true-peak -1]
                              [--expect-duration S --duration-tol 0.3] [--expect-size WxH] [--max-duration S]"""
import argparse, json, re, shutil, subprocess, sys, tempfile, os


def run(args):
    return subprocess.run(args, capture_output=True, text=True)


def probe(path):
    p = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
             "-of", "json", path])
    return json.loads(p.stdout or "{}") if p.returncode == 0 else None


def longest_freeze(path, total, min_d=0.5):
    """Freeze detection on a 10fps copy (cheap, and ignores sub-pixel background drift).
    freezedetect only reports a duration when a freeze ENDS, so a freeze that runs to the end of the clip is closed at `total`.
    Returns None when the video could not be decoded (the caller reports UNMEASURED, never a pass)."""
    tmp = tempfile.mkdtemp(); small = os.path.join(tmp, "s.mp4")
    try:
        r1 = run(["ffmpeg", "-y", "-i", path, "-vf", "fps=10,scale=320:-2", "-an", small])
        if r1.returncode != 0 or not os.path.isfile(small): return None
        p = run(["ffmpeg", "-i", small, "-vf", f"freezedetect=n=0.003:d={min_d}", "-f", "null", "-"])
        if p.returncode != 0: return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    durs = [float(x) for x in re.findall(r"freeze_duration: ([0-9.]+)", p.stderr)]
    starts = [float(x) for x in re.findall(r"freeze_start: ([0-9.]+)", p.stderr)]
    ends = re.findall(r"freeze_end: ([0-9.]+)", p.stderr)
    if len(starts) > len(ends): durs.append(max(0.0, total - starts[-1]))        # the last freeze never ended
    return max(durs) if durs else 0.0


def silent_segments(path, db=-50, d=0.3):
    p = run(["ffmpeg", "-i", path, "-af", f"silencedetect=noise={db}dB:d={d}", "-vn", "-f", "null", "-"])
    return len(re.findall(r"silence_start", p.stderr)) if p.returncode == 0 else None


def loudness(path):
    p = run(["ffmpeg", "-i", path, "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"])
    tail = p.stderr[p.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[0-9.]+) LUFS", tail); tp = re.search(r"Peak:\s+(-?[0-9.]+) dBFS", tail)
    return (float(i.group(1)) if i else None, float(tp.group(1)) if tp else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--max-freeze", type=float, default=4.0)
    ap.add_argument("--target-lufs", type=float, default=-14.0)
    ap.add_argument("--lufs-tol", type=float, default=1.5)
    ap.add_argument("--max-true-peak", type=float, default=-1.0)
    ap.add_argument("--expect-duration", type=float)
    ap.add_argument("--duration-tol", type=float, default=0.3)
    ap.add_argument("--expect-size")
    ap.add_argument("--max-duration", type=float)
    a = ap.parse_args()
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("UNMEASURED: ffmpeg/ffprobe not installed"); return 3
    if not os.path.isfile(a.video):
        print(f"UNMEASURED: {a.video} not found"); return 3
    info = probe(a.video)
    if not info or not info.get("streams"):
        print("UNMEASURED: ffprobe could not read the file"); return 3
    kinds = {s["codec_type"] for s in info["streams"]}
    vs = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    try: dur = float(info["format"]["duration"])
    except (KeyError, ValueError, TypeError): print("UNMEASURED: the file has no readable duration"); return 3
    if vs is None: print("UNMEASURED: no video stream (audio-only files are not videos)"); return 3
    fails = []; rows = []

    def check(name, ok, detail):
        rows.append(("PASS" if ok else "FAIL", name, detail))
        if not ok: fails.append(name)

    check("has-audio", "audio" in kinds, "audio stream present" if "audio" in kinds else "NO audio stream")
    if a.expect_size:
        check("size", f"{vs['width']}x{vs['height']}" == a.expect_size, f"{vs['width']}x{vs['height']} want {a.expect_size}")
    if a.expect_duration is not None:
        check("duration", abs(dur - a.expect_duration) <= a.duration_tol, f"{dur:.2f}s want {a.expect_duration}+-{a.duration_tol}")
    if a.max_duration is not None:
        check("max-duration", dur <= a.max_duration, f"{dur:.2f}s <= {a.max_duration}")
    fz = longest_freeze(a.video, dur)
    if fz is None: print("UNMEASURED: ffmpeg could not decode the video for freeze detection"); return 3
    check("no-long-freeze", fz <= a.max_freeze, f"longest near-still stretch {fz:.2f}s (limit {a.max_freeze}s)")
    if "audio" in kinds:
        n = silent_segments(a.video)
        if n is None: print("UNMEASURED: ffmpeg could not decode the audio for silence detection"); return 3
        check("no-dead-air", n == 0, f"{n} silent segment(s) (>=0.3s below -50 dB)")
        lufs, tp = loudness(a.video)
        if lufs is None:
            print("UNMEASURED: loudness could not be computed"); return 3
        check("loudness", abs(lufs - a.target_lufs) <= a.lufs_tol, f"{lufs:.1f} LUFS (target {a.target_lufs}+-{a.lufs_tol})")
        if tp is not None:
            check("true-peak", tp <= a.max_true_peak, f"{tp:.1f} dBFS (limit {a.max_true_peak})")
    for st, n, d in rows:
        print(f"[{st}] {n}: {d}")
    print("FAIL: " + ", ".join(fails) if fails else "all measured checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
