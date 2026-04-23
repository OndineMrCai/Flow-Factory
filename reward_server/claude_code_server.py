# Copyright 2026 Jayce-Ping
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# reward_server/claude_code_server.py
"""
Reward server that wraps the Flow-Factory `video_eval` Claude Code skill.

For each (prompt, video) sample:
  1. Write frames to a temp mp4 (cv2.VideoWriter, same codec fallback as
     flow_factory.rewards.videoscore2).
  2. Write the prompt to `{name}.generation_text` next to the mp4.
  3. Invoke `claude -p "/video_eval <videos_dir>" ... --output-format json`.
  4. Read the skill's JSON output from `<videos_dir>/predictions/{name}.json`
     (SKILL.md:219); fall back to extracting a JSON block from claude's stdout.
  5. Combine the three 1-5 scores into a scalar reward using the same formula
     as videoscore2.py:268-273.

Usage:
    python reward_server/claude_code_server.py --port 8000

Dependencies:
    pip install fastapi uvicorn pillow opencv-python numpy
    # plus the `claude` CLI available on PATH
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image

from example_server import RewardServer

logger = logging.getLogger(__name__)


_EXPECTED_KEYS = (
    "visual_quality",
    "text_to_video_alignment",
    "physical_common_sense_consisitency",  # skill uses this misspelling
)


class ClaudeCodeVideoEvalServer(RewardServer):
    """Reward server backed by the /video_eval Claude Code skill."""

    def __init__(
        self,
        claude_bin: str = "claude",
        claude_model: str = "sonnet",
        visual_weight: float = 1.0,
        text_align_weight: float = 1.0,
        physical_weight: float = 1.0,
        store_fps: float = 8.0,
        max_workers: int = 4,
        claude_timeout: float = 600.0,
        work_root: str = "/tmp/flowfactory_reward",
        keep_workdirs: bool = False,
        allowed_tools: str = "Bash Read Glob Grep Write",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.claude_bin = claude_bin
        self.claude_model = claude_model
        self.w_visual = float(visual_weight)
        self.w_text = float(text_align_weight)
        self.w_physical = float(physical_weight)
        self.store_fps = float(store_fps)
        self.max_workers = int(max_workers)
        self.claude_timeout = float(claude_timeout)
        self.work_root = Path(work_root)
        self.keep_workdirs = bool(keep_workdirs)
        self.allowed_tools = allowed_tools

        self.work_root.mkdir(parents=True, exist_ok=True)
        if shutil.which(self.claude_bin) is None:
            logger.warning(
                "claude binary %r not found on PATH; requests will fail",
                self.claude_bin,
            )

        logger.info(
            "ClaudeCodeVideoEvalServer ready (model=%s, weights=v:%.2f t:%.2f p:%.2f, "
            "max_workers=%d, timeout=%.0fs)",
            self.claude_model, self.w_visual, self.w_text, self.w_physical,
            self.max_workers, self.claude_timeout,
        )

    # ------------------------------------------------------------------
    # RewardServer interface
    # ------------------------------------------------------------------

    def compute_reward(
        self,
        prompt: List[str],
        image: Optional[List[Image.Image]] = None,
        video: Optional[List[List[Image.Image]]] = None,
        condition_images: Optional[List[List[Image.Image]]] = None,
        condition_videos: Optional[List[List[List[Image.Image]]]] = None,
    ) -> List[float]:
        if not video:
            raise ValueError("claude_code_server requires `video` input.")
        if len(video) != len(prompt):
            raise ValueError(
                f"prompt/video length mismatch: {len(prompt)} vs {len(video)}"
            )

        work_dir = self.work_root / uuid.uuid4().hex
        work_dir.mkdir(parents=True, exist_ok=True)

        rewards: List[float] = [0.0] * len(prompt)
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {
                    pool.submit(
                        self._score_one, work_dir, i, prompt[i], video[i]
                    ): i
                    for i in range(len(prompt))
                }
                for fut in futures:
                    idx = futures[fut]
                    rewards[idx] = fut.result()
        finally:
            if not self.keep_workdirs:
                shutil.rmtree(work_dir, ignore_errors=True)

        return rewards

    # ------------------------------------------------------------------
    # Per-sample pipeline
    # ------------------------------------------------------------------

    def _score_one(
        self,
        work_dir: Path,
        idx: int,
        prompt: str,
        frames: List[Image.Image],
    ) -> float:
        # Each sample gets its own directory so parallel claude invocations
        # don't step on each other's predictions/ directory and don't
        # redundantly evaluate sibling videos.
        sample_dir = work_dir / f"sample_{idx:04d}"
        sample_dir.mkdir(parents=True, exist_ok=True)
        name = "sample"

        self._write_video(sample_dir / f"{name}.mp4", frames)
        (sample_dir / f"{name}.generation_text").write_text(prompt or "")

        scores = self._run_claude(sample_dir, name)
        return self._score_to_reward(scores)

    def _write_video(self, path: Path, frames: List[Image.Image]) -> None:
        if not frames:
            raise ValueError(f"Empty frame list for {path}")
        w, h = frames[0].size

        fourcc = -1
        for tag in ("mp4v", "avc1", "XVID", "MJPG"):
            code = cv2.VideoWriter_fourcc(*tag)
            if code != -1:
                fourcc = code
                break
        if fourcc == -1:
            raise RuntimeError(
                "No suitable cv2 video codec found. "
                "Install opencv-python with ffmpeg support or system ffmpeg."
            )

        writer = cv2.VideoWriter(str(path), fourcc, self.store_fps, (w, h))
        if not writer.isOpened():
            raise RuntimeError(
                f"cv2.VideoWriter failed to open for {path} at {w}x{h} @ "
                f"{self.store_fps} fps"
            )
        try:
            for frame in frames:
                arr = np.array(frame.convert("RGB"))
                writer.write(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
        finally:
            writer.release()

    def _run_claude(self, videos_dir: Path, name: str) -> Dict[str, Any]:
        cmd = [
            self.claude_bin,
            "-p",
            (
                f"/video_eval {videos_dir}. "
                f"Save the evaluation JSON to {videos_dir}/predictions/{name}.json "
                f"(create the predictions/ directory if it does not exist)."
            ),
            "--dangerously-skip-permissions",
            "--output-format", "json",
            "--model", self.claude_model,
            "--allowedTools", self.allowed_tools,
        ]
        logger.debug("Running: %s", " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.claude_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"claude invocation timed out after {self.claude_timeout}s "
                f"for {name}"
            ) from e

        # Try every plausible on-disk location before falling back to stdout.
        found = self._find_score_file(videos_dir, name)
        if found is not None:
            return found

        parsed = self._extract_json_from_stdout(proc.stdout)
        if parsed is not None:
            return parsed

        parsed = self._extract_from_markdown(proc.stdout)
        if parsed is not None:
            logger.info("Recovered scores for %s via markdown fallback", name)
            return parsed

        snippet = (proc.stdout or "")[-2000:]
        err_snippet = (proc.stderr or "")[-1000:]
        raise RuntimeError(
            f"No JSON output for {name} (claude rc={proc.returncode}). "
            f"Expected {videos_dir}/predictions/{name}.json or a parseable "
            f"JSON/markdown block in stdout. "
            f"stdout tail: {snippet!r} stderr tail: {err_snippet!r}"
        )

    @staticmethod
    def _valid_scores(obj: Any) -> bool:
        return isinstance(obj, dict) and all(k in obj for k in _EXPECTED_KEYS)

    @classmethod
    def _find_score_file(cls, videos_dir: Path, name: str) -> Optional[Dict[str, Any]]:
        """Search likely on-disk paths for the skill's saved JSON."""
        candidates = [
            videos_dir / "predictions" / f"{name}.json",
            videos_dir / f"{name}.json",
            videos_dir.parent / "predictions" / f"{name}.json",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    data = json.loads(path.read_text())
                    if cls._valid_scores(data):
                        return data
                except (json.JSONDecodeError, OSError):
                    pass

        # Recursive glob as a last resort, in case the skill picked a
        # different sibling directory.
        for path in videos_dir.rglob(f"{name}.json"):
            try:
                data = json.loads(path.read_text())
                if cls._valid_scores(data):
                    return data
            except (json.JSONDecodeError, OSError):
                continue
        return None

    @classmethod
    def _extract_from_markdown(cls, stdout: str) -> Optional[Dict[str, Any]]:
        """Recover scores from the markdown-table final-message format."""
        if not stdout:
            return None
        try:
            envelope = json.loads(stdout)
            text = (
                envelope.get("result", "")
                if isinstance(envelope, dict)
                else stdout
            )
        except json.JSONDecodeError:
            text = stdout
        if not isinstance(text, str):
            return None

        label_patterns = {
            "visual_quality": r"visual\s*quality",
            "text_to_video_alignment": r"(?:t2v\s*alignment|text[- ]to[- ]video\s*alignment)",
            "physical_common_sense_consisitency": (
                r"(?:physical[/\s]+common[- ]sense\s*(?:consistency|consisitency)"
                r"|physical\s*consistency)"
            ),
        }
        scores: Dict[str, int] = {}
        for key, label in label_patterns.items():
            m = re.search(
                rf"{label}[^\d\n]{{0,60}}\**\s*([1-5])\s*\**",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if m:
                scores[key] = int(m.group(1))
        return scores if cls._valid_scores(scores) else None

    @staticmethod
    def _extract_json_from_stdout(stdout: str) -> Optional[Dict[str, Any]]:
        if not stdout:
            return None

        # `claude --output-format json` wraps the final assistant text inside
        # {"type":"result","result":"...", ...}. The skill's JSON may be either
        # that whole object, fenced in ```json ... ```, or just a {...} block.
        candidates: List[str] = []
        try:
            envelope = json.loads(stdout)
            if isinstance(envelope, dict) and "result" in envelope:
                candidates.append(envelope["result"])
        except json.JSONDecodeError:
            candidates.append(stdout)
        else:
            candidates.append(stdout)

        for text in candidates:
            if not isinstance(text, str):
                continue
            for block in _iter_json_blocks(text):
                try:
                    obj = json.loads(block)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and all(k in obj for k in _EXPECTED_KEYS):
                    return obj
        return None

    def _score_to_reward(self, scores: Dict[str, Any]) -> float:
        try:
            v = float(scores["visual_quality"])
            t = float(scores["text_to_video_alignment"])
            p = float(scores["physical_common_sense_consisitency"])
        except (KeyError, TypeError, ValueError) as e:
            raise RuntimeError(f"Invalid score JSON: {scores!r}") from e

        total_w = self.w_visual + self.w_text + self.w_physical
        if total_w <= 0:
            raise ValueError("Sum of weights must be > 0")
        return (self.w_visual * v + self.w_text * t + self.w_physical * p) / (
            total_w * 5.0
        )


# ----------------------------------------------------------------------
# JSON block scanner
# ----------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _iter_json_blocks(text: str):
    """Yield candidate JSON substrings from `text`, fenced blocks first."""
    for m in _FENCE_RE.finditer(text):
        yield m.group(1)

    # Brace-balanced scan for bare {...} objects.
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    yield text[start:i + 1]
                    start = -1


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Claude Code video_eval reward server")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--claude-bin", default="claude")
    p.add_argument("--claude-model", default="sonnet")
    p.add_argument("--visual-weight", type=float, default=1.0)
    p.add_argument("--text-align-weight", type=float, default=1.0)
    p.add_argument("--physical-weight", type=float, default=1.0)
    p.add_argument("--store-fps", type=float, default=8.0)
    p.add_argument("--max-workers", type=int, default=4)
    p.add_argument("--claude-timeout", type=float, default=600.0)
    p.add_argument("--work-root", default="/tmp/flowfactory_reward")
    p.add_argument("--keep-workdirs", action="store_true")
    p.add_argument("--allowed-tools", default="Bash Read Glob Grep Write")
    p.add_argument("--log-level", default="INFO")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    server = ClaudeCodeVideoEvalServer(
        host=args.host,
        port=args.port,
        claude_bin=args.claude_bin,
        claude_model=args.claude_model,
        visual_weight=args.visual_weight,
        text_align_weight=args.text_align_weight,
        physical_weight=args.physical_weight,
        store_fps=args.store_fps,
        max_workers=args.max_workers,
        claude_timeout=args.claude_timeout,
        work_root=args.work_root,
        keep_workdirs=args.keep_workdirs,
        allowed_tools=args.allowed_tools,
    )
    server.run()
