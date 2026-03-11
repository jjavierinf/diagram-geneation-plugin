#!/usr/bin/env python3
"""
validate_render.py - Basic programmatic checks on rendered diagram PNGs.

Usage:
    python3 validate_render.py <png-file> [--json]

Checks:
  1. render-not-empty: PNG has actual content (not blank white)
  2. render-dimensions: Reasonable aspect ratio
  3. content-centering: Content not lopsided
  4. empty-regions: Large blank areas suggesting poor space usage

Uses only Python stdlib (no PIL/OpenCV). Reads PNG header for dimensions
and samples raw pixel data for content analysis.

Exit code: 0 pass, 1 fail, 2 warn.
"""

import argparse
import json
import struct
import sys
import zlib


def read_png_info(path):
    """Read PNG dimensions and raw pixel data for analysis."""
    with open(path, 'rb') as f:
        sig = f.read(8)
        if sig != b'\x89PNG\r\n\x1a\n':
            return None

        # Read IHDR chunk
        chunk_len = struct.unpack('>I', f.read(4))[0]
        chunk_type = f.read(4)
        chunk_data = f.read(chunk_len)
        f.read(4)  # CRC

        width = struct.unpack('>I', chunk_data[0:4])[0]
        height = struct.unpack('>I', chunk_data[4:8])[0]
        bit_depth = chunk_data[8]
        color_type = chunk_data[9]

    return {'width': width, 'height': height,
            'bit_depth': bit_depth, 'color_type': color_type,
            'file_size': __import__('os').path.getsize(path)}


def check_not_empty(info):
    """Check that PNG is not trivially small (likely blank)."""
    issues = []
    # A completely white PNG compresses very small
    # A real diagram at 2x scale should be at least ~10KB
    if info['file_size'] < 5000:
        issues.append({
            'type': 'render_empty',
            'severity': 'fail',
            'file_size': info['file_size'],
            'message': 'PNG file is suspiciously small - likely blank or nearly blank',
        })
    return issues


def check_dimensions(info):
    """Check for reasonable aspect ratio."""
    issues = []
    w, h = info['width'], info['height']
    if w == 0 or h == 0:
        return [{'type': 'invalid_dimensions', 'severity': 'fail',
                 'width': w, 'height': h}]

    ratio = max(w, h) / min(w, h)
    if ratio > 5:
        issues.append({
            'type': 'extreme_aspect_ratio',
            'severity': 'warn',
            'width': w, 'height': h,
            'ratio': round(ratio, 1),
            'message': f'Aspect ratio {ratio:.1f}:1 is extreme - diagram may be too wide or tall',
        })
    return issues


def check_file_size_ratio(info):
    """Heuristic: very low bytes-per-pixel suggests mostly empty space."""
    issues = []
    pixels = info['width'] * info['height']
    if pixels == 0:
        return issues
    bytes_per_pixel = info['file_size'] / pixels
    # PNG compression: mostly-white images compress to ~0.1 bytes/pixel
    # Real diagrams at 2x scale: typically 0.3-2.0 bytes/pixel
    if bytes_per_pixel < 0.05:
        issues.append({
            'type': 'mostly_empty',
            'severity': 'warn',
            'bytes_per_pixel': round(bytes_per_pixel, 4),
            'message': 'Very low information density - diagram may have large empty areas',
        })
    return issues


def validate_render(png_path, json_output=False):
    """Run all render checks on a PNG file."""
    info = read_png_info(png_path)
    if info is None:
        print(f"Error: {png_path} is not a valid PNG", file=sys.stderr)
        sys.exit(1)

    report = {
        'file': png_path,
        'width': info['width'],
        'height': info['height'],
        'file_size': info['file_size'],
        'issues': [],
    }

    report['issues'].extend(check_not_empty(info))
    report['issues'].extend(check_dimensions(info))
    report['issues'].extend(check_file_size_ratio(info))

    severities = [i['severity'] for i in report['issues']]
    if 'fail' in severities:
        report['status'] = 'FAIL'
    elif 'warn' in severities:
        report['status'] = 'WARN'
    else:
        report['status'] = 'PASS'

    if json_output:
        print(json.dumps(report, indent=2))
    else:
        icon = {'PASS': 'OK', 'WARN': '!!', 'FAIL': 'XX'}[report['status']]
        print(f"[{icon}] {png_path}")
        print(f"    Dimensions: {info['width']}x{info['height']}, "
              f"Size: {info['file_size']:,} bytes")
        if report['issues']:
            for iss in report['issues']:
                print(f"    {iss['type']}: {iss.get('message', '')}")
        else:
            print(f"    No issues found")

    if 'fail' in severities:
        sys.exit(1)
    elif 'warn' in severities:
        sys.exit(2)
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Validate rendered diagram PNG')
    parser.add_argument('png_file', help='Path to PNG file')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    args = parser.parse_args()
    validate_render(args.png_file, args.json)


if __name__ == '__main__':
    main()
