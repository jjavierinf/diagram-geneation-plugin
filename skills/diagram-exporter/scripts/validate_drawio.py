#!/usr/bin/env python3
"""
validate_drawio.py - Programmatic quality checks for .drawio files.

Usage:
    python3 validate_drawio.py <drawio-file> [--source-html <html-file>]

Checks:
  1. Cell overlap detection (bounding box intersection with draw.io padding)
  2. Empty/missing labels on vertex cells
  3. Orphan edges (source/target pointing to non-existent cells)
  4. Font legibility (font size too small for draw.io)
  5. Text completeness vs source SVG (optional, needs --source-html)
  6. Cell out of bounds (negative coordinates or extremely large)

Output: JSON report to stdout with pass/warn/fail per check.
Exit code: 0 if all pass, 1 if any fail, 2 if any warn.
"""

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser


# ---------------------------------------------------------------------------
# DrawIO XML Parser
# ---------------------------------------------------------------------------

DRAWIO_INTERNAL_PADDING = 5  # draw.io adds ~5px padding inside each cell


class Cell:
    """Parsed mxCell with geometry and style."""
    def __init__(self, cell_el):
        self.id = cell_el.get('id', '')
        self.value = cell_el.get('value', '')
        self.style = cell_el.get('style', '')
        self.is_vertex = cell_el.get('vertex') == '1'
        self.is_edge = cell_el.get('edge') == '1'
        self.source = cell_el.get('source', '')
        self.target = cell_el.get('target', '')
        self.parent = cell_el.get('parent', '')

        geo = cell_el.find('mxGeometry')
        if geo is not None:
            self.x = float(geo.get('x', 0))
            self.y = float(geo.get('y', 0))
            self.w = float(geo.get('width', 0))
            self.h = float(geo.get('height', 0))
        else:
            self.x = self.y = self.w = self.h = 0

    @property
    def has_geometry(self):
        return self.w > 0 and self.h > 0

    @property
    def plain_text(self):
        """Strip HTML tags from value to get plain text."""
        return strip_html(self.value)

    def get_style(self, key):
        m = re.search(rf'{key}=([^;]+)', self.style)
        return m.group(1) if m else None

    def is_zone(self):
        return (self.is_vertex and
                'opacity=' in self.style and
                'verticalAlign=top' in self.style)

    def is_text_label(self):
        return self.style.startswith('text;')

    def bbox(self, padding=0):
        """Return (x1, y1, x2, y2) bounding box with optional padding."""
        return (self.x - padding, self.y - padding,
                self.x + self.w + padding, self.y + self.h + padding)


def strip_html(s):
    """Remove HTML tags and decode entities."""
    # First decode drawio-escaped HTML entities
    s = s.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')

    class Stripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
        def handle_data(self, data):
            self.parts.append(data)

    stripper = Stripper()
    stripper.feed(s)
    return ' '.join(stripper.parts).strip()


def parse_drawio(path):
    """Parse a .drawio file and return list of (tab_name, [Cell]) tuples."""
    tree = ET.parse(path)
    root = tree.getroot()
    tabs = []
    for diagram in root.findall('diagram'):
        name = diagram.get('name', 'untitled')
        model = diagram.find('.//mxGraphModel')
        if model is None:
            # Try direct root element
            cells = diagram.findall('.//mxCell')
        else:
            cells = model.findall('.//mxCell')
        tabs.append((name, [Cell(c) for c in cells]))
    return tabs


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

