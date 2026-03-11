#!/usr/bin/env python3
"""
validate_svg.py - SVG diagram quality checks on HTML source files.

Usage:
    python3 validate_svg.py <html-file> [--json] [--c4] [--strict]

Checks SVG elements for layout quality, text placement, arrow routing,
and design consistency BEFORE conversion to any output format.

Output: Human-readable report (default) or JSON (--json).
Exit code: 0 if all pass, 1 if any fail, 2 if any warn.
"""

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# SVG Parsing
# ---------------------------------------------------------------------------

def extract_svgs(html_path):
    """Extract SVG elements from HTML, skipping tiny ones (< 100px)."""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    svg_pattern = re.compile(r'(<svg[^>]*>.*?</svg>)', re.DOTALL)
    matches = svg_pattern.findall(content)

    svgs = []
    for svg_str in matches:
        w_match = re.search(r'\bwidth="(\d+)"', svg_str)
        h_match = re.search(r'\bheight="(\d+)"', svg_str)
        if w_match and h_match:
            w, h = int(w_match.group(1)), int(h_match.group(1))
            if w < 100 or h < 100:
                continue
        svgs.append(svg_str)
    return svgs


def parse_svg_elements(svg_str):
    """Parse SVG into rects, texts, lines, paths."""
    try:
        svg_el = ET.fromstring(svg_str)
    except ET.ParseError:
        return None

    rects = []
    texts = []
    lines = []
    paths = []

    # Extract C4 attributes from SVG root
    c4_level = svg_el.get('data-c4-level', '')
    c4_scope = svg_el.get('data-c4-scope', '')

    for el in svg_el.iter():
        tag = el.tag.split('}')[-1] if '}' in el.tag else el.tag

        if tag == 'rect':
            x = float(el.get('x', 0))
            y = float(el.get('y', 0))
            w = float(el.get('width', 0))
            h = float(el.get('height', 0))
            if w > 6 and h > 6:  # skip decorative accents
                rect_dict = {'x': x, 'y': y, 'w': w, 'h': h,
                             'fill': el.get('fill', ''),
                             'stroke': el.get('stroke', ''),
                             'el': el}
                # Extract all data-c4-* attributes
                for attr_name, attr_val in el.attrib.items():
                    if attr_name.startswith('data-c4-'):
                        key = 'c4_' + attr_name[8:]  # data-c4-type -> c4_type
                        rect_dict[key] = attr_val
                rects.append(rect_dict)

        elif tag == 'text':
            x = float(el.get('x', 0))
            y = float(el.get('y', 0))
            fs = el.get('font-size', '10')
            anchor = el.get('text-anchor', 'start')
            # Collect text from tspans or direct
            tspans = [c for c in el
                      if (c.tag.split('}')[-1] if '}' in c.tag else c.tag) == 'tspan']
            if tspans:
                for ts in tspans:
                    ts_text = (ts.text or '').strip()
                    if ts_text:
                        dy = float(ts.get('dy', 0))
                        texts.append({
                            'x': float(ts.get('x', x)), 'y': y + dy,
                            'text': ts_text,
                            'font_size': ts.get('font-size', fs),
                            'anchor': ts.get('text-anchor', anchor),
                        })
                        y += dy  # accumulate for next tspan
            else:
                text = (el.text or '').strip()
                if not text:
                    parts = [c.text.strip() for c in el if c.text and c.text.strip()]
                    text = ' '.join(parts)
                if text:
                    texts.append({'x': x, 'y': y, 'text': text,
                                  'font_size': fs, 'anchor': anchor})

        elif tag == 'line':
            lines.append({
                'x1': float(el.get('x1', 0)), 'y1': float(el.get('y1', 0)),
                'x2': float(el.get('x2', 0)), 'y2': float(el.get('y2', 0)),
                'stroke': el.get('stroke', ''),
                'dashed': bool(el.get('stroke-dasharray')),
                'marker': el.get('marker-end', ''),
            })

        elif tag == 'path':
            d = el.get('d', '')
            stroke = el.get('stroke', '')
            fill = el.get('fill', 'none')
            if stroke and (fill == 'none' or not fill):
                pts = re.findall(r'([ML])\s*([-\d.]+)[,\s]+([-\d.]+)', d)
                if len(pts) >= 2:
                    points = [(float(x), float(y)) for _, x, y in pts]
                    path_dict = {
                        'points': points,
                        'stroke': stroke,
                        'dashed': bool(el.get('stroke-dasharray')),
                        'marker': el.get('marker-end', ''),
                    }
                    # Extract C4 attributes from paths
                    for attr_name, attr_val in el.attrib.items():
                        if attr_name.startswith('data-c4-'):
                            key = 'c4_' + attr_name[8:]
                            path_dict[key] = attr_val
                    paths.append(path_dict)

    # Parse viewBox for SVG dimensions
    vb = svg_el.get('viewBox', '')
    vb_parts = vb.split()
    raw_w = svg_el.get('width', vb_parts[2] if len(vb_parts) >= 3 else '800')
    raw_h = svg_el.get('height', vb_parts[3] if len(vb_parts) >= 4 else '600')
    # Handle percentage widths (e.g., "100%") by falling back to viewBox
    try:
        svg_w = float(raw_w)
    except ValueError:
        svg_w = float(vb_parts[2]) if len(vb_parts) >= 3 else 800.0
    try:
        svg_h = float(raw_h)
    except ValueError:
        svg_h = float(vb_parts[3]) if len(vb_parts) >= 4 else 600.0

    return {
        'rects': rects, 'texts': texts, 'lines': lines, 'paths': paths,
        'width': svg_w, 'height': svg_h,
        'c4_level': c4_level, 'c4_scope': c4_scope,
    }


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

