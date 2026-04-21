# Visual Quality Scoring Rubric

## Definition
Visual quality covers the video's optical and perceptual properties: resolution, clarity, smoothness, temporal consistency (brightness/contrast stability), body/face deformation artifacts, and any factor that degrades the watching experience.

## Calibration Insights (from human annotation analysis)
Model evaluators make errors in both directions on visual quality:
- **Overestimation**: Pervasive motion blur dismissed as "acceptable", temporal face instability overlooked, blank animated faces not penalized enough
- **Underestimation**: Static animation/2D videos penalized for lack of motion (wrong — motion is not a VQ criterion); clean cartoon art with low resolution underscored

**Two additional rules calibrated from error analysis:**
1. **Pervasive heavy motion blur = score 1–2**, not 3. If character details are impossible to perceive due to persistent blur across most frames, that is as bad as low resolution.
2. **Static animation is NOT penalized for lack of motion.** Judge 2D/vector/cartoon art purely on rendering clarity and consistency — a clean static illustration can score 4.

---

## Score Anchors

### Score 5 — Excellent
- High resolution (720p or above), sharp throughout the entire video
- Smooth motion, no temporal flickering or abrupt brightness/contrast changes
- No blur on faces, hands, or body parts
- No AI-generation artifacts (no morphing, no shape-shifting body parts)
- Overall cinematic or broadcast quality
- **Example cues:** "clear and smooth, everything looks perfect like real video"

### Score 4 — Good
- Generally clear with minor imperfections that do not significantly affect viewing
- Acceptable resolution (typically 512x512 or higher)
- **Permitted issues (each one individually):**
  - Slight blur on hands or face in a subset of frames
  - One character's arm or finger slightly overlapping an object
  - Minor facial feature inconsistency across frames
  - Slight softness in shadow areas or background
- **Not permitted for a 4:** heavy hand/face distortion, visible watermarks, severe deformation

### Score 3 — Moderate
- Noticeable quality issues that affect but do not ruin the viewing experience
- Subject and scene are still clearly identifiable
- **Typical issues:**
  - Face is consistently blurry or low-resolution but recognizable
  - Background lacks clarity
  - Choppy frame rate / low FPS feel
  - Minor AI artifacts in hair, clothing edges
  - Very short duration (≤2s) contributing to limited visual richness
- **Not permitted for a 3:** severe body deformation, extreme pixelation making subject unrecognizable

### Score 2 — Poor
- Significant quality problems that substantially degrade viewing
- **Typical issues:**
  - Very low resolution (256x256) with heavy pixelation
  - Body shape or face constantly deforming or distorting across frames
  - Visible watermarks (e.g., Shutterstock, POND5) dominating the frame
  - Strong temporal instability (colors/contrast fluctuate dramatically)
  - Subject recognizable but severely degraded
- **Example cues:** "The resolution is very low, and the girl's body shape and face are heavily blurred and constantly deforming"

### Score 1 — Very Poor
- Extremely poor quality making the content largely unrecognizable
- **Typical issues:**
  - Subject unrecognizable due to extreme pixelation/compression artifacts
  - Characters in complete disarray with overlapping/intertwining bodies
  - Faces with missing or incoherent features (blank faces, no facial detail) — this applies equally to animated characters: a girl with a completely featureless blank face = score 1 regardless of resolution
  - Pervasive heavy motion blur across most frames making character details impossible to perceive (even if the scene type is identifiable)
  - Scene lacks any useful visual information
- **Example cues:** "We can hardly identify people and his motion in the video"; "The character rendering is severely compromised: facial features are missing"; "pervasive motion blur and compression artifacts — many characters exhibit severe blurring and distortion"

---

## Key Artifacts to Check

| Artifact | Impact | Notes |
|----------|--------|-------|
| Face deformation/morphing across frames | −1 to −2 pts | Very common in AI-generated videos |
| Blank/featureless face (animated characters) | Drops to score 1 | No eyes/nose/mouth = unrecognizable |
| Temporal face instability (hat changing, beard density shifting, face proportions inconsistent across frames) | −2 pts | Drops to score ≤2 even if individual frames look sharp |
| Hand distortion / wrong finger count | −1 pt per frame if pervasive | Check hands closely in **static/near-static** scenes only |
| Body part overlap with clothing | −0.5 to −1 pt | Arms overlapping dress, etc. |
| Pervasive heavy motion blur (most frames, character details lost) | Drops to score 1–2 | Distinct from brief motion blur on fast movements |
| Watermark (Shutterstock, POND5, etc.) | −2 pts minimum | Drops to score ≤2 |
| Resolution ≤ 256x256 | −2 pts minimum | Drops to score ≤2 |
| Resolution 512x512 | Neutral — can still score 3–5 depending on other factors | |
| Flickering brightness/contrast | −1 pt | Check across all sampled frames |
| Very short clip (≤1.5s) | −0.5 to −1 pt | Limits viewing experience |
| Static/minimal animation (2D, vector, cartoon) | **No penalty** | Motion amount is irrelevant to VQ — judge rendering clarity only |

---

## Common Model Mistakes to Avoid

1. **Do not give score 4+ to low-res (256x256) videos** — even if the content is visible, resolution alone warrants ≤2.
2. **Do not ignore body/face deformation** — if body shapes shift unnaturally between frames, deduct 1–2 points.
3. **Do not give score 5 unless the video is genuinely cinematic quality** — score 5 is rare (720p+, smooth, no artifacts at all).
4. **Watermarks immediately cap the score at 2** regardless of other qualities.
5. **Check hands carefully** — AI-generated videos frequently produce incorrect hand anatomy.
6. **Do not penalize static or 2D/vector animation for lack of motion.** A clean cartoon illustration that barely moves can still score 4. Motion amount is NOT a visual quality criterion.
7. **Treat pervasive heavy motion blur as score 1–2**, not 3. "Heavy motion blur throughout making characters hard to perceive" = score 1, same as extreme pixelation. Brief motion blur on fast-moving objects is acceptable.
8. **Temporal face instability (hat color changes, beard density shifts, face proportions vary across frames) = score 2**, even if individual frames appear relatively sharp. This is a form of AI generation artifact.
