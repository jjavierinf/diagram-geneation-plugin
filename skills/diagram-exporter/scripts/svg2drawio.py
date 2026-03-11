#!/usr/bin/env python3
"""
svg2drawio.py - Convert SVG architecture diagrams in HTML to editable .drawio files.

Usage:
    python3 svg2drawio.py <html-path> <output-drawio>

Parses SVG elements (rects, lines, paths, text) and maps them to Draw.io
mxCell XML elements. Each SVG becomes a separate tab/page in the .drawio file.
"""

import argparse
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from html import escape as html_escape


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def parse_color(fill_str, defs_map):
    """Resolve a fill value to a hex color. Handles url(#id), rgb(), rgba() refs."""
    if not fill_str or fill_str == 'none':
        return None
    if fill_str.startswith('url(#'):
        grad_id = fill_str[5:-1]
        return defs_map.get(grad_id, '#3b82f6')
    if fill_str.startswith('#'):
        return fill_str
    # Handle rgb(r,g,b) and rgba(r,g,b,a)
    rgb_match = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', fill_str)
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return f'#{r:02x}{g:02x}{b:02x}'
    named = {
        'white': '#FFFFFF', 'black': '#000000', 'red': '#FF0000',
        'blue': '#0000FF', 'green': '#00FF00', 'transparent': None,
    }
    return named.get(fill_str.lower(), fill_str)


def hex_luminance(hex_color):
    """Return relative luminance (0-1) of a hex color. Light colors > 0.5."""
    if not hex_color or not hex_color.startswith('#'):
        return 0.5
    h = hex_color.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    if len(h) != 6:
        return 0.5
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def contrast_font_color(fill_hex):
    """Return white or dark font color based on fill luminance."""
    if not fill_hex or fill_hex == 'none':
        return '#000000'
    lum = hex_luminance(fill_hex)
    return '#FFFFFF' if lum < 0.45 else '#000000'


# ---------------------------------------------------------------------------
# C4 model styles for Draw.io native C4 shapes
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

# Map data-c4-type attribute values to C4_STYLES keys
_C4_TYPE_MAP = {
    'person': 'person',
    'external person': 'external-person',
    'software system': 'software-system',
    'external system': 'external-system',
    'container': 'container',
    'container-db': 'container-db',
    'external container': 'external-container',
    'component': 'component',
    'external component': 'external-component',
    'boundary': 'boundary',
}


def _resolve_c4_style_key(c4_type_raw):
    """Map a raw data-c4-type value to a C4_STYLES key, or None."""
    if not c4_type_raw:
        return None
    normalized = c4_type_raw.strip().lower()
    return _C4_TYPE_MAP.get(normalized)


def build_c4_label(c4_name, c4_type_display, c4_technology, c4_description):
    """Build a Draw.io C4 label using %placeholder% syntax."""
    parts = []
    parts.append('&lt;b&gt;%c4Name%&lt;/b&gt;')
    if c4_type_display:
        parts.append('&lt;i&gt;[%c4Type%]&lt;/i&gt;')
    if c4_technology:
        parts.append('&lt;i&gt;[%c4Technology%]&lt;/i&gt;')
    if c4_description:
        parts.append('&lt;br/&gt;%c4Description%')
    return '&lt;br&gt;'.join(parts)


def xml_attr_escape(s):
    """Escape a string for use in an XML attribute value (inside double quotes).
    This handles &, <, >, " but preserves already-escaped &lt; &gt; etc."""
    # First replace raw & that aren't already part of an entity
    s = re.sub(r'&(?!lt;|gt;|amp;|quot;|#)', '&amp;', s)
    s = s.replace('"', '&quot;')
    # Don't re-escape < and > since our labels use &lt; and &gt; intentionally
    return s


# ---------------------------------------------------------------------------
# SVG parsing helpers
# ---------------------------------------------------------------------------

