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

Write the slide spec as JSON to `current_task/slides-spec.json`, then run:

```bash
python3 $SKILL/scripts/create_pptx.py current_task/slides-spec.json output.pptx [--template path/to/custom.pptx]
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

### 7. Deliver

Tell the user where the PPTX file is saved. If the user provided a custom template via `--template`, mention it was used.

## Template

Default template: `$SKILL/assets/templates/default.pptx`

The user can provide their own .pptx template via `--template`. The script builds all layouts from scratch using shapes on the Blank layout — the template provides slide dimensions and base styling.

To replace the default template, drop a .pptx file at `$SKILL/assets/templates/default.pptx`.

## Important

- Do NOT use the `diagram-exporter` skill's `svg2pptx.py` — that creates single-diagram slides. This skill creates full narrative presentations.
- Keep slides concise. The presentation should work even if someone only reads the slides without speaker notes.
- If using `technical-discovery` to gather context, run it first, then use the output to plan the narrative.
- If the user does not specify a topic clearly, ask ONE question: "What is the key message of this presentation?"
