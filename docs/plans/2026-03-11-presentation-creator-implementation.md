# Presentation Creator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a `presentation-creator` skill that generates complete, multi-slide PPTX presentations with narrative structure, proper layouts, concise text, speaker notes, and embedded diagrams.

**Architecture:** A SKILL.md instructs Claude to plan narrative structure and generate a JSON slide spec. A `create_pptx.py` script takes that JSON + a template .pptx and assembles the final presentation. Diagram images come from the existing screenshot pipeline (Puppeteer).

**Tech Stack:** python-pptx, JSON slide spec, Puppeteer (for diagram screenshots)

**Repo:** `~/repos/diagram-generation-plugin`

---

### Task 1: Create the default PPTX template

**Files:**
- Create: `skills/presentation-creator/assets/templates/default.pptx`
- Create: `skills/presentation-creator/scripts/build_template.py`

**Step 1: Create directory structure**

```bash
mkdir -p ~/repos/diagram-generation-plugin/skills/presentation-creator/assets/templates
mkdir -p ~/repos/diagram-generation-plugin/skills/presentation-creator/scripts
```

**Step 2: Write the template builder script**

Create `skills/presentation-creator/scripts/build_template.py` — a python script that generates the default.pptx template using python-pptx. This script is run once to generate the template (not at runtime).

The template must contain these slide layouts in its slide master:

| Index | Layout Name | Placeholders |
|-------|------------|-------------|
| 0 | Title Slide | title (centered, 40pt bold), subtitle (20pt), accent line |
| 1 | Section Divider | title (white on accent background) |
| 2 | Content | title (top, bold), body (left 60%), image area (right 40%) |
| 3 | Two Column | title (top), left body, right body (50/50 split) |
| 4 | Bullet List | title (top), body with bullet points |
| 5 | Diagram | title (top, small), full-width image area |
| 6 | Comparison | title, left-title + left-body, right-title + right-body |
| 7 | Quote | large quote text (centered, italic), attribution below |
| 8 | Closing | title (centered), subtitle, contact line |
| 9 | Blank | (fallback, no placeholders) |

Design system:
- Colors: `#2D2D2D` (text), `#006DA3` (accent/headers), `#FFFFFF` (background)
- Font: Calibri
- Title: 28-32pt bold
- Body: 16-18pt
- Slide size: 13.333" x 7.5" (widescreen 16:9)

Since python-pptx cannot create custom slide layouts in slide masters programmatically, the script should:
1. Create a `Presentation()` with standard dimensions
2. Create one example slide per layout type using `slide_layouts[6]` (Blank) as base
3. Use shapes and textboxes positioned consistently to simulate layouts
4. Save as `default.pptx`

NOTE: This template is a starter. The user will replace it with their own corporate template later. What matters now is having a working .pptx that `create_pptx.py` can load and populate.