def parse_gradient_defs(svg_el, ns):
    """Extract gradient ID -> first stop color mapping."""
    defs_map = {}
    for lg in svg_el.iter():
        tag = lg.tag.split('}')[-1] if '}' in lg.tag else lg.tag
        if tag == 'linearGradient':
            gid = lg.get('id', '')
            stops = [s for s in lg if (s.tag.split('}')[-1] if '}' in s.tag else s.tag) == 'stop']
            if stops:
                color = stops[0].get('stop-color', '#3b82f6')
                defs_map[gid] = color
    return defs_map


def is_zone_rect(r, all_rects):
    """Heuristic: zone rects are large, light-colored backgrounds.
    Uses luminance-based detection instead of hardcoded color list."""
    w = float(r.get('w', 0))
    h = float(r.get('h', 0))
    area = w * h
    if area < 50000:  # zones must be genuinely large (raised from 25000)
        return False
    fill = r.get('fill', '')
    if not fill:
        return False
    lum = hex_luminance(fill)
    # Zones are very light backgrounds (luminance > 0.85)
    return lum > 0.85


def distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def find_rect_at_point(x, y, rects, tolerance=15):
    """Find a rect that contains or nearly contains the point."""
    best = None
    best_dist = tolerance
    for r in rects:
        cx = r['x'] + r['w'] / 2
        cy = r['y'] + r['h'] / 2
        if r['x'] - tolerance <= x <= r['x'] + r['w'] + tolerance and \
           r['y'] - tolerance <= y <= r['y'] + r['h'] + tolerance:
            d = distance(x, y, cx, cy)
            if best is None or d < best_dist:
                best = r
                best_dist = d
    return best


def parse_path_points(d_attr):
    """Extract start and end points from a path d attribute (M/L commands)."""
    if not d_attr:
        return None, None
    points = []
    parts = re.findall(r'([ML])\s*([-\d.]+)[,\s]+([-\d.]+)', d_attr)
    for cmd, x, y in parts:
        points.append((float(x), float(y)))
    if len(points) >= 2:
        return points[0], points[-1]
    return None, None


def scale_font_size(svg_fs):
    """Scale SVG font sizes for DrawIO readability. SVG renders smaller than DrawIO."""
    try:
        fs = float(svg_fs)
    except (ValueError, TypeError):
        return 10
    # SVG font sizes < 9 are unreadable in DrawIO. Scale up.
    if fs <= 7:
        return 10
    if fs <= 8:
        return 10
    if fs <= 9:
        return 11
    if fs <= 9.5:
        return 11
    return max(10, round(fs))


def estimate_text_width(text, font_size):
    """Estimate pixel width for a text string at given font size."""
    try:
        fs = float(font_size)
    except (ValueError, TypeError):
        fs = 10
    # Rough estimate: ~0.62 * fontSize per character, min 50
    return max(50, int(len(text) * fs * 0.65) + 20)


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------

