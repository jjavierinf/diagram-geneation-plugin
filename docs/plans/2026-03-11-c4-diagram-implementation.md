# C4 Diagram Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add C4 model diagram support (Context, Container, Component) to the architecture-diagram-creator skill, with semantic validation and native C4 DrawIO export.

**Architecture:** C4 metadata embedded as `data-c4-*` attributes on SVG elements. Invisible to browser rendering but read by `validate_svg.py --c4` for semantic validation and by `svg2drawio.py` for native C4 `<object>` export. Three HTML templates (one per C4 level) in the creator skill.

**Tech Stack:** Python 3, XML/SVG, Draw.io XML format, existing validate_svg.py + svg2drawio.py

**Repo:** `~/repos/diagram-generation-plugin`

---

### Task 1: C4 Reference Document

**Files:**
- Create: `skills/architecture-diagram-creator/references/c4_reference.md`

**Step 1: Write the C4 reference**

```markdown
# C4 Model Reference

## Levels

### Level 1: System Context
- Shows: your system + users + external systems it talks to
- Elements: Person, Software System, External System
- NO technology details, NO internal structure

### Level 2: Container
- Shows: containers (apps, DBs, queues) inside ONE system
- Elements: Container, Container DB, Person, External System
- Includes: technology on each container and relationship

### Level 3: Component
- Shows: components inside ONE container
- Elements: Component, other Containers, Person, External System
- Includes: technology on each component

## Required Metadata Per Element

| Element | Name | Type Label | Technology | Description |
|---------|------|-----------|------------|-------------|
| Person | yes | "Person" | no | yes |
| Software System | yes | "Software System" | no | yes |
| Container | yes | "Container" | **yes** | yes |
| Container DB | yes | "Container" | **yes** | yes |
| Component | yes | "Component" | **yes** | yes |
| Relationship | label (verb phrase) | -- | yes (container-to-container) | -- |

## Color Scheme (de facto C4-PlantUML)

| Element | Internal Fill | External Fill | Font |
|---------|--------------|---------------|------|
| Person | #08427B | #686868 | white |
| Software System | #1168BD | #999999 | white |
| Container | #438DD5 | #B3B3B3 | white |
| Component | #85BBF0 | #CCCCCC | black |
| Boundary | transparent | -- | #444444 (dashed #666666 border) |
| Relationship | #666666 line | -- | #666666 text |

## SVG data-c4-* Convention

Diagram level on SVG root:
- `data-c4-level="context|container|component"`
- `data-c4-scope="System Name"`

Element types on rects:
- `data-c4-type="person|external-person|software-system|external-system|container|container-db|external-container|component|external-component|boundary"`
- `data-c4-name="Element Name"`
- `data-c4-description="Short description"`
- `data-c4-technology="Tech, Framework"` (containers and components only)

Relationships on paths/lines:
- `data-c4-label="Verb phrase"`
- `data-c4-technology="Protocol"` (container-to-container)

## Diagram Title Format

"[Type] diagram for [Scope]"
- "System Context diagram for Internet Banking"
- "Container diagram for Internet Banking"
- "Component diagram for Web Application"

## Common Mistakes to Avoid

1. Don't mix levels (no components in a context diagram)
2. Don't use single-word labels ("Uses") — be specific ("Sends emails using SMTP")
3. Don't show internals of external systems
4. Containers are runtime things (apps, DBs) — NOT JARs or DLLs
5. Always include a legend
6. External elements MUST be visually distinct (gray, not blue)
```

**Step 2: Commit**

```bash
git add skills/architecture-diagram-creator/references/c4_reference.md
git commit -m "docs: add C4 model reference for diagram creator"
```

---

### Task 2: C4 Context Template

**Files:**
- Create: `skills/architecture-diagram-creator/assets/templates/c4_context.html`

**Step 1: Create the template**

Build an HTML file following `base_template.html` CSS structure. The SVG section should have:
- `<svg data-c4-level="context" data-c4-scope="[SYSTEM_NAME]" viewBox="0 0 1200 800">`
- Central system box: `<rect data-c4-type="software-system" data-c4-name="[SYSTEM_NAME]" data-c4-description="[DESC]" ... fill="#1168BD"/>`
- Persons above: `<rect data-c4-type="person" data-c4-name="[USER]" data-c4-description="[DESC]" ... fill="#08427B"/>` with person icon text or silhouette
- External systems around: `<rect data-c4-type="external-system" data-c4-name="[EXT]" data-c4-description="[DESC]" ... fill="#999999"/>`
- Arrows with: `data-c4-label="[verb phrase]"` stroke="#666666"
- Legend at bottom with Person/System/External System swatches
- Title h2: "[Type] diagram for [Scope]"