def _estimate_text_width(text, font_size):
    """Rough pixel width estimate for a text string."""
    try:
        fs = float(font_size)
    except (ValueError, TypeError):
        fs = 10
    return len(text) * fs * 0.6


def _find_containing_rect(tx, ty, text, rects, anchor='start'):
    """Find the smallest rect that contains a text element."""
    tw = _estimate_text_width(text, 12)  # rough estimate
    # Adjust x based on anchor
    if anchor == 'middle':
        tx = tx - tw / 2
    elif anchor == 'end':
        tx = tx - tw
    best = None
    best_area = float('inf')
    for r in rects:
        if (r['x'] - 10 <= tx <= r['x'] + r['w'] + 10 and
                r['y'] - 20 <= ty <= r['y'] + r['h'] + 10):
            area = r['w'] * r['h']
            if area < best_area:
                best = r
                best_area = area
    return best


def check_text_in_bounds(elements):
    """Check that text elements fit inside their containing rect."""
    issues = []
    for t in elements['texts']:
        r = _find_containing_rect(t['x'], t['y'], t['text'],
                                  elements['rects'], t.get('anchor', 'start'))
        if r is None:
            continue  # floating text, ok
        # Check if text baseline is within rect vertically
        # SVG text y is baseline, so it should be between rect.y and rect.y+rect.h
        margin = 5
        if t['y'] < r['y'] + margin:
            issues.append({
                'type': 'text_out_of_bounds',
                'severity': 'warn',
                'text': t['text'][:50],
                'direction': 'above',
                'text_y': round(t['y'], 1),
                'rect_top': round(r['y'], 1),
            })
        elif t['y'] > r['y'] + r['h'] + margin:
            issues.append({
                'type': 'text_out_of_bounds',
                'severity': 'warn',
                'text': t['text'][:50],
                'direction': 'below',
                'text_y': round(t['y'], 1),
                'rect_bottom': round(r['y'] + r['h'], 1),
            })
        # Check horizontal: estimated text width vs rect width
        tw = _estimate_text_width(t['text'], t.get('font_size', '12'))
        if tw > r['w'] * 1.3:  # 30% tolerance
            issues.append({
                'type': 'text_overflow_horizontal',
                'severity': 'warn',
                'text': t['text'][:50],
                'est_width': round(tw, 1),
                'rect_width': round(r['w'], 1),
            })
    return issues


def check_text_overlap(elements):
    """Check that text elements don't overlap each other."""
    issues = []
    texts = elements['texts']
    for i, a in enumerate(texts):
        a_fs = float(a.get('font_size', '12'))
        a_w = _estimate_text_width(a['text'], a_fs)
        a_h = a_fs * 1.2
        ax = a['x'] - (a_w / 2 if a.get('anchor') == 'middle' else 0)
        ay = a['y'] - a_fs  # baseline to top

        for b in texts[i+1:]:
            b_fs = float(b.get('font_size', '12'))
            b_w = _estimate_text_width(b['text'], b_fs)
            b_h = b_fs * 1.2
            bx = b['x'] - (b_w / 2 if b.get('anchor') == 'middle' else 0)
            by = b['y'] - b_fs

            # Check bounding box intersection
            if (ax < bx + b_w and ax + a_w > bx and
                    ay < by + b_h and ay + a_h > by):
                issues.append({
                    'type': 'text_overlap',
                    'severity': 'warn',
                    'text_a': a['text'][:40],
                    'text_b': b['text'][:40],
                })
    return issues


def _line_crosses_rect(x1, y1, x2, y2, r, margin=5):
    """Check if a line segment passes through a rect (not just touching edges)."""
    rx, ry, rw, rh = r['x'] + margin, r['y'] + margin, r['w'] - 2*margin, r['h'] - 2*margin
    if rw <= 0 or rh <= 0:
        return False

    # Check if either endpoint is inside - that's a connection, not a crossing
    def inside(px, py):
        return rx <= px <= rx + rw and ry <= py <= ry + rh
    if inside(x1, y1) or inside(x2, y2):
        return False

    # Liang-Barsky line clipping to check intersection
    dx = x2 - x1
    dy = y2 - y1
    p = [-dx, dx, -dy, dy]
    q = [x1 - rx, rx + rw - x1, y1 - ry, ry + rh - y1]
    t0, t1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return False
        else:
            t = qi / pi
            if pi < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
        if t0 > t1:
            return False
    return t0 < t1


