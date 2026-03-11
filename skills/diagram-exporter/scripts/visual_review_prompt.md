# Visual Diagram Review

Review this rendered diagram image. Fill the checklist below with PASS/FAIL per item, provide a 1-10 score, and list specific issues with locations.

## Checklist

### Text Quality
- [ ] All text fits inside its box (no overflow, no clipping)
- [ ] Text is readable (not too small, not pixelated)
- [ ] No text overlapping other text
- [ ] Labels are concise (no paragraphs crammed into boxes)
- [ ] Font sizes are consistent (headers bigger, details smaller, max 3 sizes)

### Arrow Quality
- [ ] Arrows connect to correct boxes (endpoints touch box edges)
- [ ] No arrows crossing through unrelated boxes
- [ ] Multiple arrows to same box are SPACED, not stacked on same point
- [ ] Arrow labels (if any) are readable and positioned near the arrow
- [ ] Dashed vs solid lines are visually distinguishable
- [ ] No arrows making unnecessary detours or U-turns

### Layout Quality
- [ ] Boxes aligned on a grid (not randomly scattered)
- [ ] Consistent spacing between elements at same level
- [ ] Good use of space (no giant empty regions, no cramped areas)
- [ ] Symmetry where appropriate (parallel paths look parallel)
- [ ] Clear flow direction (left-to-right OR top-to-bottom, not mixed)
- [ ] Related elements grouped visually (zones/swimlanes if applicable)

### Visual Polish
- [ ] Color palette is consistent and professional (not rainbow)
- [ ] Font colors readable against backgrounds (dark on light, white on dark)
- [ ] No visual artifacts or rendering glitches
- [ ] Professional appearance - would you put this in a presentation?

## BAD Examples (flag these immediately)

These are common defects that should cause a score deduction:

- **Converging arrows**: 3+ arrows arriving at the exact same point on a box edge, creating a visual mess. They should be spaced along the edge.
- **Clipped text**: Text cut off at box edges ("Processin..." or text peeking above/below the box).
- **Overflow labels**: Long text that visually extends beyond its container.
- **Lopsided layout**: All content crammed to one side with giant empty space on the other.
- **Arrow spaghetti**: Arrows making unnecessary bends, loops, or crossing multiple boxes.
- **Invisible text**: White text on white/light background, or dark text on dark background.
- **Orphan elements**: Boxes or text floating disconnected from the rest of the diagram.
- **Inconsistent sizing**: Similar components with wildly different box sizes for no reason.

## GOOD Examples (these earn points)

- Boxes in neat rows/columns with even spacing
- Arrows that take the shortest clean path
- Zone containers that clearly group related components
- Legend explaining colors and line styles
- Consistent left-to-right or top-to-bottom flow
- Labels that are short but descriptive (noun + qualifier, not sentences)

## Scoring Rubric

| Score | Meaning | Criteria |
|-------|---------|----------|
| 9-10 | Publication ready | All checklist items pass. Could go directly into a presentation or wiki. |
| 7-8 | Good | 1-2 minor cosmetic issues. Readable, professional, minor alignment tweaks needed. |
| 5-6 | Usable | Noticeable problems (some text overflow, spacing issues) but information is conveyed. |
| 3-4 | Significant issues | Multiple readability problems: overlapping text, messy arrows, poor layout. |
| 1-2 | Unusable | Major rendering failures, missing content, illegible text, broken layout. |

## Response Format

```
SCORE: X/10

CHECKLIST:
[x] or [ ] for each item above

ISSUES (specific, with location):
1. [SEVERITY] Description - "box name" or "arrow from X to Y"
2. ...

SUMMARY: One sentence overall assessment.
```