Key layout:
```
          [Person 1]    [Person 2]
               \           /
                \         /
          [External] ← [SYSTEM] → [External]
                        |
                  [External DB]
```

Element text pattern (inside each rect, multi-line tspan):
```
Line 1: Name (bold, 13px)
Line 2: [Type] (11px, lighter)
Line 3: Description (10px)
```

**Step 2: Validate template renders correctly**

```bash
python3 skills/diagram-exporter/scripts/validate_svg.py \
  skills/architecture-diagram-creator/assets/templates/c4_context.html
```

Expected: PASS or WARN (no FAIL)

**Step 3: Commit**

```bash
git add skills/architecture-diagram-creator/assets/templates/c4_context.html
git commit -m "feat: add C4 System Context template"
```

---

### Task 3: C4 Container Template

**Files:**
- Create: `skills/architecture-diagram-creator/assets/templates/c4_container.html`

**Step 1: Create the template**

Same CSS as base_template.html. SVG section:
- `<svg data-c4-level="container" data-c4-scope="[SYSTEM_NAME]" viewBox="0 0 1400 900">`
- Dashed boundary rect: `<rect data-c4-type="boundary" data-c4-name="[SYSTEM_NAME]" ... fill="none" stroke="#666666" stroke-dasharray="8,4"/>`
- Container boxes inside boundary: `<rect data-c4-type="container" data-c4-name="Web App" data-c4-technology="Java, Spring" data-c4-description="Delivers content" ... fill="#438DD5"/>`
- Container DB: `<rect data-c4-type="container-db" data-c4-name="Database" data-c4-technology="PostgreSQL" data-c4-description="Stores data" ... fill="#438DD5"/>` (use rx=0, different visual — taller, narrower with "[Container: PostgreSQL]" label)
- Persons and external systems outside boundary (same as context template fills)
- Arrows with `data-c4-label` and `data-c4-technology` for container-to-container

Element text pattern for containers:
```
Line 1: Name (bold, 13px)
Line 2: [Container: Technology] (10px)
Line 3: Description (10px)
```

**Step 2: Validate**

```bash
python3 skills/diagram-exporter/scripts/validate_svg.py \
  skills/architecture-diagram-creator/assets/templates/c4_container.html
```

**Step 3: Commit**

```bash
git add skills/architecture-diagram-creator/assets/templates/c4_container.html
git commit -m "feat: add C4 Container template"
```

---

### Task 4: C4 Component Template

**Files:**
- Create: `skills/architecture-diagram-creator/assets/templates/c4_component.html`

**Step 1: Create the template**

Same pattern. SVG:
- `<svg data-c4-level="component" data-c4-scope="[CONTAINER_NAME]" viewBox="0 0 1400 900">`
- Dashed boundary for the container in scope
- Component boxes: `fill="#85BBF0"` (pale blue, black font)
- Other containers from same system shown as external blue boxes outside boundary
- External systems in gray

Element text pattern for components:
```
Line 1: Name (bold, 12px)
Line 2: [Component: Technology] (10px)
Line 3: Description (9px)
```

**Step 2: Validate**

```bash
python3 skills/diagram-exporter/scripts/validate_svg.py \
  skills/architecture-diagram-creator/assets/templates/c4_component.html
```

**Step 3: Commit**

```bash
git add skills/architecture-diagram-creator/assets/templates/c4_component.html
git commit -m "feat: add C4 Component template"
```

---

### Task 5: C4 Validation Checks in validate_svg.py

**Files:**
- Modify: `skills/diagram-exporter/scripts/validate_svg.py`

**Step 1: Write test HTML with known C4 issues**

