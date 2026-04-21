# Physical & Common-Sense Consistency Scoring Rubric

## Definition
Physical/common-sense consistency examines whether the video contains violations of physical laws, common sense, or normal real-world behavior. This includes body anatomy, object behavior, spatial relationships, natural motion, and AI-generation artifacts that produce physically impossible content.

## Calibration Insights (from human annotation analysis)
This is the **most underscored dimension by model evaluators** — the largest accuracy gap with the highest bias (+0.82). Models consistently give 4–5 while human annotators give 1–2, because:

- **Models focus on "does the overall scene make sense?"** — a person on a beach, a horse running, etc.
- **Human annotators focus on frame-level AI artifacts** — body parts deforming, objects teleporting, hands with wrong anatomy, items appearing/disappearing.

Human annotators penalize **any** physically impossible frame-level artifact, even if it's subtle. A score of 1 is common for AI-generated videos with persistent deformation artifacts.

---

## Score Anchors

### Score 5 — No Violations
- Zero physically implausible events across all frames
- Body parts, objects, and environment behave exactly as they would in reality
- Motion (human, animal, object) is fully natural and biomechanically plausible
- **Example cues:** "The person's movements and actions are natural, with no violations of common sense or physical laws"; "Studio setup is physically coherent and natural"

### Score 4 — Minor Violations
- One or two very minor issues that don't significantly break immersion
- **Permitted issues (each one individually):**
  - Slightly awkward posture in one frame
  - Very minor hand rendering imprecision (e.g., brief finger blur) in 1–2 frames
  - Slight camera drift that creates mild temporal inconsistency
  - Background crowd element appearing/disappearing briefly
- **NOT permitted for a 4:** any persistent deformation, wrong finger count, object passing through another object

### Score 3 — Moderate Violations
- Noticeable physical issues that are clearly anomalous but do not completely break the scene
- **Typical issues:**
  - Body shape changes slightly between frames but subject remains recognizable
  - One hand has unclear anatomy in multiple frames
  - Object (food, prop) changes position slightly in a static scene
  - Stylized art (cartoon, anime) with anatomically exaggerated but genre-consistent proportions
  - Running/walking motion looks slightly robotic or unnatural
- **Example cues:** "The running motion appears artificial and stiff"; "body proportions shift across frames, indicating limited animation precision"

### Score 2 — Significant Violations
- Clear physical impossibilities that would not occur in reality
- **Typical issues:**
  - Food items on a plate change position, amount, or shape significantly between frames
  - A body part (arm, leg) noticeably changes length or shape across frames
  - A person's upper body appears from an impossible spatial position
  - Object passes through another solid object
  - Pencil passes through a palm; extra fingers visible; object held impossibly
- **Example cues:** "Some banana slices move and then disappear, while the amount of cereal continuously increases"; "The movements of the fingers and hands appear slightly awkward... showing the man's upper body emerging from the gap between the two tables appears abrupt and unnatural"

### Score 1 — Severe Violations
- Pervasive, severe physical impossibilities that dominate the video
- **Typical issues:**
  - Characters' bodies overlap and intertwine continuously
  - Body parts (arms, legs, torso) constantly change shape or disappear
  - Face has missing features (blank face) or continuously morphs
  - Objects or people appear and disappear suddenly across multiple frames
  - Animals with wrong number of limbs (cat alternating between 2 and 3 legs)
  - Extreme spatial incoherence (flying fish, people floating without explanation)
- **Example cues:** "The characters are in complete disarray, their bodies overlap and intertwine, appearing and disappearing again and again suddenly"; "The cat beside her alternates between having two and three legs, which completely violates real-world physics"; "The woman's limbs and torso are constantly twisting and changing, and her head is severely distorted"

---

## Anatomy Checklist (check every video)

### Hands & Fingers
- [ ] Correct number of fingers (5 per hand)
- [ ] Fingers do not pass through objects being held
- [ ] Hand shape consistent across frames
- [ ] No extra/missing fingers

### Face
- [ ] Facial features (eyes, nose, mouth) present and stable
- [ ] Face does not morph between frames
- [ ] Proportions consistent

### Body
- [ ] Limbs do not change length or shape
- [ ] Body parts do not overlap with clothing unnaturally
- [ ] No body parts appear/disappear
- [ ] Proportions stable across frames

### Objects & Environment
- [ ] Objects remain in consistent positions (for static scenes)
- [ ] Quantities stable (food does not multiply/disappear)
- [ ] Objects do not pass through each other
- [ ] Lighting and shadows are consistent with scene physics

### Motion
- [ ] Human/animal gait looks biomechanically plausible
- [ ] Object trajectories follow gravity/physics
- [ ] No teleportation (sudden position jumps)

---

## Special Cases

### Fantasy / Sci-Fi / Stylized Content
When the prompt specifies a fantasy or stylized setting (e.g., Darth Vader, anime characters), evaluate consistency **within the established world rules**:
- Darth Vader on a beach: his outfit and behavior should be internally consistent with the character
- Anime characters: anatomical exaggeration is expected; flag inconsistencies within the style
- Magic effects: judge whether effects are stable and intentional vs. AI artifact

### Very Short Videos (≤2 frames sampled)
With very few frames, you have limited information. Be conservative — only flag violations that are clearly visible. Do not assume violations exist beyond what is seen.

---

## Common Model Mistakes to Avoid

1. **Do not give 4–5 just because the overall scene "makes sense."** Always inspect individual body parts, especially hands and faces, for deformations.
2. **Frame-level artifacts count.** Even one frame with a wrong hand shape or morphing face is a violation worth noting.
3. **Objects appearing/disappearing in static scenes are score 2 violations**, not minor issues.
4. **AI generation artifacts (morphing, deformation) are physical violations**, not just visual quality issues — they should penalize BOTH visual quality AND physical consistency.
5. **Do not conflate "fantasy context = no physics rules."** Fantasy characters still must behave consistently within their own frames.
6. **Blur and compression artifacts are NOT physical violations.** A blurry face is a visual quality issue — it does not mean the face is "morphing." Only penalize PHY when body parts/objects demonstrably change shape, position, or quantity between frames in a way that is physically impossible. If you cannot see the face clearly due to blur, do not assume deformation.
7. **Motion blur on hands/fingers during fast movements (waving, gesturing, running) is NOT a finger-count violation.** Only check finger count and hand anatomy in near-static hand positions where fingers are clearly visible. Apparent anomalies during motion blur are an artifact of the sampling rate, not a physics violation.