```python
#!/usr/bin/env python3
"""Build the default presentation template.

Run once: python3 build_template.py
Output: ../assets/templates/default.pptx
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

ACCENT = RGBColor(0x00, 0x6D, 0xA3)
DARK = RGBColor(0x2D, 0x2D, 0x2D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF5, 0xF5, 0xF5)
FONT = 'Calibri'

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'assets', 'templates', 'default.pptx')


def _textbox(slide, left, top, width, height, text, size=18, bold=False,
             color=DARK, align=PP_ALIGN.LEFT, font=FONT):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font
    p.alignment = align
    return tb


def _set_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    # 0: Title Slide
    s = prs.slides.add_slide(blank)
    _textbox(s, Inches(1), Inches(2.2), Inches(11.333), Inches(1.5),
             '[Presentation Title]', size=40, bold=True, align=PP_ALIGN.CENTER)
    s.shapes.add_shape(1, Inches(5.5), Inches(3.8), Inches(2.333), Inches(0.05))  # accent line
    _textbox(s, Inches(1), Inches(4.0), Inches(11.333), Inches(1),
             '[Subtitle]', size=20, color=RGBColor(0x66, 0x66, 0x66), align=PP_ALIGN.CENTER)

    # 1: Section Divider
    s = prs.slides.add_slide(blank)
    _set_bg(s, ACCENT)
    _textbox(s, Inches(1), Inches(2.5), Inches(11.333), Inches(2),
             '[Section Title]', size=36, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    # 2: Content (text left, image right)
    s = prs.slides.add_slide(blank)
    _textbox(s, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
             '[Slide Title]', size=28, bold=True, color=ACCENT)
    _textbox(s, Inches(0.5), Inches(1.2), Inches(6.5), Inches(5.5),
             '[Body text goes here. Keep it concise — max 40 words.]', size=18)
    # image placeholder area (right side)
    shape = s.shapes.add_shape(1, Inches(7.5), Inches(1.2), Inches(5.3), Inches(5.5))
    shape.fill.solid()
    shape.fill.fore_color.rgb = LIGHT_GRAY

    # 3: Two Column
    s = prs.slides.add_slide(blank)
    _textbox(s, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
             '[Slide Title]', size=28, bold=True, color=ACCENT)
    _textbox(s, Inches(0.5), Inches(1.2), Inches(5.8), Inches(5.5),
             '[Left column content]', size=18)
    _textbox(s, Inches(7), Inches(1.2), Inches(5.8), Inches(5.5),
             '[Right column content]', size=18)

    # 4: Bullet List
    s = prs.slides.add_slide(blank)
    _textbox(s, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
             '[Slide Title]', size=28, bold=True, color=ACCENT)
    _textbox(s, Inches(0.5), Inches(1.2), Inches(12), Inches(5.5),
             '[• Point one\n• Point two\n• Point three]', size=18)

    # 5: Diagram (full width image)
    s = prs.slides.add_slide(blank)
    _textbox(s, Inches(0.5), Inches(0.2), Inches(12), Inches(0.6),
             '[Diagram Title]', size=22, bold=True, color=DARK)
    shape = s.shapes.add_shape(1, Inches(0.3), Inches(0.9), Inches(12.733), Inches(6.3))
    shape.fill.solid()
    shape.fill.fore_color.rgb = LIGHT_GRAY

    # 6: Comparison
    s = prs.slides.add_slide(blank)
    _textbox(s, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
             '[Comparison Title]', size=28, bold=True, color=ACCENT)
    _textbox(s, Inches(0.5), Inches(1.2), Inches(5.8), Inches(0.5),
             '[Option A]', size=22, bold=True, color=ACCENT)
    _textbox(s, Inches(0.5), Inches(1.8), Inches(5.8), Inches(4.5),
             '[Option A details]', size=18)
    _textbox(s, Inches(7), Inches(1.2), Inches(5.8), Inches(0.5),
             '[Option B]', size=22, bold=True, color=ACCENT)
    _textbox(s, Inches(7), Inches(1.8), Inches(5.8), Inches(4.5),
             '[Option B details]', size=18)

    # 7: Quote
    s = prs.slides.add_slide(blank)
    _textbox(s, Inches(1.5), Inches(2), Inches(10.333), Inches(3),
             '"[Quote text here]"', size=28, color=DARK, align=PP_ALIGN.CENTER)
    _textbox(s, Inches(1.5), Inches(5), Inches(10.333), Inches(0.5),
             '— [Attribution]', size=16, color=RGBColor(0x66, 0x66, 0x66),
             align=PP_ALIGN.CENTER)

    # 8: Closing
    s = prs.slides.add_slide(blank)
    _textbox(s, Inches(1), Inches(2.2), Inches(11.333), Inches(1.5),
             '[Thank You / Questions?]', size=40, bold=True, align=PP_ALIGN.CENTER)
    _textbox(s, Inches(1), Inches(4), Inches(11.333), Inches(1),
             '[contact@email.com]', size=18, color=RGBColor(0x66, 0x66, 0x66),
             align=PP_ALIGN.CENTER)

    prs.save(OUTPUT)
    print(f'Saved template to {OUTPUT}')


if __name__ == '__main__':
    build()
```

**Step 3: Run the builder**

```bash
cd ~/repos/diagram-generation-plugin
python3 skills/presentation-creator/scripts/build_template.py
```

Expected: `Saved template to .../assets/templates/default.pptx`

**Step 4: Verify**

```bash
ls -la skills/presentation-creator/assets/templates/default.pptx
python3 -c "from pptx import Presentation; p = Presentation('skills/presentation-creator/assets/templates/default.pptx'); print(f'{len(p.slides)} slides')"
```

Expected: file exists, 9 slides.

**Step 5: Commit**

```bash
git add skills/presentation-creator/scripts/build_template.py \
  skills/presentation-creator/assets/templates/default.pptx
git commit -m "feat: add default PPTX template and builder script"
```

---

### Task 2: Create create_pptx.py assembly script

**Files:**
- Create: `skills/presentation-creator/scripts/create_pptx.py`

This is the core script. It takes a JSON slide spec and produces a PPTX.

**Step 1: Write create_pptx.py**