Create `skills/diagram-exporter/tests/test-c4-issues.html` — a deliberately bad C4 diagram:
- One rect with `data-c4-type="container"` but NO `data-c4-technology` (should trigger c4_containers_have_technology)
- One rect with `data-c4-type="software-system"` but no `data-c4-description` (should trigger c4_elements_have_metadata)
- A path with `data-c4-label="Uses"` (should trigger c4_relationships_labeled — too vague)
- `data-c4-level="context"` on SVG but a rect with `data-c4-type="component"` (should trigger c4_level_consistency)
- No boundary rect (should trigger c4_has_boundary if level is container/component)
- No legend (should trigger c4_has_legend)
- Title "My Diagram" not matching format (should trigger c4_title_format)
- An external-system rect with fill="#1168BD" (blue, should be gray — triggers c4_externals_distinct)

**Step 2: Add C4 detection to parse_svg_elements**

In `parse_svg_elements()`, after parsing the SVG element, also extract `data-c4-*` attributes:

```python
# In the SVG root parsing section:
c4_level = svg_el.get('data-c4-level', '')
c4_scope = svg_el.get('data-c4-scope', '')

# In the rect parsing loop, add to each rect dict:
c4_attrs = {k.replace('data-c4-', 'c4_'): v
            for k, v in el.attrib.items() if k.startswith('data-c4-')}
# Add c4_attrs to the rect dict

# In the path/line parsing, also grab data-c4-label and data-c4-technology

# Add to the returned dict:
# 'c4_level': c4_level, 'c4_scope': c4_scope
```

**Step 3: Write the 8 C4 check functions**

Add after the existing check functions, before ALL_CHECKS:

