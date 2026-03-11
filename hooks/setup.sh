#!/bin/bash
# Setup hook for diagram-tools plugin
# Runs once on install: creates skill symlinks + installs Python/Node deps

set -e

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SKILLS_DIR="$HOME/.claude/skills"

echo "[diagram-tools] Setting up plugin..."

# --- Symlinks ---
mkdir -p "$SKILLS_DIR"

for skill in architecture-diagram-creator diagram-exporter; do
  SRC="$PLUGIN_ROOT/skills/$skill"
  DST="$SKILLS_DIR/$skill"
  if [ -L "$DST" ]; then
    echo "[diagram-tools] Symlink already exists: $DST"
  elif [ -e "$DST" ]; then
    echo "[diagram-tools] WARNING: $DST exists and is not a symlink — skipping"
  else
    ln -s "$SRC" "$DST"
    echo "[diagram-tools] Symlink created: $DST -> $SRC"
  fi
done

# --- Python deps ---
echo "[diagram-tools] Installing Python dependencies..."
pip install --quiet python-pptx Pillow

# --- Node deps ---
echo "[diagram-tools] Installing Node.js dependencies..."
cd "$PLUGIN_ROOT"
npm install --silent

echo "[diagram-tools] Setup complete."
