# Text-to-Video Alignment Scoring Rubric

## Definition
T2V alignment measures how fully and accurately the video depicts **all** elements specified in the text prompt: characters (appearance, count, clothing, attributes), actions (including sequential steps), scene/background, quantities, colors, camera movements, and art style.

## Calibration Insights (from human annotation analysis)
Model evaluators have a slight tendency to under-score T2V alignment (being too strict). Key patterns:
- **Undercounting elements**: missing a single small detail (blue sunglasses, specific poster text) when the rest matches → score is still 4, not 3
- **Over-requiring explicit action verification**: if an action is ambiguous due to viewpoint/resolution but the core subject/activity is present, give credit rather than penalizing
- **Penalizing static descriptive scenes for lack of motion**: if the prompt describes a scene or setting (not an action sequence), a static video that depicts all visual elements correctly = score 4–5. Do NOT deduct for absence of movement
- **Empty prompt edge case**: if the prompt file is empty, score based on whether the video content looks like a plausible generic scene (may still score 3–4)
- **Overcounting matches**: giving credit for approximate matches that don't actually match (e.g., generic green fields ≠ coffee plantation)

---

## Score Anchors

### Score 5 — Perfect Alignment
- Every element in the prompt is present and accurate
- Characters match description (correct clothing color, style, accessories)
- All specified actions are performed in sequence
- Camera movements (pan, tilt, crane, zoom) are executed (if specified)
- Background/setting matches precisely
- **Descriptive/scene prompts**: if the prompt describes a place or visual scene (no actions required), all described visual elements present = score 5
- **Example cues:** "The text-to-video alignment is perfect"; "All characters and their motions are present"; "All motion and objects are reflected in the video"

### Score 4 — Strong Alignment
- Almost all elements are present; only minor details are missing or slightly off
- **Permitted mismatches (each one individually):**
  - One accessory wrong (e.g., no blue sunglasses when most clothing matches)
  - Spatial arrangement slightly different from described
  - One of multiple sequential actions partially executed
  - A named element approximated but recognizable (e.g., correct style but wrong color)
- **Example cues:** "Most elements from the prompt are reflected in the video, except that the woman is not wearing blue sunglasses"

### Score 3 — Partial Alignment
- Core subject/setting is present, but multiple specific elements are missing or incorrect
- **Typical issues:**
  - Correct type of character but wrong attributes (wrong clothing, color, accessories)
  - Some actions missing from a multi-step sequence
  - Camera movement not executed (static when pan/tilt/crane was specified)
  - Background is approximate but not accurate
  - Named entities not identifiable
  - **Two specific misses** (e.g., one background element absent + camera movement absent) → score 3, not 2, when the core subject matches
- **Example cues:** "The couple is terrified is not explicitly shown"; "Cobblestone street and sunrise present but town name and cottage character not strongly conveyed"; "stars not shown and pan left not presented"

### Score 2 — Weak Alignment
- Major elements are missing or significantly mismatched
- **Typical issues:**
  - Wrong scene type entirely (e.g., a brawl instead of a robbery)
  - Key character absent (e.g., the main character not visible)
  - Key action not performed at all
  - Wrong gender, wrong number of characters
  - Prompt specifies multiple elements; fewer than half are present
- **Example cues:** "Correct character type present but none of the three specified actions are shown"; "Beach setting completely absent"

### Score 1 — No Alignment
- Essentially no correspondence between the prompt and the video
- Wrong content entirely, or the video is so cropped/abstract that alignment cannot be assessed
- **Example cues:** "There is essentially no alignment between the prompt and the video content. The described person, setting, prop, and action are not present"

---

## Checklist: What to Verify in Every Evaluation

### Characters
- [ ] Count of characters matches prompt
- [ ] Gender, age, ethnicity match (if specified)
- [ ] Clothing: colors, style, specific items (jacket, shirt, cap, dress)
- [ ] Accessories: glasses, hat, bag, headphones, instruments
- [ ] Named characters identifiable (if named in prompt)

### Actions
- [ ] Each specified action is present (check sequentially)
- [ ] Order of actions matches if a sequence is described
- [ ] Verbs: "walks", "runs", "turns", "smiles", "picks up" — each must be visible
- [ ] Intensity/manner: "slowly", "dramatically", "with focus"

### Scene / Background
- [ ] Location type matches (indoors/outdoors, forest, beach, studio, etc.)
- [ ] Specific props mentioned (microphone, toolbox, hammer, laptop)
- [ ] Colors of background/walls/floor
- [ ] Weather, lighting, time of day

### Camera / Motion
- [ ] Pan left/right
- [ ] Tilt up/down
- [ ] Crane up/down
- [ ] Zoom in/out
- [ ] Static vs. handheld vs. tracking

### Style
- [ ] Art style: anime, cartoon, 2D animation, photorealistic, watercolor
- [ ] Named style markers: "ink wash", "vector anime", "Japanese anime"

---

## Common Model Mistakes to Avoid

1. **Do not give credit for wrong approximations.** Generic green fields ≠ coffee/tea plantation. Score as a miss.
2. **Camera movements count.** If the prompt says "pan left" and there is no pan, that is a miss worth −1 score level.
3. **Sequential actions must ALL be present.** If prompt says "ties ribbon, wraps gift, hands to friend" and only ribbon-tying is shown, that is at best a 3.
4. **Empty prompt files**: if the `.generation_text` file is empty, note this explicitly and score T2V alignment as N/A or apply lenient scoring based on plausibility.
5. **Spatial relationships matter.** Cereal and banana slices together in one bowl ≠ "a plate with sliced bananas and a bowl of cereal."
6. **Do not over-require explicit action confirmation.** If an action is ambiguous due to viewpoint, resolution, or framing — but the core subject/activity is plausibly present — give benefit of the doubt rather than scoring as absent. Only mark an action as missing when it is clearly not shown.
7. **Do not penalize descriptive scene prompts for being static.** If the prompt describes a setting or visual scene (e.g., "a quaint cobblestone town at sunrise") and all described visual elements are present, score 4–5 even if the video has no movement. Motion is only required when the prompt explicitly calls for action.
8. **Two specific misses ≠ score 2.** If the core character/subject/setting is correct but two peripheral details (e.g., a background element + camera movement) are missing, that is score 3. Score 2 requires major elements absent.