```python
# ---------------------------------------------------------------------------
# C4 Model Checks (activated with --c4 or auto-detected)
# ---------------------------------------------------------------------------

def check_c4_elements_have_metadata(elements, strict=False):
    """Every data-c4-type element must have name and description."""
    issues = []
    sev = 'fail' if strict else 'warn'
    for r in elements['rects']:
        c4_type = r.get('c4_type', '')
        if not c4_type:
            continue
        if not r.get('c4_name'):
            issues.append({'type': 'c4_missing_name', 'severity': sev,
                           'c4_type': c4_type,
                           'position': f"({r['x']:.0f},{r['y']:.0f})"})
        if c4_type != 'boundary' and not r.get('c4_description'):
            issues.append({'type': 'c4_missing_description', 'severity': sev,
                           'c4_type': c4_type, 'name': r.get('c4_name', '?'),
                           'position': f"({r['x']:.0f},{r['y']:.0f})"})
    return issues


def check_c4_containers_have_technology(elements, strict=False):
    """Containers and components must specify technology."""
    issues = []
    sev = 'fail' if strict else 'warn'
    needs_tech = {'container', 'container-db', 'external-container',
                  'component', 'external-component'}
    for r in elements['rects']:
        c4_type = r.get('c4_type', '')
        if c4_type in needs_tech and not r.get('c4_technology'):
            issues.append({'type': 'c4_missing_technology', 'severity': sev,
                           'c4_type': c4_type, 'name': r.get('c4_name', '?')})
    return issues


def check_c4_relationships_labeled(elements, strict=False):
    """Relationships must have non-empty, specific labels."""
    issues = []
    sev = 'fail' if strict else 'warn'
    vague = {'uses', 'calls', 'sends', 'gets'}
    for item in elements['lines'] + elements['paths']:
        label = item.get('c4_label', '')
        if 'c4_label' in item and not label:
            issues.append({'type': 'c4_empty_relationship_label', 'severity': sev})
        if label.lower().strip() in vague:
            issues.append({'type': 'c4_vague_relationship_label', 'severity': sev,
                           'label': label,
                           'message': f'Too vague — be specific (e.g., "Reads customer data from")'})
    return issues


def check_c4_level_consistency(elements, strict=False):
    """No cross-level mixing (e.g., components in a context diagram)."""
    issues = []
    sev = 'fail' if strict else 'warn'
    level = elements.get('c4_level', '')
    if not level:
        return issues
    c4_types = [r.get('c4_type', '') for r in elements['rects'] if r.get('c4_type')]
    forbidden = {
        'context': {'container', 'container-db', 'component', 'external-container', 'external-component'},
        'container': {'component', 'external-component'},
    }
    banned = forbidden.get(level, set())
    for ct in c4_types:
        if ct in banned:
            issues.append({'type': 'c4_level_violation', 'severity': sev,
                           'level': level, 'found_type': ct,
                           'message': f'"{ct}" should not appear in a {level} diagram'})
    return issues


def check_c4_has_boundary(elements, strict=False):
    """Container/component diagrams need at least one boundary."""
    level = elements.get('c4_level', '')
    if level not in ('container', 'component'):
        return []
    boundaries = [r for r in elements['rects'] if r.get('c4_type') == 'boundary']
    if not boundaries:
        sev = 'fail' if strict else 'warn'
        return [{'type': 'c4_missing_boundary', 'severity': sev,
                 'level': level,
                 'message': f'{level} diagram should have a system/container boundary'}]
    return []


def check_c4_title_format(elements, html_content, strict=False):
    """Title should match '[Type] diagram for [Scope]'."""
    level = elements.get('c4_level', '')
    scope = elements.get('c4_scope', '')
    if not level:
        return []
    expected_types = {
        'context': 'System Context',
        'container': 'Container',
        'component': 'Component',
    }
    expected_prefix = expected_types.get(level, '')
    # Find h2 titles in HTML
    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html_content, re.DOTALL)
    for h2 in h2s:
        clean = re.sub(r'<[^>]+>', '', h2).strip()
        if expected_prefix.lower() in clean.lower() and 'diagram' in clean.lower():
            return []
    sev = 'fail' if strict else 'warn'
    return [{'type': 'c4_title_format', 'severity': sev,
             'expected': f'{expected_prefix} diagram for {scope or "[Scope]"}',
             'message': 'No matching C4 title found in h2 elements'}]


def check_c4_has_legend(elements, strict=False):
    """C4 diagrams must have a legend/key."""
    # Look for legend-like text
    legend_keywords = {'legend', 'key', 'notation'}
    for t in elements['texts']:
        if t['text'].lower().strip() in legend_keywords:
            return []
    # Look for small rects that might be legend swatches (cluster of 3+ tiny rects near bottom)
    bottom_y = elements['height'] * 0.75
    small_bottom = [r for r in elements['rects']
                    if r['y'] > bottom_y and r['w'] < 30 and r['h'] < 30]
    if len(small_bottom) >= 3:
        return []
    sev = 'fail' if strict else 'warn'
    return [{'type': 'c4_missing_legend', 'severity': sev,
             'message': 'C4 diagram should have a key/legend explaining notation'}]


def check_c4_externals_distinct(elements, strict=False):
    """External elements should use gray fills, not blue."""
    issues = []
    sev = 'fail' if strict else 'warn'
    external_types = {'external-person', 'external-system', 'external-container', 'external-component'}
    internal_fills = {'#08427b', '#1168bd', '#438dd5', '#85bbf0'}
    for r in elements['rects']:
        if r.get('c4_type', '') in external_types:
            fill = (r.get('fill', '') or '').lower()
            if fill in internal_fills:
                issues.append({'type': 'c4_external_not_gray', 'severity': sev,
                               'name': r.get('c4_name', '?'),
                               'fill': fill,
                               'message': 'External elements should use gray fills (#686868, #999999, etc.)'})
    return issues
```

**Step 4: Add --c4 and --strict flags to main()**

```python
def main():
    parser = argparse.ArgumentParser(description='Validate SVG diagram quality in HTML files')
    parser.add_argument('html_file', help='Path to HTML file with SVG diagrams')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of human-readable')
    parser.add_argument('--c4', action='store_true', help='Enable C4 semantic checks')
    parser.add_argument('--strict', action='store_true', help='C4 issues become FAIL instead of WARN')
    args = parser.parse_args()
    validate_svg(args.html_file, args.json, c4_mode=args.c4, strict=args.strict)
```

**Step 5: Update validate_svg() to run C4 checks**

In `validate_svg()`, after the standard checks loop:

```python
# Auto-detect C4 mode from SVG attributes
is_c4 = c4_mode or bool(elements.get('c4_level'))

if is_c4:
    c4_checks = [
        check_c4_elements_have_metadata,
        check_c4_containers_have_technology,
        check_c4_relationships_labeled,
        check_c4_level_consistency,
        check_c4_has_boundary,
        check_c4_has_legend,
        check_c4_externals_distinct,
    ]
    for check_fn in c4_checks:
        svg_report['issues'].extend(check_fn(elements, strict=strict))
    # c4_title_format needs html_content
    svg_report['issues'].extend(
        check_c4_title_format(elements, html_content, strict=strict))
```

