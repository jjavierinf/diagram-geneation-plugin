# diagram-tools

Claude Code plugin for creating and exporting architecture diagrams.

## Skills included

| Skill | Purpose |
|-------|---------|
| `architecture-diagram-creator` | Create comprehensive HTML/SVG architecture diagrams (data flows, system layers, deployment) |
| `diagram-exporter` | Export HTML/SVG diagrams to PowerPoint (PPTX) or editable Draw.io files |

## Installation

```bash
/plugin install github:jjavierinf/diagram-geneation-plugin
```

Then run the setup script **once** to install Python and Node.js dependencies:

```bash
~/.claude/plugins/cache/github/jjavierinf/diagram-geneation-plugin/*/setup.sh
```

> Or if you cloned the repo manually: `bash /path/to/diagram-generation-plugin/setup.sh`

## Requirements

- Python 3.8+
- Node.js 18+
- pip
- npm

## Usage

### Create a diagram

Just ask Claude:

> "Create an architecture diagram for my data pipeline"

Claude will use `architecture-diagram-creator` to generate a self-contained HTML file with SVG diagrams.

### Export to PowerPoint

```bash
python3 ~/.claude/plugins/cache/github/jjavierinf/diagram-geneation-plugin/*/skills/diagram-exporter/scripts/svg2pptx.py \
  my-diagram.html \
  output.pptx
```

Or just tell Claude: `"Export this diagram to PPTX"`

### Export to Draw.io

```bash
python3 ~/.claude/plugins/cache/github/jjavierinf/diagram-geneation-plugin/*/skills/diagram-exporter/scripts/svg2drawio.py \
  my-diagram.html \
  output.drawio
```

## Development

Clone and symlink to work on the plugin locally:

```bash
git clone git@github.com:jjavierinf/diagram-geneation-plugin.git ~/repos/diagram-generation-plugin
```

The `skills/diagram-exporter/calibration/` directory contains calibration infrastructure for iterating on diagram quality. Run the calibration loop with:

```bash
cat skills/diagram-exporter/calibration/ralph-loop-prompt.md
# Then: /ralph-loop "<prompt>" --max-iterations 30
```

## License

MIT