```python
#!/usr/bin/env python3
"""
create_pptx.py - Assemble a PPTX presentation from a JSON slide spec.

Usage:
    python3 create_pptx.py <spec.json> <output.pptx> [--template path/to/template.pptx]

The JSON spec format:
{
  "title": "Presentation Title",
  "subtitle": "Optional subtitle",
  "slides": [
    {
      "layout": "title|section-divider|content|two-column|bullet-list|diagram|comparison|quote|closing",
      "title": "Slide Title",
      "body": "Body text (for content, bullet-list)",
      "left": "Left column text (for two-column, comparison)",
      "right": "Right column text (for two-column, comparison)",
      "left_title": "Left header (comparison)",
      "right_title": "Right header (comparison)",
      "image": "/path/to/image.png (for content, diagram)",
      "quote": "Quote text (for quote)",
      "attribution": "Quote attribution (for quote)",
      "subtitle": "Subtitle (for title, closing)",
      "contact": "Contact info (for closing)",
      "notes": "Speaker notes"
    }
  ]
}
"""
import argparse
import json
import os
import sys

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(SCRIPT_DIR, '..', 'assets', 'templates', 'default.pptx')

ACCENT = RGBColor(0x00, 0x6D, 0xA3)
DARK = RGBColor(0x2D, 0x2D, 0x2D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF5, 0xF5, 0xF5)
FONT = 'Calibri'

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def _tb(slide, left, top, width, height, text, size=18, bold=False,
        color=DARK, align=PP_ALIGN.LEFT):
    """Add a textbox with formatted text."""
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = str(text)
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = FONT
    p.alignment = align
    return tf


def _add_notes(slide, notes_text):
    """Add speaker notes to a slide."""
    if notes_text:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = str(notes_text)


def _set_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_image_fit(slide, image_path, left, top, max_w, max_h):
    """Add image fitted within bounds, maintaining aspect ratio."""
    from PIL import Image
    try:
        with Image.open(image_path) as img:
            iw, ih = img.size
    except Exception:
        iw, ih = 1600, 900

    aspect = iw / ih
    if max_w / max_h > aspect:
        h = max_h
        w = int(h * aspect)
    else:
        w = max_w
        h = int(w / aspect)
    x = left + (max_w - w) // 2
    slide.shapes.add_picture(image_path, x, top, w, h)


def build_slide(prs, spec, blank_layout):
    """Build a single slide from a spec dict."""
    layout = spec.get('layout', 'content')
    s = prs.slides.add_slide(blank_layout)

    if layout == 'title':
        _tb(s, Inches(1), Inches(2.2), Inches(11.333), Inches(1.5),
            spec.get('title', ''), size=40, bold=True, align=PP_ALIGN.CENTER)
        # accent line
        s.shapes.add_shape(1, Inches(5.5), Inches(3.8), Inches(2.333), Inches(0.05))
        sub = spec.get('subtitle', '')
        if sub:
            _tb(s, Inches(1), Inches(4.0), Inches(11.333), Inches(1),
                sub, size=20, color=RGBColor(0x66, 0x66, 0x66), align=PP_ALIGN.CENTER)

    elif layout == 'section-divider':
        _set_bg(s, ACCENT)
        _tb(s, Inches(1), Inches(2.5), Inches(11.333), Inches(2),
            spec.get('title', ''), size=36, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    elif layout == 'content':
        _tb(s, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
            spec.get('title', ''), size=28, bold=True, color=ACCENT)
        img = spec.get('image')
        if img and os.path.exists(img):
            _tb(s, Inches(0.5), Inches(1.2), Inches(6.5), Inches(5.5),
                spec.get('body', ''), size=18)
            _add_image_fit(s, img, Inches(7.5), Inches(1.2), Inches(5.3), Inches(5.5))
        else:
            _tb(s, Inches(0.5), Inches(1.2), Inches(12), Inches(5.5),
                spec.get('body', ''), size=18)

    elif layout == 'two-column':
        _tb(s, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
            spec.get('title', ''), size=28, bold=True, color=ACCENT)
        _tb(s, Inches(0.5), Inches(1.2), Inches(5.8), Inches(5.5),
            spec.get('left', ''), size=18)
        _tb(s, Inches(7), Inches(1.2), Inches(5.8), Inches(5.5),
            spec.get('right', ''), size=18)

    elif layout == 'bullet-list':
        _tb(s, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
            spec.get('title', ''), size=28, bold=True, color=ACCENT)
        body = spec.get('body', '')
        _tb(s, Inches(0.5), Inches(1.2), Inches(12), Inches(5.5), body, size=18)

    elif layout == 'diagram':
        _tb(s, Inches(0.5), Inches(0.2), Inches(12), Inches(0.6),
            spec.get('title', ''), size=22, bold=True)
        img = spec.get('image')
        if img and os.path.exists(img):
            _add_image_fit(s, img, Inches(0.3), Inches(0.9), Inches(12.733), Inches(6.3))

    elif layout == 'comparison':
        _tb(s, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
            spec.get('title', ''), size=28, bold=True, color=ACCENT)
        _tb(s, Inches(0.5), Inches(1.2), Inches(5.8), Inches(0.5),
            spec.get('left_title', ''), size=22, bold=True, color=ACCENT)
        _tb(s, Inches(0.5), Inches(1.8), Inches(5.8), Inches(4.5),
            spec.get('left', ''), size=18)
        _tb(s, Inches(7), Inches(1.2), Inches(5.8), Inches(0.5),
            spec.get('right_title', ''), size=22, bold=True, color=ACCENT)
        _tb(s, Inches(7), Inches(1.8), Inches(5.8), Inches(4.5),
            spec.get('right', ''), size=18)

    elif layout == 'quote':
        _tb(s, Inches(1.5), Inches(2), Inches(10.333), Inches(3),
            f'"{spec.get("quote", "")}"', size=28, align=PP_ALIGN.CENTER)
        _tb(s, Inches(1.5), Inches(5), Inches(10.333), Inches(0.5),
            f'— {spec.get("attribution", "")}', size=16,
            color=RGBColor(0x66, 0x66, 0x66), align=PP_ALIGN.CENTER)

    elif layout == 'closing':
        _tb(s, Inches(1), Inches(2.2), Inches(11.333), Inches(1.5),
            spec.get('title', 'Thank You'), size=40, bold=True, align=PP_ALIGN.CENTER)
        sub = spec.get('subtitle', '')
        if sub:
            _tb(s, Inches(1), Inches(4.0), Inches(11.333), Inches(0.5),
                sub, size=20, color=RGBColor(0x66, 0x66, 0x66), align=PP_ALIGN.CENTER)
        contact = spec.get('contact', '')
        if contact:
            _tb(s, Inches(1), Inches(4.8), Inches(11.333), Inches(0.5),
                contact, size=16, color=RGBColor(0x66, 0x66, 0x66), align=PP_ALIGN.CENTER)

    else:
        # Fallback: generic content slide
        _tb(s, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
            spec.get('title', ''), size=28, bold=True, color=ACCENT)
        _tb(s, Inches(0.5), Inches(1.2), Inches(12), Inches(5.5),
            spec.get('body', ''), size=18)

    _add_notes(s, spec.get('notes'))
    return s


def main():
    parser = argparse.ArgumentParser(description='Assemble PPTX from JSON slide spec')
    parser.add_argument('spec_json', help='Path to JSON slide specification')
    parser.add_argument('output_pptx', help='Output PPTX file path')
    parser.add_argument('--template', default=DEFAULT_TEMPLATE,
                        help='Path to template .pptx (default: built-in)')
    args = parser.parse_args()

    with open(args.spec_json) as f:
        spec = json.load(f)

    # Load template to get slide dimensions and style, then clear its slides
    if os.path.exists(args.template):
        prs = Presentation(args.template)
        # Remove template example slides (keep layouts)
        while len(prs.slides) > 0:
            rId = prs.slides._sldIdLst[0].rId
            prs.part.drop_rel(rId)
            del prs.slides._sldIdLst[0]
    else:
        prs = Presentation()
        prs.slide_width = SLIDE_W
        prs.slide_height = SLIDE_H

    blank_layout = prs.slide_layouts[6]  # Blank layout

    # Build slides from spec
    for slide_spec in spec.get('slides', []):
        build_slide(prs, slide_spec, blank_layout)
        print(f"  Built: [{slide_spec.get('layout')}] {slide_spec.get('title', '')[:50]}",
              file=sys.stderr)

    prs.save(args.output_pptx)
    print(f"Saved {args.output_pptx} ({len(prs.slides)} slides)", file=sys.stderr)


if __name__ == '__main__':
    main()
```