**Step 6: Run test on bad C4 diagram**

```bash
python3 skills/diagram-exporter/scripts/validate_svg.py \
  skills/diagram-exporter/tests/test-c4-issues.html --c4 --json
```

Expected: WARN status with 8 different c4_* issue types

**Step 7: Run with --strict**

```bash
python3 skills/diagram-exporter/scripts/validate_svg.py \
  skills/diagram-exporter/tests/test-c4-issues.html --c4 --strict --json
```

Expected: FAIL status (all c4 issues escalated)

**Step 8: Regression — run on all existing tests**

```bash
for f in skills/diagram-exporter/tests/test-*.html; do
  echo -n "$(basename $f): "
  python3 skills/diagram-exporter/scripts/validate_svg.py "$f" --json 2>/dev/null | \
    python3 -c "import sys,json; r=json.load(sys.stdin); print(f'{r[\"status\"]}  ({sum(len(s[\"issues\"]) for s in r[\"svgs\"])} issues)')"
done
```

Expected: Same results as before (no regressions). C4 checks should NOT fire on non-C4 diagrams because they check for `c4_type`/`c4_level` which don't exist.

**Step 9: Run on C4 templates**

```bash
python3 skills/diagram-exporter/scripts/validate_svg.py \
  skills/architecture-diagram-creator/assets/templates/c4_context.html --c4
python3 skills/diagram-exporter/scripts/validate_svg.py \
  skills/architecture-diagram-creator/assets/templates/c4_container.html --c4
python3 skills/diagram-exporter/scripts/validate_svg.py \
  skills/architecture-diagram-creator/assets/templates/c4_component.html --c4
```

Expected: PASS or WARN on each (templates are well-formed)

**Step 10: Commit**

```bash
git add skills/diagram-exporter/scripts/validate_svg.py \
  skills/diagram-exporter/tests/test-c4-issues.html
git commit -m "feat: add 8 C4 semantic validation checks (--c4, --strict flags)"
```

---

### Task 6: C4-Aware DrawIO Export in svg2drawio.py

**Files:**
- Modify: `skills/diagram-exporter/scripts/svg2drawio.py`

**Step 1: Add C4 style mapping**

Add after the color helpers section:

```python
# ---------------------------------------------------------------------------
# C4 Draw.io shape mapping
# ---------------------------------------------------------------------------

C4_STYLES = {
    'person': 'shape=mxgraph.c4.person2;whiteSpace=wrap;html=1;fillColor=#08427B;fontColor=#ffffff;align=center;metaEdit=1;resizable=0;',
    'external-person': 'shape=mxgraph.c4.person2;whiteSpace=wrap;html=1;fillColor=#686868;fontColor=#ffffff;align=center;metaEdit=1;resizable=0;',
    'software-system': 'rounded=1;whiteSpace=wrap;html=1;fillColor=#1168BD;fontColor=#ffffff;align=center;arcSize=10;strokeColor=#0E4D92;metaEdit=1;resizable=0;',
    'external-system': 'rounded=1;whiteSpace=wrap;html=1;fillColor=#999999;fontColor=#ffffff;align=center;arcSize=10;strokeColor=#8A8A8A;metaEdit=1;resizable=0;',
    'container': 'rounded=1;whiteSpace=wrap;html=1;fillColor=#438DD5;fontColor=#ffffff;align=center;arcSize=10;strokeColor=#3C7FC0;metaEdit=1;resizable=0;',
    'container-db': 'shape=cylinder3;whiteSpace=wrap;html=1;size=15;fillColor=#438DD5;fontColor=#ffffff;align=center;strokeColor=#3C7FC0;metaEdit=1;resizable=0;',
    'external-container': 'rounded=1;whiteSpace=wrap;html=1;fillColor=#B3B3B3;fontColor=#000000;align=center;arcSize=10;strokeColor=#A6A6A6;metaEdit=1;resizable=0;',
    'component': 'rounded=1;whiteSpace=wrap;html=1;fillColor=#85BBF0;fontColor=#000000;align=center;arcSize=10;strokeColor=#78A8D8;metaEdit=1;resizable=0;',
    'external-component': 'rounded=1;whiteSpace=wrap;html=1;fillColor=#CCCCCC;fontColor=#000000;align=center;arcSize=10;strokeColor=#BFBFBF;metaEdit=1;resizable=0;',
    'boundary': 'rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#666666;dashed=1;dashPattern=8 4;fontColor=#444444;verticalAlign=top;fontStyle=1;fontSize=12;arcSize=6;',
}


def build_c4_label(c4_type, name, technology, description):
    """Build the HTML label for a C4 element using %placeholder% syntax."""
    type_labels = {
        'person': 'Person', 'external-person': 'Person',
        'software-system': 'Software System', 'external-system': 'Software System',
        'container': 'Container', 'container-db': 'Container',
        'external-container': 'Container',
        'component': 'Component', 'external-component': 'Component',
    }
    type_label = type_labels.get(c4_type, c4_type)
    parts = [f'&lt;b&gt;%c4Name%&lt;/b&gt;']
    if technology:
        parts.append(f'&lt;div&gt;[{html_escape(type_label)}: %c4Technology%]&lt;/div&gt;')
    else:
        parts.append(f'&lt;div&gt;[{html_escape(type_label)}]&lt;/div&gt;')
    parts.append('&lt;div&gt;&lt;font style=&quot;font-size:11px&quot;&gt;%c4Description%&lt;/font&gt;&lt;/div&gt;')
    return ''.join(parts)
```

