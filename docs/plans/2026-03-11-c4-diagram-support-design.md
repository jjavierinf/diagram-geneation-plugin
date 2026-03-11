# Design: C4-Aware Diagram Pipeline

**Date:** 2026-03-11
**Status:** Approved
**Repo:** diagram-generation-plugin

## Context

The `architecture-diagram-creator` skill generates HTML/SVG architecture diagrams. The `diagram-exporter` skill exports them to PPTX (screenshot-based) and DrawIO (editable). We want to add C4 model support (Context, Container, Component levels) as a mode of the existing creator skill, reusing the full validation and export pipeline.

## Decision: Approach B — C4-Aware Pipeline

Embed C4 metadata in SVG elements via `data-c4-*` attributes. These are invisible to browser rendering but enable:
- Semantic validation (`validate_svg.py --c4`)
- Native C4 DrawIO export (`<object>` with c4Name, c4Type, c4Technology, c4Description)
- PPTX export unchanged (screenshot-based)

## Architecture

```
User prompt ("create C4 container diagram for X")
  │
  ├─ architecture-diagram-creator (SKILL.md detects "C4")
  │   ├─ Picks C4 template (c4_context/c4_container/c4_component)
  │   ├─ Generates HTML/SVG with data-c4-* attributes on elements
  │   └─ Outputs: diagrams/my-system-containers.html
  │
  ├─ Stage 1: validate_svg.py --c4 [--strict]
  │   ├─ Standard 11 checks (text bounds, arrows, spacing, etc.)
  │   └─ +8 C4 semantic checks (metadata, technology, level consistency, etc.)
  │
  ├─ Export DrawIO: svg2drawio.py (detects data-c4-*)
  │   ├─ Generates <object> with C4 metadata (not plain <mxCell>)
  │   ├─ Uses C4 shape styles (person2, cylinder3, dashed boundaries)
  │   └─ Output is editable with draw.io's native C4 plugin
  │
  └─ Export PPTX: svg2pptx.py (no changes needed)
      └─ Screenshots HTML as-is (data-c4-* invisible to render)
```

## SVG C4 Metadata Convention

### Diagram level (on SVG root)

```html
<svg data-c4-level="context|container|component" data-c4-scope="System Name" ...>
```

### Element types

| C4 Element | data-c4-type | Required attributes |
|------------|-------------|-------------------|
| Person | `person` | name, description |
| Person (external) | `external-person` | name, description |
| Software System | `software-system` | name, description |
| Software System (ext) | `external-system` | name, description |
| Container | `container` | name, description, technology |
| Container DB | `container-db` | name, description, technology |
| Container (ext) | `external-container` | name, description, technology |
| Component | `component` | name, description, technology |
| Component (ext) | `external-component` | name, description, technology |
| Boundary | `boundary` | name |

### Relationships (on path/line elements)

```html
<path data-c4-label="Reads from" data-c4-technology="JDBC" .../>
```

## C4 Color Scheme (de facto C4-PlantUML)

| Element | Fill | Font | External variant |
|---------|------|------|-----------------|
| Person | `#08427B` | white | `#686868` |
| Software System | `#1168BD` | white | `#999999` |
| Container | `#438DD5` | white | `#B3B3B3` |
| Component | `#85BBF0` | black | `#CCCCCC` |
| Boundary | transparent | `#444444` | dashed `#666666` |
| Relationship | line `#666666` | text `#666666` | — |

## Validation: `--c4` Flag

8 new checks added to `validate_svg.py`:

| Check | What | Default | Strict |
|-------|------|---------|--------|
| `c4_elements_have_metadata` | All data-c4-type rects have name + description | WARN | FAIL |
| `c4_containers_have_technology` | Containers/components have data-c4-technology | WARN | FAIL |
| `c4_relationships_labeled` | Paths with data-c4-label are non-empty, not "Uses" | WARN | FAIL |
| `c4_level_consistency` | No level mixing (e.g., components in context diagram) | WARN | FAIL |
| `c4_has_boundary` | Container/component diagrams have >= 1 boundary | WARN | FAIL |
| `c4_title_format` | Title matches "[Type] diagram for [Scope]" | WARN | FAIL |
| `c4_has_legend` | Legend/key present | WARN | FAIL |
| `c4_externals_distinct` | External elements use gray fills, not blue | WARN | FAIL |

Usage: `python3 validate_svg.py diagram.html --c4` or `--c4 --strict`

Auto-detected: if SVG has `data-c4-level` attribute, `--c4` mode activates automatically.

## DrawIO C4 Export

When `svg2drawio.py` detects `data-c4-*` attributes, it generates:

```xml
<object placeholders="1" c4Name="Web API" c4Type="Container"
        c4Technology="Python, FastAPI"
        c4Description="Serves REST endpoints"
        label="&lt;b&gt;%c4Name%&lt;/b&gt;&lt;div&gt;[%c4Type%: %c4Technology%]&lt;/div&gt;&lt;div&gt;%c4Description%&lt;/div&gt;">
  <mxCell style="rounded=1;whiteSpace=wrap;html=1;fillColor=#438DD5;fontColor=#ffffff;
                  align=center;arcSize=10;strokeColor=#3C7FC0;metaEdit=1;resizable=0;"
          vertex="1" parent="1">
    <mxGeometry x="100" y="200" width="240" height="120" as="geometry"/>
  </mxCell>
</object>
```

Shape mapping:
- Person → `shape=mxgraph.c4.person2`
- Container DB → `shape=cylinder3;size=15`
- Boundary → `dashed=1;dashPattern=8 4;strokeColor=#666666`

## Templates

Three new templates in `assets/templates/`:

- `c4_context.html` — System in center (blue), persons above, external systems around (gray)
- `c4_container.html` — Dashed system boundary, containers inside (blue), externals outside (gray)
- `c4_component.html` — Dashed container boundary, components inside (pale blue), other containers outside

All follow the existing `base_template.html` CSS structure with C4-specific SVG sections.

## Files to Create

| File | Purpose |
|------|---------|
| `assets/templates/c4_context.html` | Level 1 template |
| `assets/templates/c4_container.html` | Level 2 template |
| `assets/templates/c4_component.html` | Level 3 template |
| `references/c4_reference.md` | C4 spec, colors, checklist, common mistakes |

## Files to Modify

| File | Changes |
|------|---------|
| `skills/architecture-diagram-creator/SKILL.md` | C4 section: triggers, levels, workflow, flag |
| `skills/diagram-exporter/scripts/validate_svg.py` | +8 C4 checks, `--c4` flag, `--strict` flag, auto-detect |
| `skills/diagram-exporter/scripts/svg2drawio.py` | Detect data-c4-*, generate `<object>` with C4 shapes |
| `skills/diagram-exporter/SKILL.md` | Document C4 export pipeline |

## PPTX

No changes. Screenshots render the HTML as-is. `data-c4-*` attributes are invisible to the browser.

## Validation Strictness

- Default (`--c4`): pragmatic, WARNs on missing metadata
- Strict (`--c4 --strict`): full C4 model compliance, FAILs on missing metadata
- Configurable per-project via future `.c4config` or CLI flags
