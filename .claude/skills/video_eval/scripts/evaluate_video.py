#!/usr/bin/env python3
"""
Evaluate a single video against its text prompt, saving results to JSON.

This is a helper script that prepares the evaluation context for the AI agent:
  1. Extracts frames from the video at 2 FPS
  2. Reads the text prompt
  3. Prints a structured evaluation context that the agent uses to score

Usage (called by the AI agent, not typically run standalone):
    python evaluate_video.py <video_name> \
        --video_dir <dir_containing_mp4_and_generation_text> \
        --out_dir <output_json_directory> \
        [--fps 2]
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def get_video_metadata(video_path):
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr}
    data = json.loads(result.stdout)
    vs = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not vs:
        return {"error": "no video stream"}
    r = vs.get("r_frame_rate", "0/1").split("/")
    fps = float(r[0]) / float(r[1]) if float(r[1]) else 0
    duration = float(vs.get("duration", 0) or data.get("format", {}).get("duration", 0))
    return {
        "width": int(vs.get("width", 0)),
        "height": int(vs.get("height", 0)),
        "fps": round(fps, 2),
        "duration_sec": round(duration, 2),
        "codec": vs.get("codec_name", "unknown"),
    }


def extract_frames(video_path, fps=2.0):
    out_dir = tempfile.mkdtemp(prefix="veval_frames_")
    pattern = os.path.join(out_dir, "frame_%04d.png")
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", f"fps={fps}", "-q:v", "2", pattern]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr}")
    return sorted(str(f) for f in Path(out_dir).glob("frame_*.png"))


def save_result(out_dir, video_name, scores):
    """Save evaluation scores to JSON. Called after the agent determines scores."""
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{video_name}.json")
    with open(out_path, "w") as f:
        json.dump(scores, f, indent=2)
    print(f"Saved: {out_path}")
    return out_path


def prepare_context(video_name, video_dir, fps=2.0):
    """Extract frames and return evaluation context dict."""
    video_path = os.path.join(video_dir, f"{video_name}.mp4")
    prompt_path = os.path.join(video_dir, f"{video_name}.generation_text")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    # Read prompt
    prompt = ""
    if os.path.exists(prompt_path):
        with open(prompt_path) as f:
            prompt = f.read().strip()

    # Get metadata
    meta = get_video_metadata(video_path)

    # Extract frames
    frames = extract_frames(video_path, fps=fps)

    return {
        "video_name": video_name,
        "video_path": video_path,
        "prompt": prompt,
        "metadata": meta,
        "frame_paths": frames,
        "n_frames": len(frames),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video_name", help="Video name without extension")
    parser.add_argument("--video_dir", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--fps", type=float, default=2.0)
    args = parser.parse_args()

    ctx = prepare_context(args.video_name, args.video_dir, args.fps)

    print(f"\n{'='*60}")
    print(f"VIDEO: {ctx['video_name']}")
    print(f"PROMPT: {ctx['prompt'] or '(empty)'}")
    print(f"METADATA: {ctx['metadata']}")
    print(f"FRAMES EXTRACTED ({ctx['n_frames']} at {args.fps} FPS):")
    for i, fp in enumerate(ctx["frame_paths"]):
        print(f"  [{i+1:02d}] {fp}")
    print(f"{'='*60}\n")

    return ctx


if __name__ == "__main__":
    main()