def check_arrow_routing(elements):
    """Check that arrows don't cross through unrelated boxes."""
    issues = []
    rects = elements['rects']

    # Check lines
    for ln in elements['lines']:
        for r in rects:
            if _line_crosses_rect(ln['x1'], ln['y1'], ln['x2'], ln['y2'], r):
                issues.append({
                    'type': 'arrow_crosses_box',
                    'severity': 'warn',
                    'arrow': f"({ln['x1']:.0f},{ln['y1']:.0f})->({ln['x2']:.0f},{ln['y2']:.0f})",
                    'box_at': f"({r['x']:.0f},{r['y']:.0f}) {r['w']:.0f}x{r['h']:.0f}",
                })

    # Check paths (segment by segment)
    for p in elements['paths']:
        pts = p['points']
        for k in range(len(pts) - 1):
            x1, y1 = pts[k]
            x2, y2 = pts[k+1]
            for r in rects:
                if _line_crosses_rect(x1, y1, x2, y2, r):
                    issues.append({
                        'type': 'arrow_crosses_box',
                        'severity': 'warn',
                        'arrow': f"path segment ({x1:.0f},{y1:.0f})->({x2:.0f},{y2:.0f})",
                        'box_at': f"({r['x']:.0f},{r['y']:.0f}) {r['w']:.0f}x{r['h']:.0f}",
                    })
    return issues


def check_arrow_convergence(elements):
    """Detect multiple arrows converging on the exact same point."""
    issues = []
    endpoints = []

    for ln in elements['lines']:
        endpoints.append(('start', ln['x1'], ln['y1']))
        endpoints.append(('end', ln['x2'], ln['y2']))
    for p in elements['paths']:
        if p['points']:
            endpoints.append(('start', p['points'][0][0], p['points'][0][1]))
            endpoints.append(('end', p['points'][-1][0], p['points'][-1][1]))

    # Group endpoints within 15px of each other (visual review showed
    # convergence is noticeable even at 10-15px spacing)
    clusters = []
    used = set()
    for i, (_, x1, y1) in enumerate(endpoints):
        if i in used:
            continue
        cluster = [(x1, y1)]
        used.add(i)
        for j, (_, x2, y2) in enumerate(endpoints):
            if j in used:
                continue
            if math.sqrt((x2-x1)**2 + (y2-y1)**2) < 15:
                cluster.append((x2, y2))
                used.add(j)
        if len(cluster) >= 2:
            clusters.append(cluster)

    for cluster in clusters:
        cx = sum(p[0] for p in cluster) / len(cluster)
        cy = sum(p[1] for p in cluster) / len(cluster)
        issues.append({
            'type': 'arrow_convergence',
            'severity': 'warn',
            'count': len(cluster),
            'point': f"({cx:.0f},{cy:.0f})",
            'message': f'{len(cluster)} arrow endpoints within 5px - space them out',
        })
    return issues


def check_consistent_spacing(elements):
    """Check that boxes at similar y-coordinates have consistent horizontal gaps."""
    issues = []
    rects = sorted(elements['rects'], key=lambda r: (r['y'], r['x']))

    # Group rects by similar y (within 20px = same row)
    rows = []
    for r in rects:
        placed = False
        for row in rows:
            if abs(r['y'] - row[0]['y']) < 20:
                row.append(r)
                placed = True
                break
        if not placed:
            rows.append([r])

    for row in rows:
        if len(row) < 3:
            continue  # need at least 3 to check consistency
        row.sort(key=lambda r: r['x'])
        gaps = []
        for i in range(len(row) - 1):
            gap = row[i+1]['x'] - (row[i]['x'] + row[i]['w'])
            gaps.append(gap)
        if not gaps:
            continue
        avg_gap = sum(gaps) / len(gaps)
        if avg_gap <= 0:
            continue
        for i, gap in enumerate(gaps):
            if abs(gap - avg_gap) / avg_gap > 0.3:
                issues.append({
                    'type': 'inconsistent_spacing',
                    'severity': 'warn',
                    'row_y': round(row[0]['y']),
                    'gap': round(gap, 1),
                    'avg_gap': round(avg_gap, 1),
                    'between': f"box at x={row[i]['x']:.0f} and x={row[i+1]['x']:.0f}",
                })
    return issues


