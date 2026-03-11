---
name: diagram-exporter
description: Use when exporting HTML/SVG architecture diagrams to PowerPoint slides, editable DrawIO files, or both. Triggers on "export diagram", "make PPTX", "make PowerPoint", "drawio", "presentation from diagram", "editable diagram", "convert SVG".
---

# Diagram Exporter

Export HTML/SVG architecture diagrams to PPTX (screenshot-based, crisp) or Draw.io (editable boxes/arrows).

## When to Use

- User wants a PowerPoint from an HTML architecture diagram
- User wants an editable .drawio file from SVG diagrams
- User says "export", "presentation", "pptx", "drawio", "editable diagram"

**NOT for creating diagrams** - use `architecture-diagram-creator` for that.

## Quick Reference

| Format | Command | What You Get |
|--------|---------|--------------|
| PPTX | `python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/svg2pptx.py <html> <output.pptx>` | SVG validation + title slide + one slide per diagram (4x screenshots) |
| DrawIO | `python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/svg2drawio.py <html> <output.drawio>` | Editable diagram with boxes, arrows, text (one tab per SVG) |

## PPTX Workflow

1. **Stage 1 SVG lint runs automatically** before screenshots (via `validate_svg.py`)
   - FAIL (exit 1): export aborts with error message - fix SVG issues first
   - WARN (exit 2): warnings printed but export continues
   - Use `--no-validate` to skip validation
2. It screenshots each `.diagram-wrap svg` at 4x resolution via Puppeteer
3. Builds 16:9 slides: dark title slide + one diagram per slide
4. Optional `--title "Custom Title"` flag
5. **Stage 3B visual review recommended**: after export, review the output PNGs/slides for visual quality (text readability, arrow routing, layout balance)

```bash
# Default: validates SVGs before screenshotting
python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/svg2pptx.py \
  docs/optimove-ceo-overview.html \
  /tmp/optimove-diagrams.pptx

# Skip validation (not recommended)
python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/svg2pptx.py \
  docs/optimove-ceo-overview.html \
  /tmp/optimove-diagrams.pptx --no-validate
```

## DrawIO Workflow

1. Run the svg2drawio.py command
2. It parses SVG elements and maps them to Draw.io cells
3. Each SVG becomes a separate tab in the .drawio file
4. Result is editable (drag boxes, reconnect arrows)

```bash
python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/svg2drawio.py \
  docs/optimove-ceo-overview.html \
  /tmp/optimove-diagrams.drawio
```

## Element Mapping (DrawIO)

| SVG Element | DrawIO Result |
|-------------|---------------|
| Large light-fill `<rect>` | Zone container (swimlane) |
| `<rect>` with gradient/solid | Vertex box, color from gradient |
| `<text>` near a rect | Label (`value` attribute) |
| `<line>` with marker-end | Edge arrow |
| `<path>` M/L commands | Edge with waypoints |
| `stroke-dasharray` | Dashed edge |
| Multiple `<text>` in rect | `<br>` separated HTML label |

## DrawIO Quality Validation (REQUIRED)

**WARNING:** Do NOT use an HTML preview to validate DrawIO output. HTML renders text like SVG (exact pixel positions) but Draw.io has different font metrics, ~5px internal cell padding, and different line-height. Text that looks fine in HTML WILL overlap in Draw.io.

**Use the real Draw.io renderer:**

```bash
# Render all tabs to PNG using draw.io-export (real engine)
~/repos/claude-skills/skills/diagram-exporter/scripts/render_drawio.sh \
  output.drawio /tmp/drawio-review/
```

**Automated validation (run EVERY time):**

```bash
python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/validate_drawio.py \
  output.drawio --source-html source.html
```

Checks: cell overlap detection (with draw.io padding), empty labels, orphan edges, font legibility, text completeness vs source SVG, out-of-bounds coordinates.

**Full review process (iterate until quality >= 7/10):**
1. Generate the .drawio file
2. Run `validate_drawio.py` - fix any FAIL issues, review WARN issues
3. Render each tab with `render_drawio.sh`
4. Read each PNG and check for: text overlap, text truncation, arrow routing errors
5. If issues found, fix `svg2drawio.py` and re-render
6. Optionally send renders to an independent review agent for rating (target: 7+/10)

**Known converter limitations:**
- SVG fonts < 9px are scaled to 10-11px minimum for readability
- Very small nested rects (badges, table cells < 3500px² area) are skipped; their text becomes floating labels
- Page-level titles (center-anchored, wider than zone) are kept as floating text, not zone labels
- Draw.io's internal padding means tightly-packed SVG layouts lose some detail

## 3-Stage Validation Pipeline

Quality validation runs at three stages. Use ALL stages for production diagrams.

### Stage 1: SVG Lint (after HTML generation)

```bash
python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/validate_svg.py <html-file>
```

