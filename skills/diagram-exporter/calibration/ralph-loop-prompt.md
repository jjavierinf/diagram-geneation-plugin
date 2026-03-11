# Diagram Quality Calibration - Ralph Loop Prompt

You are running iteration N of a diagram quality calibration loop. Your job is to generate a diagram, validate it through the 3-stage pipeline, do visual review, detect gaps between visual and programmatic validation, and log everything.

## Step 0: Read State

```bash
cat ~/repos/claude-skills/skills/diagram-exporter/calibration/state.json
```

Read the `iteration` field. Increment it by 1. That's your current iteration number.

## Step 1: Pick Spec

```bash
cat ~/repos/claude-skills/skills/diagram-exporter/calibration/diagram-specs.json
```

Your spec is `specs[iteration - 1]` (0-indexed). If iteration > 20, you're in REGRESSION phase - read the spec's description to find which diagram to re-generate.

For REGRESSION iterations (21-25): Look at `calibration-log.jsonl`, find the 5 lowest-scoring iterations from 1-20, and re-generate those diagrams using the same spec but with all accumulated rules from `skill-rule-updates.md` applied.

## Step 2: Generate the Diagram

Use the `architecture-diagram-creator` skill patterns to create an HTML file with SVG diagram matching the spec. Save to:

```
~/repos/claude-skills/skills/diagram-exporter/calibration/diagrams/iter-{N}.html
```

**IMPORTANT generation rules:**
- Zone backgrounds must use opacity 0.25-0.40 (NOT the faint 0.05-0.10 that produces invisible zones)
- Zone fill colors: use saturated pastels like `#b3d9ff` (blue), `#b3e6cc` (green), `#ffd9b3` (amber), `#e6ccff` (purple)
- Read `skill-rule-updates.md` and apply ALL accumulated rules
- Read `diagram-standards.md` memory file and follow all conventions

## Step 3: Stage 1 - SVG Validation

```bash
python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/validate_svg.py \
  ~/repos/claude-skills/skills/diagram-exporter/calibration/diagrams/iter-{N}.html --json
```

If FAIL: fix issues and re-validate (up to 3 tries). Log each attempt.

## Step 4: Stage 2 - DrawIO Conversion + Validation

```bash
python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/svg2drawio.py \
  ~/repos/claude-skills/skills/diagram-exporter/calibration/diagrams/iter-{N}.html \
  /tmp/calibration-iter-{N}.drawio

python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/validate_drawio.py \
  /tmp/calibration-iter-{N}.drawio \
  --source-html ~/repos/claude-skills/skills/diagram-exporter/calibration/diagrams/iter-{N}.html
```

## Step 5: Stage 3A - Render + Programmatic Check

```bash
~/repos/claude-skills/skills/diagram-exporter/scripts/render_drawio.sh \
  /tmp/calibration-iter-{N}.drawio /tmp/calibration-renders-{N}/

python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/validate_render.py \
  /tmp/calibration-renders-{N}/tab1.png
```

## Step 6: Stage 3B - Visual Review

Read the rendered PNG (`/tmp/calibration-renders-{N}/tab1.png`) and perform visual review using the checklist from `scripts/visual_review_prompt.md`.

Score the diagram 1-10. Fill the full checklist.

## Step 7: Gap Detection

For each visual review checklist item that FAILED:

1. Check if ANY programmatic validator (Stage 1, 2, or 3A) flagged the same issue
2. If NO validator caught it → this is a GAP
3. Classify the gap:
   - `zone_opacity_low` - zone backgrounds too faint to see
   - `crammed_text` - text fits technically but is visually crammed (needs more margin)
   - `subtle_convergence` - arrows converge but within current threshold
   - `indistinguishable_dashes` - dashed/dotted lines look too similar
   - `poor_color_grouping` - zone colors too similar to component colors
   - `arrow_label_collision` - arrow labels overlap other elements
   - `asymmetric_layout` - parallel structures not visually parallel
   - `zone_label_confusion` - zone labels blend with component labels
   - `excessive_whitespace_local` - large empty area within a zone (not caught by global check)
   - `poor_visual_hierarchy` - all elements same visual weight, no emphasis
   - NEW TYPE if none above fits (document it clearly)

## Step 8: Log Results

Append one JSON line to `calibration-log.jsonl`:

```json
{
  "iteration": N,
  "spec_id": <id>,
  "spec_name": "<name>",
  "wave": <wave>,
  "stage1_status": "PASS|WARN|FAIL",
  "stage1_issues": <count>,
  "stage1_retries": <count>,
  "stage2_status": "PASS|WARN|FAIL",
  "stage3a_status": "PASS|WARN|FAIL",
  "visual_score": <1-10>,
  "visual_checklist": {"text_quality": <pass_count>/<total>, "arrow_quality": <pass_count>/<total>, "layout_quality": <pass_count>/<total>, "visual_polish": <pass_count>/<total>},
  "gaps": [{"type": "<gap_type>", "description": "<what visual review found>", "suggested_check": "<how to detect programmatically>"}],
  "file": "diagrams/iter-{N}.html"
}
```

## Step 9: Update State

Update `state.json`:
- Increment `iteration`
- Append visual score to `scores` array
- If new gaps found: update `gap_types_seen` counts, set `last_gap_iteration` to current
- For each gap type with 2+ occurrences: flag it for validator update

## Step 10: Calibration Batch (every 5th iteration: 5, 10, 15, 20)

If `iteration % 5 == 0`:

1. **Aggregate gaps** from `calibration-log.jsonl` for the last 5 iterations
2. **For gap types with 2+ occurrences**: add a check to `validate_svg.py`
   - Write the check function following the existing pattern
   - Add it to `ALL_CHECKS` list
   - Test it against all previous diagrams
3. **For generation issues**: add a rule to `skill-rule-updates.md`
4. **Update `known-visual-issues.md`** with new entries or status changes
5. **Increment `validator_updates` or `skill_rule_updates` in state.json**

## Step 11: Check Completion

ALL must be true:
- `iteration >= 20`
- Last 3 scores in `scores` array are ALL >= 7
- `iteration - last_gap_iteration >= 5` (no new gaps in 5 iterations)
- `known-visual-issues.md` unchanged for 3+ iterations

If ALL true, output: `<promise>CALIBRATION COMPLETE</promise>`

If NOT complete, output what's needed:
- "Continuing: iteration {N} done, score {S}/10, {G} new gaps. Next: iteration {N+1}."

## Notes

- If render_drawio.sh fails (Docker not available), skip Stage 3A/3B but still do Stage 1+2 and score based on SVG visual review directly (read the HTML SVG)
- If a validator update breaks existing passing diagrams, revert and find a less aggressive threshold
- Keep the log append-only - never delete entries
- The prompt is self-contained: read state, do work, update state, check completion