def svg_to_drawio_cells(svg_el, page_id):
    """Convert an SVG element tree into a list of mxCell XML strings."""
    defs_map = parse_gradient_defs(svg_el, '')

    # Collect all elements by type
    raw_rects = []
    raw_lines = []
    raw_paths = []
    raw_texts = []

    for el in svg_el.iter():
        tag = el.tag.split('}')[-1] if '}' in el.tag else el.tag

        if tag == 'rect':
            x = float(el.get('x', 0))
            y = float(el.get('y', 0))
            w = float(el.get('width', 0))
            h = float(el.get('height', 0))
            fill = el.get('fill', '')
            stroke = el.get('stroke', '')
            rx = float(el.get('rx', 0))
            raw_rects.append({
                'x': x, 'y': y, 'w': w, 'h': h,
                'fill': fill, 'stroke': stroke, 'rx': rx, 'el': el
            })

        elif tag == 'line':
            raw_lines.append({
                'x1': float(el.get('x1', 0)), 'y1': float(el.get('y1', 0)),
                'x2': float(el.get('x2', 0)), 'y2': float(el.get('y2', 0)),
                'stroke': el.get('stroke', '#94a3b8'),
                'dashed': '1' if el.get('stroke-dasharray') else '0',
                'marker': el.get('marker-end', ''),
                'stroke_width': el.get('stroke-width', '1.5'),
            })

        elif tag == 'path':
            d_attr = el.get('d', '')
            fill = el.get('fill', 'none')
            stroke = el.get('stroke', '')
            if fill != 'none' and not stroke:
                continue
            if not d_attr or not stroke:
                continue
            raw_paths.append({
                'd': d_attr, 'stroke': stroke,
                'dashed': '1' if el.get('stroke-dasharray') else '0',
                'marker': el.get('marker-end', ''),
                'stroke_width': el.get('stroke-width', '1.5'),
            })

        elif tag == 'text':
            x = float(el.get('x', 0))
            y = float(el.get('y', 0))
            font_size = el.get('font-size', '10')
            font_weight = el.get('font-weight', 'normal')
            fill = el.get('fill', '#000000')
            anchor = el.get('text-anchor', 'start')

            # Check for tspan children with dy offsets (multi-line text)
            tspans = [c for c in el
                      if (c.tag.split('}')[-1] if '}' in c.tag else c.tag) == 'tspan']
            if tspans:
                cur_y = y
                for ts in tspans:
                    ts_text = (ts.text or '').strip()
                    if not ts_text:
                        continue
                    dy = float(ts.get('dy', 0))
                    cur_y += dy
                    ts_x = float(ts.get('x', x))
                    raw_texts.append({
                        'x': ts_x, 'y': cur_y, 'text': ts_text,
                        'font_size': ts.get('font-size', font_size),
                        'font_weight': ts.get('font-weight', font_weight),
                        'fill': ts.get('fill', fill),
                        'anchor': ts.get('text-anchor', anchor),
                    })
            else:
                text = (el.text or '').strip()
                if not text:
                    # Fallback: concatenate child text
                    parts = []
                    for c in el:
                        if c.text and c.text.strip():
                            parts.append(c.text.strip())
                    text = ' '.join(parts)
                if text:
                    raw_texts.append({
                        'x': x, 'y': y, 'text': text,
                        'font_size': font_size,
                        'font_weight': font_weight,
                        'fill': fill,
                        'anchor': anchor,
                    })

    # ---- Classify rects ----
    component_rects = []
    zone_rects = []

    # First pass: separate zones from components
    non_zone_rects = []
    for r in raw_rects:
        if r['w'] <= 6 or r['h'] <= 6:
            continue  # accent / decorative
        if is_zone_rect(r, raw_rects):
            zone_rects.append(r)
        else:
            non_zone_rects.append(r)

    # Second pass: skip rects fully contained inside another non-zone rect
    # (these are detail elements like table rows, badge pills that are too
    # small for draw.io's internal padding and cause overlap)
    MIN_COMPONENT_AREA = 3500  # skip tiny rects (badges, table cells)
    all_larger_rects = non_zone_rects + zone_rects  # check containment against both
    for r in non_zone_rects:
        area = r['w'] * r['h']
        if area < MIN_COMPONENT_AREA:
            # Check if it's inside a larger rect (zone or component)
            inside_larger = False
            for r2 in all_larger_rects:
                if r2 is r:
                    continue
                if (r2['w'] * r2['h'] > area and
                        r2['x'] <= r['x'] and r['x'] + r['w'] <= r2['x'] + r2['w'] and
                        r2['y'] <= r['y'] and r['y'] + r['h'] <= r2['y'] + r2['h']):
                    inside_larger = True
                    break
            if inside_larger:
                continue  # skip nested detail rects
        component_rects.append(r)

    # ---- Assign text to SMALLEST containing component rect ----
    used_texts = set()
    text_to_rect = {}

    for ti, t in enumerate(raw_texts):
        best_ri = None
        best_area = float('inf')
        for ri, r in enumerate(component_rects):
            if (r['x'] - 5 <= t['x'] <= r['x'] + r['w'] + 5 and
                    r['y'] - 5 <= t['y'] <= r['y'] + r['h'] + 15):
                area = r['w'] * r['h']
                if area < best_area:
                    best_area = area
                    best_ri = ri
        if best_ri is not None:
            text_to_rect[ti] = best_ri
            used_texts.add(ti)

    rect_labels = {}
    for ri in range(len(component_rects)):
        rect_labels[ri] = [raw_texts[ti] for ti, ari in text_to_rect.items() if ari == ri]

    # ---- Assign zone labels (text near top of zone) ----
    zone_labels = {}
    for zi, z in enumerate(zone_rects):
        labels = []
        for ti, t in enumerate(raw_texts):
            if ti in used_texts:
                continue
            # Skip small-font texts (arrow annotations like "triggers", "SQL")
            fs = float(t.get('font_size', '10'))
            if fs < 11:
                continue  # zone labels are always prominent, not tiny annotations
            # For center-anchored text, check if its estimated width fits
            # within the zone. Page-level titles are wider than any single zone.
            if t.get('anchor') == 'middle':
                est_w = estimate_text_width(t['text'], fs)
                if est_w > z['w'] * 1.2:
                    continue  # text wider than zone → likely page title
            if (z['x'] - 10 <= t['x'] <= z['x'] + z['w'] + 10 and
                    z['y'] - 20 <= t['y'] <= z['y'] + 30):
                labels.append(t)
                used_texts.add(ti)
        zone_labels[zi] = labels

    # ---- Build mxCell XML ----
    cells = []
    cell_id = 2
    rect_cell_ids = {}

    # Zone rects - subtle container style
    for zi, z in enumerate(zone_rects):
        zid = cell_id
        cell_id += 1

        # Check for C4 boundary metadata
        el = z.get('el')
        c4_type_raw = el.get('data-c4-type', '') if el is not None else ''
        c4_style_key = _resolve_c4_style_key(c4_type_raw)

        if c4_style_key == 'boundary':
            c4_name = el.get('data-c4-name', '') if el is not None else ''
            c4_desc = el.get('data-c4-description', '') if el is not None else ''
            c4_label = '&lt;b&gt;%c4Name%&lt;/b&gt;'
            if c4_desc:
                c4_label += '&lt;br&gt;%c4Description%'
            style = C4_STYLES['boundary']
            cells.append(
                f'<object placeholders="1" '
                f'c4Name="{xml_attr_escape(c4_name)}" '
                f'c4Type="boundary" '
                f'c4Description="{xml_attr_escape(c4_desc)}" '
                f'label="{xml_attr_escape(c4_label)}" '
                f'id="{zid}">'
                f'<mxCell style="{style}" vertex="1" parent="1">'
                f'<mxGeometry x="{z["x"]}" y="{z["y"]}" '
                f'width="{z["w"]}" height="{z["h"]}" as="geometry"/>'
                f'</mxCell>'
                f'</object>'
            )
        else:
            label_parts = [html_escape(t['text']) for t in zone_labels.get(zi, [])]
            label = '&lt;br&gt;'.join(label_parts) if label_parts else ''
            color = parse_color(z['fill'], defs_map) or '#F5F5F5'
            stroke_color = z['stroke'] or '#CCCCCC'
            zone_font = '#64748b'
            if zone_labels.get(zi):
                zone_font = zone_labels[zi][0].get('fill', '#64748b')
            style = (f'rounded=1;whiteSpace=wrap;html=1;fillColor={color};'
                     f'strokeColor={stroke_color};opacity=50;'
                     f'verticalAlign=top;fontStyle=1;fontSize=12;'
                     f'fontColor={zone_font};arcSize=6;spacingTop=4;')
            cells.append(
                f'<mxCell id="{zid}" value="{xml_attr_escape(label)}" '
                f'style="{style}" vertex="1" parent="1">'
                f'<mxGeometry x="{z["x"]}" y="{z["y"]}" '
                f'width="{z["w"]}" height="{z["h"]}" as="geometry"/>'
                f'</mxCell>'
            )

    # Component rects
    for ri, r in enumerate(component_rects):
        rid = cell_id
        cell_id += 1
        rect_cell_ids[ri] = rid

        # Check for C4 metadata on the raw SVG element
        el = r.get('el')
        c4_type_raw = el.get('data-c4-type', '') if el is not None else ''
        c4_style_key = _resolve_c4_style_key(c4_type_raw)

        if c4_style_key:
            # ---- C4-native export: emit <object> wrapping <mxCell> ----
            c4_name = el.get('data-c4-name', '') if el is not None else ''
            c4_desc = el.get('data-c4-description', '') if el is not None else ''
            c4_tech = el.get('data-c4-technology', '') if el is not None else ''
            c4_type_display = c4_type_raw.strip()

            c4_label = build_c4_label(c4_name, c4_type_display, c4_tech, c4_desc)
            style = C4_STYLES[c4_style_key]

            cells.append(
                f'<object placeholders="1" '
                f'c4Name="{xml_attr_escape(c4_name)}" '
                f'c4Type="{xml_attr_escape(c4_type_display)}" '
                f'c4Technology="{xml_attr_escape(c4_tech)}" '
                f'c4Description="{xml_attr_escape(c4_desc)}" '
                f'label="{xml_attr_escape(c4_label)}" '
                f'id="{rid}">'
                f'<mxCell style="{style}" vertex="1" parent="1">'
                f'<mxGeometry x="{r["x"]}" y="{r["y"]}" '
                f'width="{r["w"]}" height="{r["h"]}" as="geometry"/>'
                f'</mxCell>'
                f'</object>'
            )
        else:
            # ---- Standard (non-C4) export ----
            # Group texts by y-coordinate: texts at similar y are horizontal siblings
            # (e.g., table column headers) → join with " | " not "<br>"
            texts_for_rect = rect_labels.get(ri, [])
            if not texts_for_rect:
                label = ''
            else:
                # Sort by y then x
                sorted_texts = sorted(texts_for_rect, key=lambda t: (t['y'], t['x']))
                lines = []  # list of lists, each inner list = texts on same y-row
                for t in sorted_texts:
                    if lines and abs(t['y'] - lines[-1][0]['y']) < 5:
                        lines[-1].append(t)
                    else:
                        lines.append([t])
                label_parts = []
                for line_group in lines:
                    # Sort each line by x (left to right)
                    line_group.sort(key=lambda t: t['x'])
                    parts = []
                    for t in line_group:
                        txt = html_escape(t['text'])
                        if t['font_weight'] in ('600', '700', 'bold'):
                            txt = f'&lt;b&gt;{txt}&lt;/b&gt;'
                        parts.append(txt)
                    label_parts.append(' | '.join(parts) if len(parts) > 1 else parts[0])
                label = '&lt;br&gt;'.join(label_parts)

            fill = parse_color(r['fill'], defs_map) or '#FFFFFF'
            stroke_color = r['stroke'] or 'none'
            rounded = '1' if r['rx'] > 0 else '0'

            # Smart font color: use luminance-based contrast
            font_color = contrast_font_color(fill)

            # Determine font size: use the predominant label font size, scaled
            label_fs = 10
            if rect_labels.get(ri):
                sizes = [scale_font_size(t.get('font_size', '10')) for t in rect_labels[ri]]
                label_fs = max(sizes) if sizes else 10

            style = (f'rounded={rounded};whiteSpace=wrap;html=1;fillColor={fill};'
                     f'strokeColor={stroke_color};fontColor={font_color};'
                     f'fontSize={label_fs};arcSize=10;spacing=4;')

            cells.append(
                f'<mxCell id="{rid}" value="{xml_attr_escape(label)}" '
                f'style="{style}" vertex="1" parent="1">'
                f'<mxGeometry x="{r["x"]}" y="{r["y"]}" '
                f'width="{r["w"]}" height="{r["h"]}" as="geometry"/>'
                f'</mxCell>'
            )

    # ---- Filter out legend-internal lines ----
    # Legend rects are small white boxes containing short colored line segments
    # (typically < 30px long) used as visual keys. These lines are not data edges.
    def is_inside_any_rect(x1, y1, x2, y2, rects):
        """Check if a line segment is fully contained inside a component rect."""
        for r in rects:
            if (r['x'] <= min(x1, x2) and max(x1, x2) <= r['x'] + r['w'] and
                    r['y'] <= min(y1, y2) and max(y1, y2) <= r['y'] + r['h']):
                return True
        return False

    def line_length(x1, y1, x2, y2):
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    # Remove short lines inside SMALL component rects (legend decoration)
    # Only check small rects (area < 15000) to avoid filtering arrows inside
    # large content boxes that were misclassified
    legend_rects = [r for r in component_rects if r['w'] * r['h'] < 15000]
    raw_lines = [ln for ln in raw_lines
                 if not (line_length(ln['x1'], ln['y1'], ln['x2'], ln['y2']) < 30 and
                         is_inside_any_rect(ln['x1'], ln['y1'], ln['x2'], ln['y2'],
                                            legend_rects))]

    # ---- Edges ----
    # IMPORTANT: We do NOT bind edges to source/target rects via id attributes.
    # Draw.io's orthogonal edge router re-routes aggressively between connected
    # shapes, creating loops and detours for closely-stacked boxes.
    # Instead we use only explicit sourcePoint/targetPoint coordinates with
    # no edgeStyle, giving us exact positioning that matches the original SVG.

    def is_straight(x1, y1, x2, y2):
        """True if the line is purely horizontal or vertical."""
        return abs(x1 - x2) < 1 or abs(y1 - y2) < 1

    # Lines as edges
    for ln in raw_lines:
        eid = cell_id
        cell_id += 1

        color = ln['stroke']
        dashed = ln['dashed']
        has_arrow = bool(ln['marker'])
        sw = ln.get('stroke_width', '1.5')
        # No edgeStyle = straight line between explicit points
        style = (f'strokeColor={color};strokeWidth={sw};dashed={dashed};'
                 f'endArrow={"block" if has_arrow else "none"};endFill=1;'
                 f'exitX=0.5;exitY=1;entryX=0.5;entryY=0;')

        cells.append(
            f'<mxCell id="{eid}" value="" '
            f'style="{style}" edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{ln["x1"]}" y="{ln["y1"]}" as="sourcePoint"/>'
            f'<mxPoint x="{ln["x2"]}" y="{ln["y2"]}" as="targetPoint"/>'
            f'</mxGeometry>'
            f'</mxCell>'
        )

    # Paths as edges with explicit waypoints
    for p in raw_paths:
        eid = cell_id
        cell_id += 1
        start, end = parse_path_points(p['d'])
        if not start or not end:
            continue

        color = p['stroke']
        dashed = p['dashed']
        has_arrow = bool(p['marker'])
        sw = p.get('stroke_width', '1.5')
        style = (f'strokeColor={color};strokeWidth={sw};dashed={dashed};'
                 f'endArrow={"block" if has_arrow else "none"};endFill=1;')

        # Extract ALL points from path as explicit waypoints
        all_points = re.findall(r'([-\d.]+)[,\s]+([-\d.]+)', p['d'])
        waypoints_xml = ''
        if len(all_points) > 2:
            waypoints_xml = '<Array as="points">'
            for px, py in all_points[1:-1]:
                waypoints_xml += f'<mxPoint x="{px}" y="{py}"/>'
            waypoints_xml += '</Array>'

        cells.append(
            f'<mxCell id="{eid}" value="" '
            f'style="{style}" edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{start[0]}" y="{start[1]}" as="sourcePoint"/>'
            f'<mxPoint x="{end[0]}" y="{end[1]}" as="targetPoint"/>'
            f'{waypoints_xml}'
            f'</mxGeometry>'
            f'</mxCell>'
        )

    # Floating text labels (unassigned to any rect)
    # CRITICAL: Merge nearby text elements into single multi-line cells.
    # Draw.io renders each cell with internal padding (~5px), so many
    # individual text cells at close y-coordinates overlap. SVG can render
    # text at exact pixel positions but draw.io cannot.

    floating_texts = [(ti, raw_texts[ti]) for ti in range(len(raw_texts))
                      if ti not in used_texts]

    # Group floating texts that are vertically close and horizontally aligned.
    # Thresholds are generous because draw.io renders each cell with ~5px
    # internal padding, so individual text cells at close positions overlap.
    MERGE_X_THRESHOLD = 80   # max x-distance to consider "same column"
    MERGE_Y_THRESHOLD = 28   # max y-gap between consecutive lines
    MERGE_FS_THRESHOLD = 5   # max font-size difference to merge
    merged_groups = []
    used_floating = set()

    # Sort floating texts by y then x for better merge ordering
    floating_texts_sorted = sorted(floating_texts, key=lambda ft: (ft[1]['y'], ft[1]['x']))

    for i, (ti, t) in enumerate(floating_texts_sorted):
        if ti in used_floating:
            continue
        group = [t]
        used_floating.add(ti)
        base_fs = float(t.get('font_size', '10'))
        # Find other texts that are vertically below and horizontally close
        # Don't merge texts with very different font sizes (e.g. big "3" vs small label)
        for j, (tj, t2) in enumerate(floating_texts_sorted):
            if tj in used_floating:
                continue
            t2_fs = float(t2.get('font_size', '10'))
            if (abs(t2['x'] - t['x']) < MERGE_X_THRESHOLD and
                    0 < t2['y'] - group[-1]['y'] < MERGE_Y_THRESHOLD and
                    abs(t2_fs - base_fs) <= MERGE_FS_THRESHOLD):
                group.append(t2)
                used_floating.add(tj)
        merged_groups.append(group)

    for group in merged_groups:
        tid = cell_id
        cell_id += 1

        # Group texts by y-coordinate: same-y texts join with " | "
        sorted_group = sorted(group, key=lambda t: (t['y'], t['x']))
        lines = []
        for t in sorted_group:
            if lines and abs(t['y'] - lines[-1][0]['y']) < 5:
                lines[-1].append(t)
            else:
                lines.append([t])

        label_parts = []
        max_w = 0
        for line_group in lines:
            line_group.sort(key=lambda t: t['x'])
            parts = []
            line_w = 0
            for t in line_group:
                txt = html_escape(t['text'])
                if t['font_weight'] in ('600', '700', 'bold'):
                    txt = f'&lt;b&gt;{txt}&lt;/b&gt;'
                parts.append(txt)
                fs = scale_font_size(t.get('font_size', '10'))
                line_w += estimate_text_width(t['text'], fs)
            label_parts.append(' | '.join(parts) if len(parts) > 1 else parts[0])
            # For multi-text lines, estimate total width including separators
            if len(parts) > 1:
                line_w += (len(parts) - 1) * 20  # separator width
            if line_w > max_w:
                max_w = line_w

        # Also compute max single-text width
        for t in group:
            fs = scale_font_size(t.get('font_size', '10'))
            w = estimate_text_width(t['text'], fs)
            if w > max_w:
                max_w = w

        label = '&lt;br&gt;'.join(label_parts)
        color = group[0].get('fill', '#000000')
        fs = scale_font_size(group[0].get('font_size', '10'))
        # Height: account for number of LINES (not texts)
        line_h = max(14, fs + 4)
        est_h = line_h * len(lines) + 8

        # Position from first text in group
        tx = group[0]['x']
        ty = group[0]['y'] - fs  # offset up since SVG y is baseline
        if group[0].get('anchor') == 'middle':
            tx = tx - max_w / 2
        elif group[0].get('anchor') == 'end':
            tx = tx - max_w

        style = (f'text;html=1;align=center;verticalAlign=top;'
                 f'resizable=0;points=[];'
                 f'strokeColor=none;fillColor=none;fontColor={color};fontSize={fs};'
                 f'spacingTop=0;spacingBottom=0;spacing=0;')
        cells.append(
            f'<mxCell id="{tid}" value="{xml_attr_escape(label)}" '
            f'style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{tx}" y="{ty}" '
            f'width="{max_w}" height="{est_h}" as="geometry"/>'
            f'</mxCell>'
        )

    return cells