def check_overlaps(cells, padding=DRAWIO_INTERNAL_PADDING):
    """Detect vertex cells whose bounding boxes overlap (with draw.io padding)."""
    issues = []
    vertices = [c for c in cells if c.is_vertex and c.has_geometry
                and not c.is_zone() and not c.is_text_label()]

    for i, a in enumerate(vertices):
        ax1, ay1, ax2, ay2 = a.bbox(padding)
        for b in vertices[i+1:]:
            bx1, by1, bx2, by2 = b.bbox(padding)

            # Skip containment pairs (one cell inside the other = nesting, not collision)
            # Use tolerance of padding to handle near-containment from draw.io spacing
            tol = padding
            a_contains_b = (a.x - tol <= b.x and a.y - tol <= b.y and
                            a.x + a.w + tol >= b.x + b.w and a.y + a.h + tol >= b.y + b.h)
            b_contains_a = (b.x - tol <= a.x and b.y - tol <= a.y and
                            b.x + b.w + tol >= a.x + a.w and b.y + b.h + tol >= a.y + a.h)
            if a_contains_b or b_contains_a:
                continue

            # Check intersection
            if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
                # Calculate overlap area
                ox = max(0, min(ax2, bx2) - max(ax1, bx1))
                oy = max(0, min(ay2, by2) - max(ay1, by1))
                overlap_area = ox * oy
                min_area = min(a.w * a.h, b.w * b.h)

                # Only report significant overlaps (>40% of smaller cell)
                if min_area > 0 and overlap_area / min_area > 0.4:
                    issues.append({
                        'type': 'overlap',
                        'severity': 'warn',
                        'cell_a': a.id,
                        'cell_b': b.id,
                        'text_a': a.plain_text[:50],
                        'text_b': b.plain_text[:50],
                        'overlap_pct': round(overlap_area / min_area * 100, 1),
                    })
    return issues


def check_empty_labels(cells):
    """Find vertex cells (non-zone, non-text) with empty labels."""
    issues = []
    for c in cells:
        if (c.is_vertex and c.has_geometry and
                not c.is_zone() and not c.is_text_label() and
                not c.plain_text.strip()):
            # Skip if it's a very small decorative element
            if c.w * c.h < 200:
                continue
            issues.append({
                'type': 'empty_label',
                'severity': 'warn',
                'cell_id': c.id,
                'position': f'({c.x}, {c.y})',
                'size': f'{c.w}x{c.h}',
            })
    return issues


def check_orphan_edges(cells):
    """Find edges whose source/target don't point to existing cell IDs."""
    issues = []
    cell_ids = {c.id for c in cells}
    for c in cells:
        if not c.is_edge:
            continue
        # Edges can use sourcePoint/targetPoint instead of source/target
        # Only flag if source/target is set but points to non-existent cell
        if c.source and c.source not in cell_ids:
            issues.append({
                'type': 'orphan_edge',
                'severity': 'fail',
                'cell_id': c.id,
                'missing': f'source={c.source}',
            })
        if c.target and c.target not in cell_ids:
            issues.append({
                'type': 'orphan_edge',
                'severity': 'fail',
                'cell_id': c.id,
                'missing': f'target={c.target}',
            })
    return issues


def check_font_legibility(cells, min_font=9):
    """Find cells with font size below minimum for draw.io readability."""
    issues = []
    for c in cells:
        if not c.is_vertex or not c.plain_text.strip():
            continue
        fs_str = c.get_style('fontSize')
        if fs_str:
            try:
                fs = float(fs_str)
                if fs < min_font:
                    issues.append({
                        'type': 'small_font',
                        'severity': 'warn',
                        'cell_id': c.id,
                        'text': c.plain_text[:40],
                        'font_size': fs,
                        'minimum': min_font,
                    })
            except ValueError:
                pass
    return issues


def check_unique_ids(cells):
    """Detect duplicate cell IDs."""
    issues = []
    seen = {}
    for c in cells:
        if c.id in seen:
            issues.append({
                'type': 'duplicate_id',
                'severity': 'fail',
                'cell_id': c.id,
                'first_text': seen[c.id].plain_text[:50],
                'second_text': c.plain_text[:50],
            })
        else:
            seen[c.id] = c
    return issues


def check_text_fits(cells):
    """Detect labels wider than their cell. For multi-line labels, check longest line."""
    issues = []
    for c in cells:
        if not c.is_vertex or not c.has_geometry or c.is_text_label():
            continue
        text = c.plain_text.strip()
        if not text:
            continue
        fs_str = c.get_style('fontSize')
        font_size = float(fs_str) if fs_str else 12.0
        # Split by line breaks (plain_text already stripped HTML, but check for common separators)
        lines = re.split(r'\s*\n\s*', text) if '\n' in text else [text]
        # Also check if the raw value has <br> tags (multi-line HTML label)
        if '<br' in c.value.lower() or '&lt;br' in c.value.lower():
            lines = [l.strip() for l in re.split(r'<br\s*/?>|&lt;br\s*/?>|&lt;br&gt;', c.value, flags=re.IGNORECASE)]
            lines = [strip_html(l) for l in lines if strip_html(l).strip()]
        estimated_width = max(len(line) * font_size * 0.6 for line in lines) if lines else 0
        if estimated_width > c.w * 1.5:
            issues.append({
                'type': 'text_overflow',
                'severity': 'warn',
                'cell_id': c.id,
                'text': text[:50],
                'estimated_width': round(estimated_width, 1),
                'cell_width': c.w,
            })
    return issues