def check_whitespace_balance(elements):
    """Check that diagram content is reasonably centered in the SVG."""
    issues = []
    rects = elements['rects']
    if not rects:
        return issues

    # Content bounding box
    min_x = min(r['x'] for r in rects)
    min_y = min(r['y'] for r in rects)
    max_x = max(r['x'] + r['w'] for r in rects)
    max_y = max(r['y'] + r['h'] for r in rects)

    content_cx = (min_x + max_x) / 2
    content_cy = (min_y + max_y) / 2
    svg_cx = elements['width'] / 2
    svg_cy = elements['height'] / 2

    # Check if content center deviates > 20% from SVG center
    x_dev = abs(content_cx - svg_cx) / elements['width']
    y_dev = abs(content_cy - svg_cy) / elements['height']

    if x_dev > 0.2:
        issues.append({
            'type': 'whitespace_imbalance',
            'severity': 'warn',
            'axis': 'horizontal',
            'deviation_pct': round(x_dev * 100, 1),
        })
    if y_dev > 0.2:
        issues.append({
            'type': 'whitespace_imbalance',
            'severity': 'warn',
            'axis': 'vertical',
            'deviation_pct': round(y_dev * 100, 1),
        })
    return issues


def check_label_completeness(elements):
    """Check that rects have labels and arrows have labels (C4 best practice)."""
    issues = []
    # Check rects without any text nearby
    for r in elements['rects']:
        has_text = False
        for t in elements['texts']:
            if (r['x'] - 10 <= t['x'] <= r['x'] + r['w'] + 10 and
                    r['y'] - 10 <= t['y'] <= r['y'] + r['h'] + 15):
                has_text = True
                break
        if not has_text:
            # Skip very small rects (decorative) and very large (zone backgrounds)
            area = r['w'] * r['h']
            if 1000 < area < 200000:
                issues.append({
                    'type': 'unlabeled_box',
                    'severity': 'warn',
                    'position': f"({r['x']:.0f},{r['y']:.0f})",
                    'size': f"{r['w']:.0f}x{r['h']:.0f}",
                })

    # Count unlabeled arrows (lines + paths with marker-end but no nearby text)
    arrow_count = 0
    labeled_count = 0
    all_arrows = []
    for ln in elements['lines']:
        if ln['marker']:
            arrow_count += 1
            mx = (ln['x1'] + ln['x2']) / 2
            my = (ln['y1'] + ln['y2']) / 2
            all_arrows.append((mx, my))
    for p in elements['paths']:
        if p['marker'] and len(p['points']) >= 2:
            arrow_count += 1
            mx = (p['points'][0][0] + p['points'][-1][0]) / 2
            my = (p['points'][0][1] + p['points'][-1][1]) / 2
            all_arrows.append((mx, my))

    for mx, my in all_arrows:
        for t in elements['texts']:
            if math.sqrt((t['x'] - mx)**2 + (t['y'] - my)**2) < 40:
                labeled_count += 1
                break

    if arrow_count > 0:
        unlabeled_pct = (arrow_count - labeled_count) / arrow_count * 100
        if unlabeled_pct > 50:
            issues.append({
                'type': 'unlabeled_arrows',
                'severity': 'warn',
                'total': arrow_count,
                'unlabeled': arrow_count - labeled_count,
                'pct': round(unlabeled_pct, 1),
            })
    return issues


def check_arrow_through_text(elements):
    """Check that arrow lines don't pass through text labels."""
    issues = []
    for t in elements['texts']:
        fs = float(t.get('font_size', '12'))
        tw = _estimate_text_width(t['text'], fs)
        th = fs * 1.4
        tx = t['x'] - (tw / 2 if t.get('anchor') == 'middle' else 0)
        ty = t['y'] - fs  # baseline to top
        # Create a pseudo-rect for the text bounding box
        text_rect = {'x': tx, 'y': ty, 'w': tw, 'h': th}

        for ln in elements['lines']:
            if _line_crosses_rect(ln['x1'], ln['y1'], ln['x2'], ln['y2'], text_rect, margin=2):
                issues.append({
                    'type': 'arrow_through_text',
                    'severity': 'warn',
                    'text': t['text'][:40],
                    'arrow': f"({ln['x1']:.0f},{ln['y1']:.0f})->({ln['x2']:.0f},{ln['y2']:.0f})",
                })
        for p in elements['paths']:
            pts = p['points']
            for k in range(len(pts) - 1):
                if _line_crosses_rect(pts[k][0], pts[k][1], pts[k+1][0], pts[k+1][1],
                                      text_rect, margin=2):
                    issues.append({
                        'type': 'arrow_through_text',
                        'severity': 'warn',
                        'text': t['text'][:40],
                        'arrow': f"path near ({pts[k][0]:.0f},{pts[k][1]:.0f})",
                    })
                    break  # one hit per text per path is enough
    return issues