**Step 2: Modify the rect emission loop to detect C4**

In `svg_to_drawio_cells()`, when iterating rects, check for `data-c4-*` on the raw SVG element (`r['el']`). If present, emit `<object>` instead of `<mxCell>`:

```python
# In the component rects loop, before the existing mxCell emission:
c4_type = r['el'].get('data-c4-type', '') if 'el' in r else ''
if c4_type and c4_type in C4_STYLES:
    c4_name = r['el'].get('data-c4-name', '')
    c4_tech = r['el'].get('data-c4-technology', '')
    c4_desc = r['el'].get('data-c4-description', '')
    label = build_c4_label(c4_type, c4_name, c4_tech, c4_desc)
    style = C4_STYLES[c4_type]
    obj_attrs = (f'placeholders="1" c4Name="{xml_attr_escape(c4_name)}" '
                 f'c4Type="{xml_attr_escape(c4_type)}" '
                 f'c4Technology="{xml_attr_escape(c4_tech)}" '
                 f'c4Description="{xml_attr_escape(c4_desc)}"')
    cells.append(
        f'<object {obj_attrs} label="{xml_attr_escape(label)}" id="{rid}">'
        f'<mxCell style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{r["x"]}" y="{r["y"]}" '
        f'width="{r["w"]}" height="{r["h"]}" as="geometry"/>'
        f'</mxCell></object>'
    )
else:
    # existing mxCell code...
```

Same for zone rects — if `data-c4-type="boundary"`, use C4 boundary style.

**Step 3: Test DrawIO export of C4 context template**

```bash
python3 skills/diagram-exporter/scripts/svg2drawio.py \
  skills/architecture-diagram-creator/assets/templates/c4_context.html \
  /tmp/c4-context-test.drawio

python3 skills/diagram-exporter/scripts/validate_drawio.py \
  /tmp/c4-context-test.drawio \
  --source-html skills/architecture-diagram-creator/assets/templates/c4_context.html
```

Expected: PASS/WARN. Verify the .drawio XML contains `<object ... c4Name=...>` elements.

**Step 4: Verify C4 object elements in output**

```bash
grep -c '<object.*c4Name' /tmp/c4-context-test.drawio
```

Expected: > 0 (at least one C4 object element)

**Step 5: Regression — export non-C4 test**

```bash
python3 skills/diagram-exporter/scripts/svg2drawio.py \
  skills/diagram-exporter/tests/test-01-simple-flow.html \
  /tmp/regression-test.drawio
```

Expected: Works as before (no `<object>` elements, all `<mxCell>`)

**Step 6: Commit**

```bash
git add skills/diagram-exporter/scripts/svg2drawio.py
git commit -m "feat: C4-native DrawIO export with <object> and C4 shape styles"
```

---

### Task 7: Update SKILL.md Files

