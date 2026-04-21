---
name: video_eval
description: >
  Evaluate text-to-video generation quality on three dimensions: visual quality,
  text-to-video alignment, and physical/common-sense consistency. Produces integer
  scores 1–5 per dimension, with reasoning, saved as JSON. Calibrated against
  human annotator labels to minimize bias.

usage: /video_eval <path_to_video_label_directory>
example: /video_eval /data/trainset/video
---

# Video Evaluation Skill

## Overview

This skill evaluates AI-generated videos against their text prompts across three dimensions.
It is calibrated against human annotator ground truth — follow the workflow and rubrics closely
to achieve alignment with human judgements.

**Key calibration facts from 50-video human-annotated dataset:**

| Dimension | Exact Match | Within-±1 | MAE | Model Bias |
|-----------|-------------|-----------|-----|------------|
| Visual Quality | 30% | 86% | 0.84 | **+0.24 (overestimates)** |
| T2V Alignment | 42% | 94% | 0.66 | ≈0 (well-calibrated) |
| Physical Consistency | 28% | 60% | 1.26 | **+0.82 (overestimates)** |

**The biggest failure mode is overestimating Physical Consistency** — model evaluators
default to "the overall scene makes physical sense" while human annotators penalize
frame-level AI artifacts aggressively (body deformations, hand anomalies, disappearing objects).

---

## Invocation

When the user runs `/video_eval <directory>`, perform the following workflow for each
`{video_name}.mp4` / `{video_name}.generation_text` pair in the directory.

---

## Step-by-Step Evaluation Workflow

### Step 1: Extract Video Frames

Use `ffmpeg` to extract frames at **2 FPS**:

```bash
ffmpeg -i {video_name}.mp4 -vf fps=2 /tmp/frames/frame_%04d.png
```

Or use the helper script:

```bash
python scripts/extract_frames.py {video_dir}/{video_name}.mp4 --fps 2 --out_dir /tmp/frames/
```

Also capture video metadata (resolution, FPS, duration) using ffprobe:

```bash
ffprobe -v quiet -print_format json -show_streams -show_format {video_path}
```

### Step 2: Read the Text Prompt

```
cat {video_dir}/{video_name}.generation_text
```

Note: If the file is empty, record `prompt: "(empty)"` and score T2V alignment leniently.

### Step 3: Inspect All Frames

Read every extracted frame image carefully. For each frame, note:
- Resolution and overall clarity
- Body part integrity (face, hands, arms, legs)
- Object positions and quantities
- Consistency with previous frames

### Step 4: Score Each Dimension

Apply the rubrics in `references/` strictly. See the **Critical Calibration Rules** below.

#### 4a. Visual Quality — `references/visual_quality_rubric.md`

Focus on: resolution, body/face deformation artifacts, watermarks, temporal consistency.

**Quick anchors:**
- 5: Cinematic, 720p+, smooth, no artifacts
- 4: Good quality, minor hand/face blur acceptable
- 3: Noticeable issues (blurry face, choppy), scene still recognizable
- 2: Severe deformation or very low res (≤256px) or watermark
- 1: Subject unrecognizable, extreme artifacts

#### 4b. T2V Alignment — `references/text_to_video_alignment_rubric.md`

Check ALL elements: characters, clothing, actions (each step), background, camera movement, art style.

**Quick anchors:**
- 5: Every element present and correct
- 4: Almost all correct, one small miss
- 3: Core subject present but multiple details missing
- 2: Major elements absent or wrong
- 1: No meaningful alignment

#### 4c. Physical Consistency — `references/physical_consistency_rubric.md`

⚠️ **THIS IS THE HARDEST DIMENSION — read every frame carefully.**

Focus on: finger count, hand anatomy, body part deformation between frames, object stability, motion plausibility.

**Quick anchors:**
- 5: Zero violations across all frames
- 4: One or two very minor issues (brief finger blur)
- 3: Noticeable but moderate issues
- 2: Clear violations (food items moving, body parts changing shape, object passing through another)
- 1: Severe pervasive violations (faces morphing, bodies overlapping, limbs appearing/disappearing)

### Step 5: Output JSON

Save to `{output_dir}/{video_name}.json`:

```json
{
  "visual_quality": <1-5>,
  "text_to_video_alignment": <1-5>,
  "physical_common_sense_consisitency": <1-5>,
  "visual_quality_reasoning": "Brief explanation citing specific observations (resolution, artifacts, etc.)",
  "text_to_video_alignment_reasoning": "List which prompt elements are present/absent",
  "physical_common_sense_consisitency_reasoning": "Describe specific violations or confirm none found"
}
```