def check_font_consistency(elements):
    """Flag diagrams using more than 3 distinct font sizes."""
    sizes = set()
    for t in elements['texts']:
        try:
            sizes.add(round(float(t['font_size'])))
        except (ValueError, TypeError):
            pass
    if len(sizes) > 3:
        issues = [{
            'type': 'too_many_font_sizes',
            'severity': 'warn',
            'count': len(sizes),
            'sizes': sorted(sizes),
        }]
        return issues
    return []


def check_color_consistency(elements):
    """Flag diagrams using more than 8 distinct fill colors."""
    fills = set()
    for r in elements['rects']:
        f = r.get('fill', '')
        if f and f != 'none':
            fills.add(f.lower())
    if len(fills) > 8:
        return [{
            'type': 'too_many_colors',
            'severity': 'warn',
            'count': len(fills),
            'colors': sorted(fills),
        }]
    return []


def check_zone_label_clearance(elements):
    """Check that zone labels have adequate clearance from component boxes.

    Zone labels positioned too close to component boxes get overlapped or
    confused during rendering. Added by calibration batch 3 (iterations 11-15):
    zone_label_confusion gap in nested hierarchy layouts.
    """
    issues = []
    rects = elements['rects']
    texts = elements['texts']
    if len(rects) < 3:
        return issues

    # Identify zones as the largest rects
    areas = sorted([r['w'] * r['h'] for r in rects], reverse=True)
    median_area = areas[len(areas) // 2]
    zone_threshold = median_area * 2

    zones = [r for r in rects if r['w'] * r['h'] >= zone_threshold]
    components = [r for r in rects if r['w'] * r['h'] < zone_threshold and r['w'] > 30]

    # Find texts that are likely zone labels (near top of a zone, bold-weight keywords)
    for zone in zones:
        # Zone label expected near (zone.x + margin, zone.y + margin)
        zone_label_area = {
            'x': zone['x'], 'y': zone['y'],
            'w': zone['w'], 'h': 40  # first 40px of zone
        }

        for comp in components:
            # Check if component overlaps zone label area
            if (comp['x'] < zone_label_area['x'] + zone_label_area['w'] and
                    comp['x'] + comp['w'] > zone_label_area['x'] and
                    comp['y'] < zone_label_area['y'] + zone_label_area['h'] and
                    comp['y'] + comp['h'] > zone_label_area['y']):
                issues.append({
                    'type': 'zone_label_overlap',
                    'severity': 'warn',
                    'zone_at': f"({zone['x']:.0f},{zone['y']:.0f})",
                    'box_at': f"({comp['x']:.0f},{comp['y']:.0f})",
                    'message': 'Component box overlaps zone label area (top 40px of zone)',
                })

    return issues


def check_label_density(elements):
    """Check for clusters of small rects (label badges) that are too close together.

    Arrow annotation badges (small rects with text) that cluster together create
    unreadable label density. Added by calibration batch 2 (iterations 6-10):
    arrow_label_collision gap found when multiple annotation badges overlap.
    """
    issues = []
    rects = elements['rects']

    # Identify small rects as potential label badges (area < 3000, w < 120, h < 40)
    badges = [r for r in rects if r['w'] < 120 and r['h'] < 40 and r['w'] * r['h'] < 3000]

    if len(badges) < 2:
        return issues

    # Check pairwise distance between badge centers
    for i, a in enumerate(badges):
        acx = a['x'] + a['w'] / 2
        acy = a['y'] + a['h'] / 2
        nearby = 0
        for b in badges[i+1:]:
            bcx = b['x'] + b['w'] / 2
            bcy = b['y'] + b['h'] / 2
            dist = math.sqrt((acx - bcx)**2 + (acy - bcy)**2)
            if dist < 50:  # badges within 50px are too close
                nearby += 1

        if nearby >= 2:  # 3+ badges clustered
            issues.append({
                'type': 'label_density',
                'severity': 'warn',
                'badge_at': f"({a['x']:.0f},{a['y']:.0f})",
                'nearby_count': nearby,
                'message': f'{nearby + 1} label badges clustered within 50px - spread them out',
            })

    return issues


def check_box_containment(elements):
    """Check that component boxes are geometrically inside their zone (large) rects.

    Zone rects are identified as the largest rects (area > 50% of median).
    Component rects should be fully contained within at least one zone rect.
    Added by calibration batch 1 (iterations 1-5): box_outside_zone gap detected
    when a component box was positioned below its intended zone boundary.
    """
    issues = []
    rects = elements['rects']
    if len(rects) < 3:
        return issues  # too few rects to distinguish zones from components

    # Identify zones as the largest rects
    areas = sorted([r['w'] * r['h'] for r in rects], reverse=True)
    median_area = areas[len(areas) // 2]
    zone_threshold = median_area * 2  # zones are significantly larger than components

    zones = [r for r in rects if r['w'] * r['h'] >= zone_threshold]
    components = [r for r in rects if r['w'] * r['h'] < zone_threshold]

    if not zones:
        return issues

    for comp in components:
        # Skip very small rects (legend swatches, decorations)
        if comp['w'] < 30 or comp['h'] < 30:
            continue

        contained = False
        for zone in zones:
            # Check if component is fully inside zone (with 5px tolerance)
            if (comp['x'] >= zone['x'] - 5 and
                    comp['y'] >= zone['y'] - 5 and
                    comp['x'] + comp['w'] <= zone['x'] + zone['w'] + 5 and
                    comp['y'] + comp['h'] <= zone['y'] + zone['h'] + 5):
                contained = True
                break

        if not contained:
            issues.append({
                'type': 'box_outside_zone',
                'severity': 'warn',
                'box_position': f"({comp['x']:.0f},{comp['y']:.0f})",
                'box_size': f"{comp['w']:.0f}x{comp['h']:.0f}",
                'message': 'Component box not contained within any zone rect',
            })
    return issues


def check_has_title(html_content, svg_index):
    """Check that the SVG section has an h2 title."""
    # Find all h2 elements and SVG positions
    h2s = list(re.finditer(r'<h2[^>]*>(.*?)</h2>', html_content, re.DOTALL))
    svgs = list(re.finditer(r'<svg[^>]*>', html_content))

    if svg_index >= len(svgs):
        return []

    svg_pos = svgs[svg_index].start()
    # Find nearest h2 before this SVG
    found = False
    for h2 in reversed(h2s):
        if h2.start() < svg_pos:
            found = True
            break

    if not found:
        return [{'type': 'missing_title', 'severity': 'warn',
                 'message': f'SVG {svg_index + 1} has no preceding h2 title'}]
    return []


# ---------------------------------------------------------------------------
# C4 Semantic Checks
# ---------------------------------------------------------------------------

# Vague relationship labels that don't convey meaningful information
_VAGUE_LABELS = {'uses', 'calls', 'sends', 'reads', 'writes', 'gets', 'sets',
                 'connects', 'talks to', 'communicates with', 'depends on'}


def check_c4_elements_have_metadata(elements, strict=False):
    """Every element with data-c4-type must have name and description."""
    issues = []
    for r in elements['rects']:
        c4_type = r.get('c4_type', '')
        if not c4_type:
            continue
        c4_name = r.get('c4_name', '')
        c4_desc = r.get('c4_description', '')
        missing = []
        if not c4_name:
            missing.append('name')
        if not c4_desc:
            missing.append('description')
        if missing:
            issues.append({
                'type': 'c4_elements_have_metadata',
                'severity': 'fail' if strict else 'warn',
                'c4_type': c4_type,
                'c4_name': c4_name or '(unnamed)',
                'missing': ', '.join(missing),
            })
    return issues


def check_c4_containers_have_technology(elements, strict=False):
    """Container and component elements need a technology annotation."""
    issues = []
    for r in elements['rects']:
        c4_type = r.get('c4_type', '').lower()
        if c4_type not in ('container', 'component'):
            continue
        if not r.get('c4_technology', ''):
            issues.append({
                'type': 'c4_containers_have_technology',
                'severity': 'fail' if strict else 'warn',
                'c4_type': c4_type,
                'c4_name': r.get('c4_name', '(unnamed)'),
                'message': f'{c4_type} missing technology annotation',
            })
    return issues


def check_c4_relationships_labeled(elements, strict=False):
    """Relationships must have non-empty, specific labels."""
    issues = []
    for p in elements['paths']:
        label = p.get('c4_label', '')
        if not label:
            continue  # unlabeled arrows handled by label_completeness check
        if label.strip().lower() in _VAGUE_LABELS:
            issues.append({
                'type': 'c4_relationships_labeled',
                'severity': 'fail' if strict else 'warn',
                'label': label,
                'message': f'Vague relationship label "{label}" - be more specific',
            })
    for ln in elements['lines']:
        label = ln.get('c4_label', '')
        if label and label.strip().lower() in _VAGUE_LABELS:
            issues.append({
                'type': 'c4_relationships_labeled',
                'severity': 'fail' if strict else 'warn',
                'label': label,
                'message': f'Vague relationship label "{label}" - be more specific',
            })
    return issues


def check_c4_level_consistency(elements, strict=False):
    """No cross-level element mixing (e.g., components in a context diagram)."""
    issues = []
    level = elements.get('c4_level', '').lower()
    if not level:
        return issues

    # Define what types are allowed at each level
    allowed = {
        'context': {'person', 'software system', 'software-system', 'software_system',
                     'external system', 'external-system', 'external_system',
                     'enterprise boundary'},
        'container': {'person', 'software system', 'software-system', 'software_system',
                      'external system', 'external-system', 'external_system',
                      'container', 'container-db', 'database', 'boundary'},
        'component': {'person', 'software system', 'software-system', 'software_system',
                      'external system', 'external-system', 'external_system',
                      'container', 'container-db', 'component', 'database', 'boundary'},
    }

    level_allowed = allowed.get(level)
    if not level_allowed:
        return issues

    for r in elements['rects']:
        c4_type = r.get('c4_type', '').lower()
        if not c4_type:
            continue
        if c4_type not in level_allowed:
            issues.append({
                'type': 'c4_level_consistency',
                'severity': 'fail' if strict else 'warn',
                'c4_level': level,
                'c4_type': c4_type,
                'c4_name': r.get('c4_name', '(unnamed)'),
                'message': f'"{c4_type}" element not expected in {level}-level diagram',
            })
    return issues


def check_c4_has_boundary(elements, strict=False):
    """Container and component diagrams should have boundary rects."""
    issues = []
    level = elements.get('c4_level', '').lower()
    if level not in ('container', 'component'):
        return issues

    # Look for boundary rects (large rects with dashed stroke or c4_type=boundary)
    has_boundary = False
    for r in elements['rects']:
        c4_type = r.get('c4_type', '').lower()
        if 'boundary' in c4_type:
            has_boundary = True
            break
        # Heuristic: large rect with dashed stroke could be boundary
        if r.get('stroke') and r['w'] > 400 and r['h'] > 300:
            has_boundary = True
            break

    if not has_boundary:
        issues.append({
            'type': 'c4_has_boundary',
            'severity': 'fail' if strict else 'warn',
            'c4_level': level,
            'message': f'{level}-level diagram should have a system boundary rect',
        })
    return issues


def check_c4_title_format(elements, html_content, strict=False):
    """Title should match C4 naming convention: '<Level> diagram for <Scope>'."""
    issues = []
    c4_level = elements.get('c4_level', '')
    c4_scope = elements.get('c4_scope', '')
    if not c4_level:
        return issues

    # Find h2 titles
    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html_content, re.DOTALL)
    # Also check <title>
    titles = re.findall(r'<title>(.*?)</title>', html_content, re.DOTALL)

    all_titles = h2s + titles
    # Expected pattern: "System Context diagram for X" or "Container diagram for X"
    expected_patterns = [
        rf'(?i){re.escape(c4_level)}.*diagram.*for',
        rf'(?i).*diagram.*{re.escape(c4_level)}',
    ]

    has_c4_title = False
    for title in all_titles:
        title_clean = re.sub(r'<[^>]+>', '', title).strip()
        for pat in expected_patterns:
            if re.search(pat, title_clean):
                has_c4_title = True
                break
        if has_c4_title:
            break

    if not has_c4_title:
        issues.append({
            'type': 'c4_title_format',
            'severity': 'fail' if strict else 'warn',
            'c4_level': c4_level,
            'titles_found': [re.sub(r'<[^>]+>', '', t).strip() for t in all_titles[:3]],
            'message': f'Title should follow C4 format: "{c4_level.title()} diagram for <scope>"',
        })
    return issues


def check_c4_has_legend(elements, strict=False):
    """C4 diagrams should include a legend/key."""
    issues = []
    if not elements.get('c4_level'):
        return issues

    # Look for legend-like text in the SVG
    legend_keywords = {'legend', 'key', 'person', 'software system', 'external system',
                       'container', 'component'}
    legend_text_count = 0
    for t in elements['texts']:
        if t['text'].strip().lower() in legend_keywords:
            legend_text_count += 1

    # A legend typically has 3+ keyword matches clustered together
    if legend_text_count < 3:
        issues.append({
            'type': 'c4_has_legend',
            'severity': 'fail' if strict else 'warn',
            'message': 'C4 diagram should include a legend/key explaining element types',
        })
    return issues


def check_c4_externals_distinct(elements, strict=False):
    """External elements should use gray fill, not blue (which denotes internal)."""
    issues = []
    # C4 convention: internal = blue (#1168BD), external = gray (#999999)
    blue_fills = {'#1168bd', '#438dd5', '#08427b', '#085bbf'}

    for r in elements['rects']:
        c4_type = r.get('c4_type', '').lower().replace('_', '-')
        if 'external' not in c4_type:
            continue
        fill = r.get('fill', '').lower()
        if fill in blue_fills:
            issues.append({
                'type': 'c4_externals_distinct',
                'severity': 'fail' if strict else 'warn',
                'c4_name': r.get('c4_name', '(unnamed)'),
                'fill': fill,
                'message': 'External element uses blue fill - should be gray (#999999) to distinguish from internal',
            })
    return issues


C4_CHECKS = [
    ('c4_elements_have_metadata', check_c4_elements_have_metadata),
    ('c4_containers_have_technology', check_c4_containers_have_technology),
    ('c4_relationships_labeled', check_c4_relationships_labeled),
    ('c4_level_consistency', check_c4_level_consistency),
    ('c4_has_boundary', check_c4_has_boundary),
    ('c4_has_legend', check_c4_has_legend),
    ('c4_externals_distinct', check_c4_externals_distinct),
]

# C4 checks that need html_content (handled separately like check_has_title)
C4_CHECKS_HTML = [
    ('c4_title_format', check_c4_title_format),
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    ('text_in_bounds', check_text_in_bounds),
    ('text_overlap', check_text_overlap),
    ('arrow_routing', check_arrow_routing),
    ('arrow_convergence', check_arrow_convergence),
    ('arrow_through_text', check_arrow_through_text),
    ('consistent_spacing', check_consistent_spacing),
    ('whitespace_balance', check_whitespace_balance),
    ('label_completeness', check_label_completeness),
    ('font_consistency', check_font_consistency),
    ('color_consistency', check_color_consistency),
    ('box_containment', check_box_containment),
    ('label_density', check_label_density),
    ('zone_label_clearance', check_zone_label_clearance),
]


def validate_svg(html_path, json_output=False, c4_mode=False, strict=False):
    """Run all SVG checks on each SVG in the HTML file."""
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    svg_strings = extract_svgs(html_path)
    if not svg_strings:
        print("No SVG elements found.", file=sys.stderr)
        sys.exit(1)

    report = {'file': html_path, 'svgs': []}
    overall_status = 'pass'

    for i, svg_str in enumerate(svg_strings):
        elements = parse_svg_elements(svg_str)
        if elements is None:
            continue

        svg_report = {
            'index': i,
            'rects': len(elements['rects']),
            'texts': len(elements['texts']),
            'lines': len(elements['lines']),
            'paths': len(elements['paths']),
            'issues': [],
        }

        for check_name, check_fn in ALL_CHECKS:
            svg_report['issues'].extend(check_fn(elements))

        # Title check needs html content
        svg_report['issues'].extend(check_has_title(html_content, i))

        # C4 semantic checks (auto-detect or explicit --c4 flag)
        is_c4 = c4_mode or bool(elements.get('c4_level'))
        if is_c4:
            for check_name, check_fn in C4_CHECKS:
                svg_report['issues'].extend(check_fn(elements, strict=strict))
            for check_name, check_fn in C4_CHECKS_HTML:
                svg_report['issues'].extend(check_fn(elements, html_content, strict=strict))

        # Escalate to FAIL when warning count is high (visual review correlation:
        # diagrams with 10+ warnings consistently scored < 5/10)
        warn_count = sum(1 for iss in svg_report['issues'] if iss['severity'] == 'warn')
        if warn_count >= 10:
            for iss in svg_report['issues']:
                if iss['severity'] == 'warn':
                    iss['severity'] = 'fail'
            svg_report['issues'].append({
                'type': 'quality_threshold',
                'severity': 'fail',
                'message': f'{warn_count} issues detected - diagram needs significant rework',
            })

        # Status
        severities = [iss['severity'] for iss in svg_report['issues']]
        if 'fail' in severities:
            svg_report['status'] = 'FAIL'
            overall_status = 'fail'
        elif 'warn' in severities:
            svg_report['status'] = 'WARN'
            if overall_status != 'fail':
                overall_status = 'warn'
        else:
            svg_report['status'] = 'PASS'

        report['svgs'].append(svg_report)

    report['status'] = overall_status.upper()

    if json_output:
        print(json.dumps(report, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"SVG Validation: {html_path}")
        print(f"{'='*60}")
        for svg in report['svgs']:
            icon = {'PASS': 'OK', 'WARN': '!!', 'FAIL': 'XX'}[svg['status']]
            print(f"\n[{icon}] SVG {svg['index'] + 1}")
            print(f"    Elements: {svg['rects']} rects, {svg['texts']} texts, "
                  f"{svg['lines']} lines, {svg['paths']} paths")
            if not svg['issues']:
                print(f"    No issues found")
            else:
                by_type = {}
                for iss in svg['issues']:
                    by_type.setdefault(iss['type'], []).append(iss)
                for itype, items in by_type.items():
                    print(f"\n    {itype} ({len(items)}):")
                    for item in items[:5]:
                        detail = ', '.join(f'{k}={v}' for k, v in item.items()
                                           if k not in ('type', 'severity'))
                        print(f"      - {detail}")
                    if len(items) > 5:
                        print(f"      ... and {len(items)-5} more")
        print(f"\n{'='*60}")
        print(f"Overall: {report['status']}")
        print(f"{'='*60}\n")

    if overall_status == 'fail':
        sys.exit(1)
    elif overall_status == 'warn':
        sys.exit(2)
    else:
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Validate SVG diagram quality in HTML files')
    parser.add_argument('html_file', help='Path to HTML file with SVG diagrams')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of human-readable')
    parser.add_argument('--c4', action='store_true', help='Enable C4 semantic validation checks')
    parser.add_argument('--strict', action='store_true', help='Escalate C4 warnings to failures')
    args = parser.parse_args()
    validate_svg(args.html_file, args.json, c4_mode=args.c4, strict=args.strict)


if __name__ == '__main__':
    main()
