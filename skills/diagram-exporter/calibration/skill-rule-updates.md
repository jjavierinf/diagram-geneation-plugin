# Skill Rule Updates

Generation rules learned from calibration iterations. These feed back into `diagram-standards.md` and the `architecture-diagram-creator` skill.

## Format

Each rule has:
- **Source:** iteration(s) where the gap was observed
- **Category:** zone_style | text_layout | arrow_routing | color_scheme | spacing
- **Rule:** what to always/never do
- **Before/After:** example of bad vs good

## Rules

### Rule 1: Boxes must have margin inside zones
- **Source:** iteration 4 (box_outside_zone)
- **Category:** spacing
- **Rule:** Every component box must be positioned at least 20px inside its zone rect boundary on all sides. Never let a box touch or exceed zone edges.
- **Before:** Zone y=425, h=110 (ends at 535), box at y=560 → box outside zone
- **After:** Zone y=425, h=200 (ends at 625), box at y=560 → box safely inside

### Rule 2: Zone labels need clear space
- **Source:** iterations 1, 2, 4, 5 (zone_label_lost)
- **Category:** zone_style
- **Rule:** Position zone labels at the TOP of the zone with at least 30px vertical clearance before any component box. Place label at (zone.x + 20, zone.y + 25). Never position a component box within 40px of the zone label.
- **Before:** Zone label at y=55, first box at y=60 → label gets occluded/clipped in conversion
- **After:** Zone label at y=48, first box at y=80 → clear separation preserved

### Rule 3: Legend uses larger swatches
- **Source:** iteration 1 (legend_conversion_artifact)
- **Category:** zone_style
- **Rule:** Legend color swatches should be at least 20x20px (not 12x12). Larger swatches survive DrawIO conversion better and are more visible.
- **Before:** `<rect width="12" height="12"/>` → too small, gets lost in conversion
- **After:** `<rect width="20" height="20"/>` → survives conversion cleanly

### Rule 4: Arrow annotation badges need vertical offset
- **Source:** iterations 6, 10 (arrow_label_collision)
- **Category:** text_layout
- **Rule:** Arrow label badges (rect+text) must be positioned at least 15px ABOVE or BELOW the arrow path, never ON the path. When multiple annotations exist between the same pair of boxes, stack them vertically with 10px gaps.
- **Before:** Badge at same y as arrow path → badge gets crossed by arrow and merged in conversion
- **After:** Badge 15px above arrow → clearly separated, survives conversion

### Rule 5: Limit annotations per gap
- **Source:** iteration 10 (crammed_text)
- **Category:** text_layout
- **Rule:** Maximum 2 annotation badges between any pair of adjacent boxes. If more context needed, use a separate note or expand box spacing. Never stack 3+ badges in the same inter-box gap.
- **Before:** 3 badges (format, volume, frequency) between Kafka and Spark → unreadable cluster
- **After:** 1 combined badge "Avro / 5K/min" or wider spacing

### Rule 6: Use stroke-width >= 2.5 for dashed lines
- **Source:** iteration 7 (indistinguishable_dashes)
- **Category:** arrow_routing
- **Rule:** Dashed and dotted lines must use stroke-width >= 2.5 to remain distinguishable against zone backgrounds. Use contrasting stroke colors (not similar to zone fill).
- **Before:** `stroke-width="1.5" stroke="#667eea"` on blue zone → faint, hard to see
- **After:** `stroke-width="2.5" stroke="#667eea"` → clearly visible dashes

### Rule 7: Nested zones need 50px+ vertical clearance
- **Source:** iterations 8, 14 (zone_label_confusion)
- **Category:** spacing
- **Rule:** In nested zone layouts, each zone level needs at least 50px between the zone top edge and the first child element. Inner zones should have their label clearly separated from parent zone labels. Never nest more than 3 zone levels deep.
- **Before:** Outer zone label at y=48, inner zone starts at y=50 → labels collide
- **After:** Outer zone label at y=48, inner zone starts at y=90 → clear separation

### Rule 8: Hierarchy layouts need wider horizontal spacing
- **Source:** iteration 14 (crammed_text in hierarchy)
- **Category:** spacing
- **Rule:** In tree/hierarchy layouts, sibling boxes at the same level need at least 40px horizontal gap. Parent-to-child connections should use generous vertical spacing (100px+) to leave room for arrow labels.
- **Before:** 2 team boxes with 10px gap, labels "leads | leads" overlapping → unreadable
- **After:** 2 team boxes with 60px gap, labels placed cleanly above each arrow
