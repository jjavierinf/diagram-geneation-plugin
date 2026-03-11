#!/bin/bash
# Setup script for diagram-tools plugin
# Run once after installing the plugin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Installing Python dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

echo "==> Installing Node.js dependencies..."
cd "$SCRIPT_DIR"
npm install

echo ""
echo "Setup complete. You can now use:"
echo "  - architecture-diagram-creator skill: generate HTML/SVG architecture diagrams"
echo "  - diagram-exporter skill: export diagrams to PPTX or Draw.io"