# ---------------------------------------------------------------------------
# HTML parsing and .drawio assembly
# ---------------------------------------------------------------------------

def html_to_drawio(html_path, output_path):
    """Parse HTML, extract SVGs, convert each to a Draw.io diagram tab."""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    svg_pattern = re.compile(r'(<svg[^>]*>.*?</svg>)', re.DOTALL)
    svg_matches_raw = svg_pattern.findall(content)

    # Filter out tiny inline SVGs (legends, icons) that produce empty tabs
    svg_matches = []
    for svg_str in svg_matches_raw:
        # Check width/height attributes
        w_match = re.search(r'\bwidth="(\d+)"', svg_str)
        h_match = re.search(r'\bheight="(\d+)"', svg_str)
        if w_match and h_match:
            w, h = int(w_match.group(1)), int(h_match.group(1))
            if w < 100 or h < 100:
                continue  # skip tiny SVGs (legend icons, decorative)
        svg_matches.append(svg_str)

    if not svg_matches:
        print("No SVG elements found in the HTML file.", file=sys.stderr)
        sys.exit(1)

    svg_titles = []
    for i, svg_str in enumerate(svg_matches):
        pos = content.find(svg_str)
        preceding = content[:pos]
        h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', preceding, re.DOTALL)
        if h2_matches:
            title = re.sub(r'<[^>]+>', ' ', h2_matches[-1]).strip()
            title = ' '.join(title.split())
        else:
            title = f'Diagram {i + 1}'
        svg_titles.append(title)

    diagrams_xml = []
    for i, (svg_str, title) in enumerate(zip(svg_matches, svg_titles)):
        try:
            svg_el = ET.fromstring(svg_str)
        except ET.ParseError as e:
            print(f"Warning: Could not parse SVG {i}: {e}", file=sys.stderr)
            continue

        cells = svg_to_drawio_cells(svg_el, i)
        cells_xml = '\n          '.join(cells)

        diagram_xml = f'''  <diagram id="page-{i}" name="{html_escape(title)}">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="900" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        {cells_xml}
      </root>
    </mxGraphModel>
  </diagram>'''
        diagrams_xml.append(diagram_xml)

    drawio_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="Claude" modified="2026-03-10" type="device">
{chr(10).join(diagrams_xml)}
</mxfile>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(drawio_xml)

    print(f"Saved {output_path} ({len(diagrams_xml)} diagram tabs)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Convert HTML/SVG diagrams to Draw.io')
    parser.add_argument('html_path', help='Path to the HTML file with SVG diagrams')
    parser.add_argument('output_drawio', help='Output .drawio file path')
    args = parser.parse_args()

    html_path = os.path.abspath(args.html_path)
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found", file=sys.stderr)
        sys.exit(1)

    html_to_drawio(html_path, args.output_drawio)


if __name__ == '__main__':
    main()