**Step 2: Test with a sample spec**

Create `/tmp/test-spec.json`:

```json
{
  "slides": [
    {"layout": "title", "title": "System Architecture", "subtitle": "Q1 2026 Overview"},
    {"layout": "section-divider", "title": "Data Pipeline"},
    {"layout": "bullet-list", "title": "Key Components", "body": "• Airflow orchestration\n• StarRocks analytics\n• MinIO object storage"},
    {"layout": "two-column", "title": "Before vs After", "left": "Manual CSV uploads\nWeekly batch processing\nNo monitoring", "right": "Automated ELT pipeline\nReal-time streaming\nFull observability"},
    {"layout": "closing", "title": "Questions?", "contact": "team@company.com"}
  ]
}
```

Run:

```bash
cd ~/repos/diagram-generation-plugin
python3 skills/presentation-creator/scripts/create_pptx.py \
  /tmp/test-spec.json /tmp/test-presentation.pptx
```

Expected: `Saved /tmp/test-presentation.pptx (5 slides)`

**Step 3: Verify output**

```bash
python3 -c "
from pptx import Presentation
p = Presentation('/tmp/test-presentation.pptx')
for i, s in enumerate(p.slides):
    texts = [sh.text for sh in s.shapes if sh.has_text_frame]
    print(f'Slide {i+1}: {texts[0][:50] if texts else \"(empty)\"}')
"
```

