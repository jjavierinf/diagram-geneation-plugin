#!/bin/bash
# render_drawio.sh - Render each tab of a .drawio file to PNG using real draw.io engine
#
# Usage: ./render_drawio.sh <input.drawio> <output-dir>
#
# Requires: draw.io-export (npm) from ~/repos/dags/node_modules/
# The draw.io-export CLI only renders the first tab, so this script
# splits multi-tab files into separate files and renders each.
#
# Output: PNG files named tab1.png, tab2.png, etc. at 2x scale

set -euo pipefail

INPUT="${1:?Usage: render_drawio.sh <input.drawio> <output-dir>}"
OUTDIR="${2:?Usage: render_drawio.sh <input.drawio> <output-dir>}"

mkdir -p "$OUTDIR"

# Split into individual files
python3 - "$INPUT" "$OUTDIR" <<'PYEOF'
import sys, xml.etree.ElementTree as ET
inp, outdir = sys.argv[1], sys.argv[2]
tree = ET.parse(inp)
root = tree.getroot()
diagrams = root.findall('diagram')
print(len(diagrams))
for i, d in enumerate(diagrams):
    new_root = ET.Element('mxfile')
    new_root.append(d)
    ET.ElementTree(new_root).write(f'{outdir}/_tab{i}.drawio', xml_declaration=True, encoding='UTF-8')
    print(f'  Tab {i+1}: {d.get("name", "untitled")}', file=sys.stderr)
PYEOF

# Read number of tabs from first line of python output
NUM_TABS=$(python3 -c "
import xml.etree.ElementTree as ET, sys
print(len(ET.parse(sys.argv[1]).getroot().findall('diagram')))
" "$INPUT")

echo "Found $NUM_TABS tab(s) in $(basename "$INPUT")"

for i in $(seq 0 $((NUM_TABS - 1))); do
    tab_num=$((i + 1))
    echo "Rendering tab $tab_num..."
    HTTPS_PROXY="" npx drawio "$OUTDIR/_tab${i}.drawio" -o "$OUTDIR/tab${tab_num}.png" -s 2 2>/dev/null
    rm -f "$OUTDIR/_tab${i}.drawio"
done

echo ""
echo "Renders saved to $OUTDIR/"
ls -la "$OUTDIR"/tab*.png