**Files:**
- Modify: `skills/architecture-diagram-creator/SKILL.md`
- Modify: `skills/diagram-exporter/SKILL.md`

**Step 1: Update architecture-diagram-creator SKILL.md**

Add a C4 section after the existing workflow:

```markdown
## C4 Model Diagrams

Create C4 diagrams (Context, Container, Component) with semantic metadata.

### When to Use C4 Mode
- "Create C4 diagram for [system]"
- "Show system context / containers / components"
- "C4 architecture diagram"

### Workflow

1. Determine C4 level from user request:
   - **Context** (L1): "who uses this system and what does it talk to?"
   - **Container** (L2): "what apps/DBs/services make up this system?"
   - **Component** (L3): "what are the parts inside this container?"
2. Pick template from `assets/templates/c4_[level].html`
3. Fill in elements with `data-c4-*` attributes (see `references/c4_reference.md`)
4. Run `validate_svg.py --c4` to check C4 semantic rules
5. Export to DrawIO (native C4 shapes) and/or PPTX (screenshots)

### C4 Color Scheme

| Internal | External |
|----------|----------|
| Person: #08427B | #686868 |
| System: #1168BD | #999999 |
| Container: #438DD5 | #B3B3B3 |
| Component: #85BBF0 | #CCCCCC |

### C4 Element Text Pattern

Each box has 3 lines:
1. **Name** (bold)
2. [Type: Technology] (or just [Type])
3. Description (smaller font)
```

**Step 2: Update diagram-exporter SKILL.md**

In the validation pipeline section, add:

```markdown
### C4 Semantic Validation

When exporting C4 diagrams (detected by `data-c4-level` on SVG), additional checks run:

\`\`\`bash
# Pragmatic mode (default)
python3 $SKILL/scripts/validate_svg.py c4-diagram.html --c4

# Strict compliance
python3 $SKILL/scripts/validate_svg.py c4-diagram.html --c4 --strict
\`\`\`

8 C4-specific checks: element metadata, technology on containers, relationship labels, level consistency, boundaries, title format, legend, external color distinction.

DrawIO export automatically generates native C4 `<object>` elements when `data-c4-*` attributes are detected.
```

**Step 3: Commit**

```bash
git add skills/architecture-diagram-creator/SKILL.md \
  skills/diagram-exporter/SKILL.md
git commit -m "docs: update SKILL.md files with C4 workflow and validation docs"
```

---

### Task 8: End-to-End Smoke Test

**Files:** (no new files, just verification)

**Step 1: Generate → Validate → Export full cycle**

```bash
SKILL=~/repos/diagram-generation-plugin/skills

# Validate C4 context template
python3 $SKILL/diagram-exporter/scripts/validate_svg.py \
  $SKILL/architecture-diagram-creator/assets/templates/c4_context.html --c4 --json

# Export to DrawIO
python3 $SKILL/diagram-exporter/scripts/svg2drawio.py \
  $SKILL/architecture-diagram-creator/assets/templates/c4_context.html \
  /tmp/c4-final.drawio

# Validate DrawIO
python3 $SKILL/diagram-exporter/scripts/validate_drawio.py \
  /tmp/c4-final.drawio \
  --source-html $SKILL/architecture-diagram-creator/assets/templates/c4_context.html

# Verify C4 native objects
grep -c 'c4Name' /tmp/c4-final.drawio
```

**Step 2: Export to PPTX**

```bash
python3 $SKILL/diagram-exporter/scripts/svg2pptx.py \
  $SKILL/architecture-diagram-creator/assets/templates/c4_context.html \
  /tmp/c4-context.pptx
```

Expected: Validation passes, PPTX generated with slides.

**Step 3: Full regression on existing tests**

```bash
for f in $SKILL/diagram-exporter/tests/test-*.html; do
  echo -n "$(basename $f): "
  python3 $SKILL/diagram-exporter/scripts/validate_svg.py "$f" --json 2>/dev/null | \
    python3 -c "import sys,json; r=json.load(sys.stdin); print(f'{r[\"status\"]}  ({sum(len(s[\"issues\"]) for s in r[\"svgs\"])} issues)')"
done
```

Expected: Same status/issue counts as before.

**Step 4: Commit test results**

```bash
git add -A
git commit -m "test: end-to-end C4 pipeline smoke test passed"
```