def _parse_hex(color_str):
    """Parse a color string (#RGB, #RRGGBB, rgb(), rgba()) to (r, g, b) 0-255."""
    if not color_str:
        return None
    color_str = color_str.strip()
    # Handle rgb()/rgba()
    rgb_match = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', color_str)
    if rgb_match:
        return (int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3)))
    color_str = color_str.lstrip('#')
    # Handle 3-char hex
    if len(color_str) == 3:
        color_str = ''.join(ch * 2 for ch in color_str)
    if len(color_str) != 6:
        return None
    try:
        r = int(color_str[0:2], 16)
        g = int(color_str[2:4], 16)
        b = int(color_str[4:6], 16)
        return (r, g, b)
    except ValueError:
        return None


def _relative_luminance(rgb):
    """Compute WCAG relative luminance from (r, g, b) 0-255."""
    def linearize(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(rgb1, rgb2):
    """Compute WCAG contrast ratio between two (r, g, b) colors."""
    l1 = _relative_luminance(rgb1)
    l2 = _relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def check_color_contrast(cells, min_ratio=3.0):
    """WCAG AA contrast check between fontColor and fillColor."""
    issues = []
    for c in cells:
        if not c.is_vertex or c.is_text_label() or not c.plain_text.strip():
            continue
        font_color = _parse_hex(c.get_style('fontColor'))
        fill_color = _parse_hex(c.get_style('fillColor'))
        if font_color is None or fill_color is None:
            continue
        ratio = _contrast_ratio(font_color, fill_color)
        if ratio < min_ratio:
            issues.append({
                'type': 'low_contrast',
                'severity': 'fail' if ratio < 2.0 else 'warn',
                'cell_id': c.id,
                'text': c.plain_text[:50],
                'contrast_ratio': round(ratio, 2),
                'minimum': min_ratio,
                'font_color': c.get_style('fontColor'),
                'fill_color': c.get_style('fillColor'),
            })
    return issues


def check_duplicate_labels(cells):
    """Find sibling vertices (same parent) with identical labels. Skip zones."""
    issues = []
    # Group vertices by parent
    by_parent = {}
    for c in cells:
        if c.is_vertex and c.has_geometry and not c.is_zone() and not c.is_text_label():
            text = c.plain_text.strip()
            if text:
                by_parent.setdefault(c.parent, []).append(c)

    for parent_id, siblings in by_parent.items():
        seen = {}
        for c in siblings:
            text = c.plain_text.strip()
            if text in seen:
                issues.append({
                    'type': 'duplicate_label',
                    'severity': 'warn',
                    'cell_a': seen[text].id,
                    'cell_b': c.id,
                    'label': text[:80],
                    'parent': parent_id,
                })
            else:
                seen[text] = c
    return issues


def check_min_spacing(cells, min_gap=8):
    """Find vertex pairs that are close but not overlapping (gap 0-8px)."""
    issues = []
    vertices = [c for c in cells
                if c.is_vertex and c.has_geometry
                and not c.is_zone() and not c.is_text_label()]

    for i, a in enumerate(vertices):
        ax1, ay1, ax2, ay2 = a.bbox()
        for b in vertices[i+1:]:
            bx1, by1, bx2, by2 = b.bbox()

            # Compute gap on each axis
            gap_x = max(bx1 - ax2, ax1 - bx2)
            gap_y = max(by1 - ay2, ay1 - by2)

            # If either axis has negative gap (overlap), skip - handled by overlap check
            if gap_x < 0 and gap_y < 0:
                continue

            # Distance is the max of the two gaps if separated on that axis,
            # or 0 if they share an axis range
            gap = max(gap_x, 0) if gap_y < 0 else (
                  max(gap_y, 0) if gap_x < 0 else
                  math.sqrt(max(gap_x, 0)**2 + max(gap_y, 0)**2))

            if 0 <= gap < min_gap:
                issues.append({
                    'type': 'tight_spacing',
                    'severity': 'warn',
                    'cell_a': a.id,
                    'cell_b': b.id,
                    'text_a': a.plain_text[:50],
                    'text_b': b.plain_text[:50],
                    'gap_px': round(gap, 1),
                    'minimum': min_gap,
                })
    return issues


def check_out_of_bounds(cells, max_coord=5000):
    """Find cells with negative or extremely large coordinates."""
    issues = []
    for c in cells:
        if not c.is_vertex or not c.has_geometry:
            continue
        if c.x < -10 or c.y < -10 or c.x > max_coord or c.y > max_coord:
            issues.append({
                'type': 'out_of_bounds',
                'severity': 'warn',
                'cell_id': c.id,
                'text': c.plain_text[:40],
                'position': f'({c.x}, {c.y})',
            })
    return issues


def extract_svg_texts_per_tab(html_path):
    """Extract text elements from each SVG in the HTML, returning a list per SVG."""
    try:
        with open(html_path, 'r') as f:
            html_content = f.read()
    except (FileNotFoundError, PermissionError):
        return None

    # Split by SVG blocks
    svg_blocks = re.findall(r'<svg[^>]*>.*?</svg>', html_content, re.DOTALL)
    # Filter out tiny SVGs (legends, icons) matching converter behavior
    filtered_blocks = []
    for block in svg_blocks:
        w_match = re.search(r'\bwidth="(\d+)"', block[:200])
        h_match = re.search(r'\bheight="(\d+)"', block[:200])
        if w_match and h_match:
            w, h = int(w_match.group(1)), int(h_match.group(1))
            if w < 100 or h < 100:
                continue
        filtered_blocks.append(block)

    result = []
    for block in filtered_blocks:
        texts = set()
        # Match direct text content and tspan content
        for m in re.finditer(r'<text[^>]*>([^<]+)</text>', block):
            text = m.group(1).strip()
            if len(text) >= 3:
                texts.add(text.lower())
        for m in re.finditer(r'<tspan[^>]*>([^<]+)</tspan>', block):
            text = m.group(1).strip()
            if len(text) >= 3:
                texts.add(text.lower())
        result.append(texts)
    return result


def check_text_completeness(cells, svg_texts):
    """Compare drawio tab text content against source SVG text elements."""
    issues = []

    if not svg_texts:
        return issues

    # Collect all text from drawio cells
    drawio_texts = set()
    for c in cells:
        pt = c.plain_text.strip().lower()
        if pt:
            for part in re.split(r'\s*[|]\s*|\s*\n\s*', pt):
                if len(part) >= 3:
                    drawio_texts.add(part)

    # Find SVG texts missing from drawio
    missing = []
    for svg_text in svg_texts:
        found = any(svg_text in dt or dt in svg_text for dt in drawio_texts)
        if not found:
            missing.append(svg_text)

    if missing:
        pct_missing = len(missing) / max(len(svg_texts), 1) * 100
        if pct_missing > 20:
            issues.append({
                'type': 'text_completeness',
                'severity': 'warn',
                'missing_count': len(missing),
                'total_source': len(svg_texts),
                'pct_missing': round(pct_missing, 1),
                'examples': missing[:5],
            })

    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Validate .drawio file quality')
    parser.add_argument('drawio_file', help='Path to .drawio file')
    parser.add_argument('--source-html', help='Source HTML for text completeness check')
    parser.add_argument('--json', action='store_true', help='Output raw JSON (default: human-readable)')
    args = parser.parse_args()

    tabs = parse_drawio(args.drawio_file)

    # Extract per-SVG texts if source HTML provided
    svg_texts_per_tab = None
    if args.source_html:
        svg_texts_per_tab = extract_svg_texts_per_tab(args.source_html)

    report = {'file': args.drawio_file, 'tabs': []}
    overall_status = 'pass'

    for tab_idx, (tab_name, cells) in enumerate(tabs):
        tab_report = {
            'name': tab_name,
            'cell_count': len(cells),
            'vertices': len([c for c in cells if c.is_vertex]),
            'edges': len([c for c in cells if c.is_edge]),
            'issues': [],
        }

        # Run all checks
        tab_report['issues'].extend(check_unique_ids(cells))
        tab_report['issues'].extend(check_overlaps(cells))
        tab_report['issues'].extend(check_empty_labels(cells))
        tab_report['issues'].extend(check_orphan_edges(cells))
        tab_report['issues'].extend(check_font_legibility(cells))
        tab_report['issues'].extend(check_out_of_bounds(cells))
        tab_report['issues'].extend(check_text_fits(cells))
        tab_report['issues'].extend(check_color_contrast(cells))
        tab_report['issues'].extend(check_duplicate_labels(cells))
        tab_report['issues'].extend(check_min_spacing(cells))

        if svg_texts_per_tab and tab_idx < len(svg_texts_per_tab):
            tab_report['issues'].extend(
                check_text_completeness(cells, svg_texts_per_tab[tab_idx]))

        # Determine tab status
        severities = [i['severity'] for i in tab_report['issues']]
        if 'fail' in severities:
            tab_report['status'] = 'FAIL'
            overall_status = 'fail'
        elif 'warn' in severities:
            tab_report['status'] = 'WARN'
            if overall_status != 'fail':
                overall_status = 'warn'
        else:
            tab_report['status'] = 'PASS'

        report['tabs'].append(tab_report)

    report['status'] = overall_status.upper()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*60}")
        print(f"DrawIO Validation: {args.drawio_file}")
        print(f"{'='*60}")

        for tab in report['tabs']:
            status_icon = {'PASS': 'OK', 'WARN': '!!', 'FAIL': 'XX'}[tab['status']]
            print(f"\n[{status_icon}] Tab: {tab['name']}")
            print(f"    Cells: {tab['cell_count']} ({tab['vertices']} vertices, {tab['edges']} edges)")

            if not tab['issues']:
                print(f"    No issues found")
            else:
                by_type = {}
                for issue in tab['issues']:
                    by_type.setdefault(issue['type'], []).append(issue)

                for itype, items in by_type.items():
                    print(f"\n    {itype} ({len(items)}):")
                    for item in items[:5]:  # show max 5 per type
                        detail = _format_issue(item)
                        print(f"      - {detail}")
                    if len(items) > 5:
                        print(f"      ... and {len(items)-5} more")

        print(f"\n{'='*60}")
        print(f"Overall: {report['status']}")
        print(f"{'='*60}\n")

    # Exit code
    if overall_status == 'fail':
        sys.exit(1)
    elif overall_status == 'warn':
        sys.exit(2)
    else:
        sys.exit(0)


