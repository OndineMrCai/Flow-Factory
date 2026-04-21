#!/usr/bin/env python3
"""
Extract frames from a video at a given FPS and save as PNG images.
Also prints video metadata (resolution, duration, fps).

Usage:
    python extract_frames.py <video_path> [--fps 2] [--out_dir /tmp/frames]

Output:
    Prints metadata to stdout.
    Saves frames as frame_0001.png, frame_0002.png, ... in --out_dir.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def get_video_metadata(video_path: str) -> dict:
    """Use ffprobe to extract video metadata."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    data = json.loads(result.stdout)
    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"), None
    )
    if not video_stream:
        raise ValueError("No video stream found.")

    # Parse FPS (stored as fraction e.g. "24/1" or "30000/1001")
    r_frame_rate = video_stream.get("r_frame_rate", "0/1")
    num, den = r_frame_rate.split("/")
    fps = float(num) / float(den) if float(den) != 0 else 0

    duration = float(video_stream.get("duration", 0) or data.get("format", {}).get("duration", 0))
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    nb_frames = video_stream.get("nb_frames", "unknown")

    return {
        "width": width,
        "height": height,
        "fps": round(fps, 3),
        "duration_sec": round(duration, 3),
        "nb_frames": nb_frames,
        "codec": video_stream.get("codec_name", "unknown"),
    }


def extract_frames(video_path: str, fps: float = 2.0, out_dir: str = None) -> list:
    """
    Extract frames from video at given FPS using ffmpeg.
    Returns list of output image paths.
    """
    if out_dir is None:
        out_dir = tempfile.mkdtemp(prefix="video_frames_")
    os.makedirs(out_dir, exist_ok=True)

    out_pattern = os.path.join(out_dir, "frame_%04d.png")
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", "2",
        out_pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    frames = sorted(Path(out_dir).glob("frame_*.png"))
    return [str(f) for f in frames]


def main():
    parser = argparse.ArgumentParser(description="Extract video frames for evaluation")
    parser.add_argument("video_path", help="Path to input video file")
    parser.add_argument("--fps", type=float, default=2.0, help="Frames per second to extract (default: 2)")
    parser.add_argument("--out_dir", default=None, help="Output directory for frames (default: temp dir)")
    parser.add_argument("--json", action="store_true", help="Output metadata as JSON")
    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"Error: video not found: {args.video_path}", file=sys.stderr)
        sys.exit(1)

    meta = get_video_metadata(args.video_path)
    frames = extract_frames(args.video_path, fps=args.fps, out_dir=args.out_dir)

    meta["n_sampled_frames"] = len(frames)
    meta["sampled_fps"] = args.fps
    meta["frame_paths"] = frames

    if args.json:
        print(json.dumps(meta, indent=2))
    else:
        print(f"Video: {args.video_path}")
        print(f"  Resolution : {meta['width']}x{meta['height']}")
        print(f"  FPS        : {meta['fps']}")
        print(f"  Duration   : {meta['duration_sec']}s")
        print(f"  Codec      : {meta['codec']}")
        print(f"  Frames extracted at {args.fps} FPS: {len(frames)}")
        print(f"  Output dir : {frames[0] if frames else 'N/A'}")
        for i, f in enumerate(frames):
            print(f"    [{i+1:02d}] {os.path.basename(f)}")


if __name__ == "__main__":
    main()