Expected: 5 slides with correct titles.

**Step 4: Commit**

```bash
git add skills/presentation-creator/scripts/create_pptx.py
git commit -m "feat: add PPTX assembly script (create_pptx.py)"
```

---

### Task 3: Create the SKILL.md

**Files:**
- Create: `skills/presentation-creator/SKILL.md`

**Step 1: Write the skill instructions**

```markdown
---
name: presentation-creator
description: Generate complete multi-slide PowerPoint presentations with narrative structure, proper layouts, concise text, speaker notes, and embedded diagrams. Use when users request presentations, slide decks, pitch decks, status updates, or any PPTX output that tells a story.
---

# Presentation Creator

Generate complete PPTX presentations with narrative structure, visual layouts, and embedded diagrams.

## When to Use

- "Create a presentation about X"
- "Make a slide deck for Y"
- "PPTX for the team meeting"
- "Pitch deck for project Z"
- "Status update presentation"

## Workflow

### 1. Understand the Ask

Infer the presentation type and pick a storytelling framework:

| Type | Framework | Structure |
|------|-----------|-----------|
| Technical / architecture | Pyramid | Conclusion → arguments → evidence |
| Proposal / pitch | SCR | Situation → complication → resolution |
| Status update / analytics | What-So What-Now What | Data → implications → action |
| General / other | Problem-Solution-Benefit | Problem → fix → value |

If unclear, default to Problem-Solution-Benefit.

### 2. Plan the Narrative

Before writing any slide content, plan the story arc:
1. What is the ONE key message?
2. What are the 3-5 supporting points?
3. What order creates the most compelling narrative?
4. Where do diagrams add clarity that text cannot?

Output: ordered list of slide ideas (1 idea per slide).

### 3. Assign Layouts

Each slide gets a layout from this vocabulary:

| Layout | Use for |
|--------|---------|
| `title` | First slide only |
| `section-divider` | Transitions between major sections |
| `content` | Text with optional diagram/image on the right |
| `two-column` | Side-by-side comparisons, before/after |
| `bullet-list` | Key points, lists, summaries |
| `diagram` | Full-width architecture or flow diagram |
| `comparison` | Option A vs Option B with headers |
| `quote` | Key quote, callout, or highlight |
| `closing` | Last slide (thank you, questions, contact) |

### 4. Write Content

Rules:
- **Body text:** max 40 words per slide
- **Titles:** max 8 words
- **One idea per slide** — if you have two ideas, use two slides
- **Speaker notes:** put the full detail here, not on the slide
- **Bullets:** max 5 per slide, each max 10 words

### 5. Generate Diagrams (if needed)

If a slide needs a diagram:
1. Use the `architecture-diagram-creator` skill to generate the HTML diagram
2. Screenshot it using the diagram-exporter pipeline (Puppeteer)
3. Reference the PNG path in the slide spec's `image` field

### 6. Assemble the PPTX

Write the slide spec as JSON, then run:

```bash
python3 $SKILL/scripts/create_pptx.py spec.json output.pptx [--template path/to/custom.pptx]
```

### JSON Spec Format

```json
{
  "slides": [
    {
      "layout": "title",
      "title": "Presentation Title",
      "subtitle": "Optional subtitle",
      "notes": "Speaker notes for this slide"
    },
    {
      "layout": "content",
      "title": "Slide Title",
      "body": "Body text here",
      "image": "/path/to/diagram.png",
      "notes": "Detailed speaker notes"
    }
  ]
}
```

Write the JSON to `current_task/slides-spec.json`, then run the assembly script.

### 7. Deliver

Tell the user where the PPTX file is saved.

## Template

Default template: `$SKILL/assets/templates/default.pptx`

The user can provide their own .pptx template via `--template`. The template should use Blank slide layout (index 6) as the base — the script builds all layouts from scratch using shapes.

## Important

- Do NOT use the `diagram-exporter` skill's `svg2pptx.py` — that creates single-diagram slides. This skill creates full narrative presentations.
- Keep slides concise. The presentation should work even if someone only reads the slides without speaker notes.
- If using `technical-discovery` to gather context, run it first, then use the output to plan the narrative.
```

