# Known Visual Issues

Issues that visual review catches but programmatic validators miss. Each entry records when it was first seen, how many times, and whether a validator check has been added.

## Format

```
### [gap_type]
- **First seen:** iteration N
- **Occurrences:** N
- **Status:** open | validator_added | generation_rule_added
- **Description:** What the issue looks like visually
- **Suggested check:** How to detect programmatically
```

## Issues

### zone_label_lost
- **First seen:** iteration 1
- **Occurrences:** 14 (iter 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 13, 16, 18, 19)
- **Status:** open (DrawIO conversion issue, not fixable in SVG validator)
- **Description:** Zone labels (e.g., "PUBLIC SUBNET", "CLIENTS") are present in SVG source but get truncated or lost during DrawIO conversion. Renders show partial text like "NTS" instead of "CLIENTS" or "TE SUBNET" instead of "PRIVATE SUBNET".
- **Suggested check:** validate_drawio.py should compare zone label count/text between source HTML and DrawIO output. Zone labels positioned near box edges are most vulnerable.

### legend_conversion_artifact
- **First seen:** iteration 1
- **Occurrences:** 1
- **Status:** open
- **Description:** Legend items using small color swatches (12x12 rect) with adjacent text get misinterpreted during DrawIO conversion, appearing as clipped floating text between diagram boxes.
- **Suggested check:** validate_drawio.py should detect small rects (<20px) with adjacent text and ensure they convert as legend items.

### box_outside_zone
- **First seen:** iteration 4
- **Occurrences:** 1
- **Status:** validator_added (check_box_containment in validate_svg.py, batch 1)
- **Description:** Component box positioned below its intended zone boundary, appearing visually disconnected. In iter-4, Reports box at y=560 fell below Reporting zone ending at y=535.
- **Suggested check:** Geometric containment check - all component rects must be fully inside at least one zone rect.

### arrow_label_collision
- **First seen:** iteration 6
- **Occurrences:** 2 (iter 6, 10)
- **Status:** generation_rule_added (Rules 4+5) + validator_added (check_label_density, batch 2)
- **Description:** Arrow annotation badges placed ON arrow paths or too close to component boxes get merged/absorbed during DrawIO conversion. Multiple badges between same boxes create unreadable clusters.
- **Suggested check:** check_label_density detects badge clustering at SVG level. DrawIO conversion proximity is harder to detect programmatically.

### zone_label_confusion
- **First seen:** iteration 8
- **Occurrences:** 1
- **Status:** open
- **Description:** In nested zone layouts, inner zone labels (e.g., "VPC 10.0.0.0/16") blend with component box labels, especially when zone label text is same style/size as box text.
- **Suggested check:** Zone labels should use different font weight, style, or size than component labels.

### indistinguishable_dashes
- **First seen:** iteration 7
- **Occurrences:** 1
- **Status:** generation_rule_added (Rule 6)
- **Description:** Dashed arrows with thin stroke-width on colored zone backgrounds become hard to distinguish from solid lines. Purple dashes on blue zone particularly affected.
- **Suggested check:** Check stroke-width of dashed lines >= 2.5 and stroke color has sufficient contrast against zone fill.

### crammed_text
- **First seen:** iteration 10
- **Occurrences:** 1
- **Status:** generation_rule_added (Rule 5)
- **Description:** Too many annotation badges in a single inter-box gap create an unreadable text cluster. In iter-10, 6 badges between boxes created visual noise.
- **Suggested check:** Count annotation rects per inter-box gap, flag if > 2.
