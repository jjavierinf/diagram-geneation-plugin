# Design: Presentation Creator Skill

**Date:** 2026-03-11
**Status:** Approved
**Repo:** diagram-generation-plugin

## Problem

The plugin can create architecture diagrams and export them to PPTX, but only as screenshot-based single slides. There is no way to generate a full, multi-slide presentation that tells a story — with narrative structure, proper layouts, concise text, speaker notes, and embedded diagrams.

## Decision

A new `presentation-creator` skill that generates complete PPTX presentations using python-pptx with a pre-designed template. The skill infers the presentation type from the user's request and applies an appropriate storytelling framework.

## Pipeline

```
User prompt
  │
  ├─ 1. Narrative Planning
  │   Infer storytelling framework from context:
  │   - Technical/architecture → pyramid (conclusion first)
  │   - Proposal/pitch → situation-complication-resolution
  │   - Status update → what-so what-now what
  │   - General → problem-solution-benefit
  │   Output: ordered list of ideas, one per slide
  │
  ├─ 2. Slide Design
  │   Assign layout type to each slide from fixed vocabulary:
  │   title, section-divider, text-left, text-right,
  │   two-column, bullet-list, diagram, comparison, quote, closing
  │   (~10-12 types, all pre-designed in the template)
  │
  ├─ 3. Content Generation
  │   - Body text: max 40 words per slide
  │   - Titles: max 8 words
  │   - Speaker notes: full detail and talking points
  │   - One idea per slide
  │
  ├─ 4. Visual Assets
  │   Only diagrams from diagram-creator / diagram-exporter.
  │   Rendered as PNG via Puppeteer, embedded in slides.
  │   No external images (Unsplash, AI generation, etc.)
  │
  └─ 5. PPTX Assembly
      python-pptx loads template .pptx
      Maps each slide to the corresponding layout
      Fills placeholders (title, body, image, notes)
      Output: .pptx file
```

## Template System

- **Default:** open-source template packaged at `assets/templates/default.pptx`
- **Replaceable:** user can swap in their own .pptx template
- **Requirement:** template must have slide layouts that match the vocabulary (title, section-divider, text-left, etc.)
- **Fallback:** if a layout name is missing from the template, use a generic layout
- Layout matching: by layout name in the slide master. The script maps vocabulary names to layout names.

## Layout Vocabulary

| Layout | Use case | Placeholders |
|--------|----------|-------------|
| `title` | First slide | title, subtitle |
| `section-divider` | Section transitions | title |
| `text-left` | Text with image right | title, body, image |
| `text-right` | Image with text right | title, body, image |
| `two-column` | Side-by-side comparison | title, left-body, right-body |
| `bullet-list` | Key points | title, body (bullets) |
| `diagram` | Full diagram slide | title, image |
| `comparison` | Before/after, option A/B | title, left-title, left-body, right-title, right-body |
| `quote` | Key quote or callout | quote-text, attribution |
| `closing` | Last slide | title, subtitle, contact |

## Storytelling Frameworks

The skill picks one based on context. The user can also specify.

| Framework | Structure | Best for |
|-----------|-----------|----------|
| Pyramid | Conclusion → arguments → evidence | Technical, executive |
| SCR | Situation → complication → resolution | Proposals, pitches |
| What-So What-Now What | Data → implications → action | Status updates, analytics |
| Problem-Solution-Benefit | Problem → fix → value | General |

## Integration

| Skill | Role |
|-------|------|
| `technical-discovery` | Feeds content when source is code/docs |
| `architecture-diagram-creator` | Generates diagrams embedded as "diagram" slides |
| `diagram-exporter` (svg2pptx.py) | Renders HTML diagrams to PNG for embedding |

## Files to Create

| File | Purpose |
|------|---------|
| `skills/presentation-creator/SKILL.md` | Skill instructions |
| `skills/presentation-creator/assets/templates/default.pptx` | Default template |
| `skills/presentation-creator/scripts/create_pptx.py` | PPTX assembly script |

## Files to Modify

| File | Changes |
|------|---------|
| (none) | This is a new skill, no modifications to existing files |

## Design Rules (enforced by SKILL.md)

- Max 40 words per slide body
- Max 8 words per title
- One idea per slide
- Speaker notes hold the full detail
- Diagrams only from own pipeline (no external images)
- Template is replaceable but default ships with skill