**Step 2: Commit**

```bash
git add skills/presentation-creator/SKILL.md
git commit -m "feat: add presentation-creator skill"
```

---

### Task 4: Smoke Test — Full Presentation Generation

**Files:** (no new files, verification only)

**Step 1: Create a realistic test spec**

Create `/tmp/test-full-spec.json`:

```json
{
  "slides": [
    {
      "layout": "title",
      "title": "Data Platform Architecture",
      "subtitle": "Technical Overview — March 2026",
      "notes": "Welcome everyone. Today I'll walk you through our data platform architecture, focusing on the recent migration to StarRocks and the new ELT pipeline."
    },
    {
      "layout": "section-divider",
      "title": "The Problem"
    },
    {
      "layout": "bullet-list",
      "title": "Legacy Pain Points",
      "body": "• Manual CSV uploads every Monday\n• 48-hour latency on analytics\n• No data quality checks\n• Single point of failure on ETL server",
      "notes": "These pain points were costing us roughly 20 hours per week in manual work and delayed decision-making by 2-3 days."
    },
    {
      "layout": "section-divider",
      "title": "The Solution"
    },
    {
      "layout": "content",
      "title": "Automated ELT Pipeline",
      "body": "Airflow orchestrates extraction from 12 sources, loads into StarRocks staging, transforms to data models with full lineage tracking.",
      "notes": "We chose Airflow over Prefect for its mature operator library and our team's existing experience. StarRocks replaced ClickHouse for its MySQL compatibility."
    },
    {
      "layout": "two-column",
      "title": "Before vs After",
      "left": "Manual uploads\n48hr latency\nNo monitoring\n3 data sources",
      "right": "Automated ELT\n< 1hr latency\nFull observability\n12 data sources"
    },
    {
      "layout": "comparison",
      "title": "Storage Options Evaluated",
      "left_title": "MinIO (Chosen)",
      "left": "S3-compatible\nSelf-hosted, no egress costs\nIntegrates with StarRocks backup",
      "right_title": "AWS S3",
      "right": "Managed service\nEgress costs add up\nRequires VPN for on-prem"
    },
    {
      "layout": "section-divider",
      "title": "Results"
    },
    {
      "layout": "bullet-list",
      "title": "Impact After 3 Months",
      "body": "• Analytics latency: 48hrs → 45min\n• Manual work: 20hrs/week → 2hrs/week\n• Data sources: 3 → 12\n• Zero data incidents",
      "notes": "The ROI calculation shows we recovered the implementation cost within the first quarter."
    },
    {
      "layout": "closing",
      "title": "Questions?",
      "subtitle": "Data Platform Team",
      "contact": "data-platform@company.com"
    }
  ]
}
```

**Step 2: Generate PPTX**

```bash
cd ~/repos/diagram-generation-plugin
python3 skills/presentation-creator/scripts/create_pptx.py \
  /tmp/test-full-spec.json /tmp/test-full-presentation.pptx
```

Expected: `Saved /tmp/test-full-presentation.pptx (10 slides)`

**Step 3: Verify slides and speaker notes**

```bash
python3 -c "
from pptx import Presentation
p = Presentation('/tmp/test-full-presentation.pptx')
for i, s in enumerate(p.slides):
    texts = [sh.text for sh in s.shapes if sh.has_text_frame]
    title = texts[0][:60] if texts else '(empty)'
    has_notes = bool(s.notes_slide.notes_text_frame.text) if s.has_notes_slide else False
    print(f'Slide {i+1}: {title} [notes: {has_notes}]')
print(f'Total: {len(p.slides)} slides')
"
```

Expected: 10 slides, speaker notes on slides 1, 3, 5, 9.

**Step 4: Push**

```bash
git push origin main
```