---

## Critical Calibration Rules

These rules are derived from error analysis on 50 human-annotated videos.
Violating them is the primary source of score deviation from human labels.

### Visual Quality
1. **Watermarks (Shutterstock, POND5, etc.) → score ≤ 2**, regardless of other quality.
2. **Resolution ≤ 256×256 → score ≤ 2**, even if content is visible.
3. **Persistent face/body deformation across frames → deduct 1–2 points** from what the overall scene might suggest.
4. **Score 5 is rare** — requires 720p+, smooth motion, zero artifacts.
5. **Pervasive heavy motion blur throughout → score 1–2**, not 3. If character details are impossible to perceive due to persistent blur, treat it the same as extreme pixelation.
6. **Static/2D/vector animation: do NOT deduct for lack of motion.** A clean still illustration can score 4. Judge rendering clarity only.
7. **Temporal face instability (hat color changes, beard density shifts, face proportions vary across frames) → score ≤ 2**, even if individual frames look sharp.
8. **Blank/featureless face in animated characters → score 1**, same as subject unrecognizable.

### T2V Alignment
1. **Check camera movements** (pan/tilt/crane) — if specified in prompt and absent in video, deduct 1 score level.
2. **All sequential actions must be shown** — partial execution caps at score 3.
3. **Approximate backgrounds ≠ correct** (generic green field ≠ coffee plantation).
4. **Empty prompt file** → note it, score leniently based on plausibility (likely 3–4).
5. **Descriptive/scene prompts need no motion.** If the prompt describes a visual setting (not an action), a static video with all elements present = score 4–5.
6. **Two peripheral misses ≠ score 2.** If the core subject/setting is correct but two details (e.g., background element + camera movement) are missing, that is score 3. Score 2 requires major elements absent.
7. **Do not over-require exact action confirmation.** If an action is ambiguous due to viewpoint/resolution but the core activity is plausibly present, give credit. Only mark absent when clearly not shown.

### Physical Consistency
1. **Always inspect hands and faces** — AI videos routinely have wrong finger counts, morphing faces.
2. **Frame-by-frame comparison matters** — objects that change position/quantity between frames in a static scene = score 2.
3. **Do not give 4–5 just because the overall scene "makes sense"** — inspect individual body parts.
4. **Fantasy/stylized content** — evaluate consistency within the established world rules, not against strict realism.
5. **Very short clips (≤3 frames sampled)** — be conservative; only flag clearly visible violations.
6. **Blur ≠ deformation.** A blurry face is a VQ issue, not a PHY violation. Only penalize PHY when body parts demonstrably change shape/position between frames. If you cannot see body parts clearly due to blur, do not assume physical violations.
7. **Motion blur on hands during fast movements ≠ wrong finger count.** Only check finger anatomy in near-static hand positions where fingers are clearly visible.

---

## Parallel Evaluation (Batch Mode)

When evaluating multiple videos, launch parallel subagents — one per batch of 5 videos:

```
For each batch of 5 videos:
  → Launch Agent with model=sonnet, evaluate sequentially within batch
  → Save JSON outputs to output_dir/
```

After all agents complete, run accuracy analysis:

```bash
python scripts/compute_accuracy.py \
  --pred_dir <predictions_dir> \
  --label_dir <gt_labels_dir> \
  --output accuracy_report.json
```

---

## File Structure Reference

```
video_eval_skill/
├── SKILL.md                          ← This file (Claude Code skill)
├── references/
│   ├── visual_quality_rubric.md      ← Detailed scoring guide for VQ
│   ├── text_to_video_alignment_rubric.md  ← Detailed scoring guide for T2V
│   └── physical_consistency_rubric.md     ← Detailed scoring guide for PHY
└── scripts/
    ├── extract_frames.py             ← Extract frames + metadata from video
    ├── evaluate_video.py             ← Prepare evaluation context for single video
    └── compute_accuracy.py           ← Compare predictions vs GT labels
```

---

## Example Session

```
User: /video_eval /data/trainset/video

→ List all .mp4 files in directory
→ For each video_name:
    1. ffmpeg extract frames at 2 FPS
    2. Read generation_text prompt
    3. Inspect all frames
    4. Score VQ / T2V / PHY per rubrics
    5. Save {video_name}.json to predictions/
→ Report completion summary
```