def _format_issue(issue):
    t = issue['type']
    if t == 'overlap':
        return (f"'{issue['text_a']}' overlaps '{issue['text_b']}' "
                f"({issue['overlap_pct']}% of smaller cell)")
    elif t == 'empty_label':
        return f"Cell {issue['cell_id']} at {issue['position']} ({issue['size']}) has no label"
    elif t == 'orphan_edge':
        return f"Edge {issue['cell_id']}: {issue['missing']} not found"
    elif t == 'small_font':
        return f"'{issue['text']}' font={issue['font_size']}px (min {issue['minimum']})"
    elif t == 'out_of_bounds':
        return f"'{issue['text']}' at {issue['position']}"
    elif t == 'text_completeness':
        if 'missing_count' in issue:
            return (f"{issue['missing_count']}/{issue['total_source']} texts missing "
                    f"({issue['pct_missing']}%): {issue.get('examples', [])}")
        return issue.get('message', str(issue))
    elif t == 'duplicate_id':
        return (f"ID '{issue['cell_id']}' used by '{issue['first_text']}' "
                f"and '{issue['second_text']}'")
    elif t == 'text_overflow':
        return (f"'{issue['text']}' est. {issue['estimated_width']}px "
                f"in cell {issue['cell_width']}px wide")
    elif t == 'low_contrast':
        return (f"'{issue['text']}' contrast {issue['contrast_ratio']}:1 "
                f"(min {issue['minimum']}:1) font={issue['font_color']} fill={issue['fill_color']}")
    elif t == 'duplicate_label':
        return (f"'{issue['label']}' on cells {issue['cell_a']} and {issue['cell_b']} "
                f"(parent {issue['parent']})")
    elif t == 'tight_spacing':
        return (f"'{issue['text_a']}' and '{issue['text_b']}' "
                f"gap={issue['gap_px']}px (min {issue['minimum']}px)")
    return str(issue)


if __name__ == '__main__':
    main()