11 checks: text-in-bounds, text-overlap, arrow-routing, arrow-convergence, arrow-through-text, consistent-spacing, whitespace-balance, label-completeness, font-consistency, color-consistency, has-title. Escalates to FAIL when 10+ issues found.

Run IMMEDIATELY after generating the HTML. Fix SVG issues before converting.

### Stage 2: Conversion Check (after DrawIO generation)

The existing `validate_drawio.py` command above.

### Stage 3: Visual Review (after rendering)

**3A. Programmatic PNG check:**
```bash
python3 ~/repos/claude-skills/skills/diagram-exporter/scripts/validate_render.py <png-file>
```

**3B. Agent visual review (ALWAYS run for final output):**

Dispatch a subagent with the prompt template in `scripts/visual_review_prompt.md` plus the rendered PNG. Target score: 7+/10.

### C4 Semantic Validation

When exporting C4 diagrams, additional semantic checks are available.

- **`--c4` flag** - Enables C4-specific validation. Auto-detected when `data-c4-level` attributes are present on SVG elements.
- **`--strict` flag** - Enforces full C4 compliance (all 8 checks must pass, warnings become errors).

**C4-specific checks (8):**
1. Every element has a valid `data-c4-type` (Person, System, Container, Component, External)
2. `data-c4-level` is consistent across the diagram (no mixed levels)
3. All elements have `data-c4-description` set
4. Color matches the C4 type (e.g., Person = `#08427B`)
5. Element labels follow the Name / [Type: Tech] / Description pattern
6. Relationships have verb-phrase labels (not empty arrows)
7. External elements use gray (`#999999`) fill
8. No orphan elements (every node has at least one relationship)

**DrawIO C4 export:** When `data-c4-*` attributes are detected, `svg2drawio.py` auto-generates native C4 `<object>` elements with `c4Type`, `c4Technology`, and `c4Description` properties, making the output compatible with Draw.io's built-in C4 shape library.

### Full Pipeline Example (DrawIO)

```bash
SKILL=~/repos/claude-skills/skills/diagram-exporter

# Stage 1: Lint source SVG
python3 $SKILL/scripts/validate_svg.py docs/my-diagram.html

# Convert
python3 $SKILL/scripts/svg2drawio.py docs/my-diagram.html /tmp/out.drawio

# Stage 2: Check conversion
python3 $SKILL/scripts/validate_drawio.py /tmp/out.drawio --source-html docs/my-diagram.html

# Render
$SKILL/scripts/render_drawio.sh /tmp/out.drawio /tmp/renders/

# Stage 3A: Check render
python3 $SKILL/scripts/validate_render.py /tmp/renders/tab1.png

# Stage 3B: Visual review (dispatch subagent with visual_review_prompt.md + PNG)
```

### Full Pipeline Example (PPTX)

```bash
SKILL=~/repos/claude-skills/skills/diagram-exporter

# Stage 1 runs automatically inside svg2pptx.py (--validate is default)
python3 $SKILL/scripts/svg2pptx.py docs/my-diagram.html /tmp/out.pptx

# Stage 3B: Visual review - open the PPTX and check slide quality
# or dispatch subagent with visual_review_prompt.md + screenshot of slides
```

## Calibration Loop

Automated quality calibration that generates 25 diagrams, validates through all 3 stages, does visual review, and feeds gaps back into validators and generation rules.

**Infrastructure:** `calibration/` directory with:
- `state.json` - iteration counter, scores, gap tracking
- `calibration-log.jsonl` - per-iteration structured results
- `diagram-specs.json` - 25 diagram specifications (5 waves of increasing complexity)
- `known-visual-issues.md` - catalog of visual-only gaps
- `skill-rule-updates.md` - generation rules learned from gaps
- `diagrams/` - generated HTML files

**Launch:**
```bash
# Use Ralph Loop with the calibration prompt
cat ~/repos/claude-skills/skills/diagram-exporter/calibration/ralph-loop-prompt.md
# Then: /ralph-loop "<prompt content>" --max-iterations 30 --completion-promise "CALIBRATION COMPLETE"
```

**Completion criteria:** 20+ iterations, last 3 scores >= 7, no new gaps in 5 iterations.

## Requirements

- **Node.js + Puppeteer**: `npm install puppeteer` (for PPTX screenshots)
- **python-pptx**: `pip install python-pptx` (for PPTX generation)
- **draw.io-export**: `npm install draw.io-export` (for DrawIO visual validation)
- No extra deps needed for DrawIO generation itself (plain XML)

## Input Format

HTML files must have SVG diagrams wrapped in `.diagram-wrap` divs:
```html
<div class="diagram-wrap">
  <svg viewBox="0 0 1100 530">...</svg>
</div>
```

Section titles are extracted from the nearest `<h2>` element. Page title from `.hero h1`.
