# Technical Discovery Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a `technical-discovery` skill that explores available sources (code, Confluence, Jira, memory), consolidates findings into structured markdown, and asks the user only when critical info cannot be inferred.

**Architecture:** A single SKILL.md file with clear instructions for source detection, parallel exploration, consolidation with code-as-truth priority, and structured markdown output. The `architecture-diagram-creator` SKILL.md gets a one-line addition pointing to this skill as a pre-step.

**Tech Stack:** Markdown (SKILL.md), no code — this is a prompt-engineering skill that orchestrates existing tools and skills.

---

### Task 1: Create the technical-discovery SKILL.md

**Files:**
- Create: `skills/technical-discovery/SKILL.md`

**Step 1: Create the skill directory**

```bash
mkdir -p ~/repos/diagram-generation-plugin/skills/technical-discovery
```

**Step 2: Write SKILL.md**

Create `skills/technical-discovery/SKILL.md` with the following content:

```markdown
---
name: technical-discovery
description: Explore code, docs, and project context to produce structured technical documentation. Use before creating architecture diagrams when documentation is sparse or absent. Triggers on "analyze system", "document architecture", "technical discovery", or when architecture-diagram-creator lacks clear input.
---

# Technical Discovery

Explore all available sources to produce a structured technical document — the single source of truth for a system's architecture. Use this before creating diagrams when documentation is sparse, inconsistent, or absent.

## When to Use

- Before creating an architecture diagram and there is no clear documentation
- "Analyze the system/project/codebase"
- "Document the architecture of X"
- "What does this system do?"
- Called by `architecture-diagram-creator` when input context is insufficient

## Workflow

### Phase 1: Detect Available Sources

Check what is available — use what exists, never mention what does not:

| Source | Detection | What to extract |
|--------|-----------|----------------|
| Code | Always available (glob, grep, read) | imports, configs, DAG definitions, SQL DDLs, README, directory structure, connection strings, environment variables |
| Confluence | `confluence-explorer` skill exists | relevant pages, tables, data models, attachments |
| Jira | `jira-explorer` skill exists | ticket descriptions, comments, epic context, linked architecture docs |
| Memory | `mem-search` skill exists | previous session findings, decisions, architecture notes |

### Phase 2: Parallel Exploration (Silent)

Explore all detected sources in parallel. Do NOT ask the user anything yet. For each source:

**Code (always):**
1. Read README if exists
2. Glob for config files (*.yaml, *.yml, *.json, *.ini, *.env.example)
3. Glob for entry points (dag_*.py, main.py, app.py, index.*, Dockerfile)
4. Grep for connection strings, database references, API endpoints
5. Grep for imports to identify frameworks and libraries
6. Read SQL DDLs for table structures
7. Map directory structure for component boundaries

**Confluence (if available):**
1. Search for pages matching system/project name
2. Extract architecture sections, data models, flow descriptions
3. Download relevant diagrams/attachments

**Jira (if available):**
1. Search for epic or project tickets
2. Extract architecture decisions from comments
3. Note linked Confluence pages

**Memory (if available):**
1. Search for system name, related components
2. Retrieve previous architecture decisions

### Phase 3: Consolidate

Cross-reference all sources. Rules:

1. **Code is the source of truth.** If Confluence says service A connects to DB via REST but code shows JDBC — use JDBC, note the inconsistency.
2. **Flag contradictions** in the "Inconsistencies Found" section. Do not silently pick one.
3. **Identify critical gaps** — components with unclear connections, ambiguous data flows, technology choices that cannot be inferred.

### Phase 4: Ask (Only If Necessary)

Only ask if a piece of information is:
- **Critical for the diagram** (will appear as a component, connection, or label)
- **Cannot be inferred from code** (ambiguous imports, multiple possible paths, business logic)

Rules:
- Maximum 5 questions in a single message
- Each question includes context explaining WHY you need it
- Format: numbered list
- Example: "1. Service X imports both `psycopg2` and `requests` — does it connect to the DB directly or via an API gateway? (this determines whether to show a direct DB connection or an intermediary)"

If everything can be inferred: skip this phase entirely, write the output directly.

### Phase 5: Output

Write the discovery document:

- **Default:** `current_task/<system-name>-discovery.md`
- **If user asked for documentation:** `docs/<system-name>-architecture.md`

Then return to the calling skill (or the user) with the file path.

## Output Format

```markdown
# [System Name] — Technical Discovery

## Components
<!-- One line per component: name, technology, responsibility -->

## Connections
<!-- Component A → Component B: protocol/method, what data flows -->

## Data Flow
<!-- End-to-end: source → processing → destination -->

## Technologies
<!-- Stack summary: languages, frameworks, DBs, queues, cloud services -->

## External Integrations
<!-- External systems, APIs, third-party services -->

## Inconsistencies Found
<!-- "Confluence says X but code shows Y — used Y (code is truth)" -->
<!-- Omit section if no inconsistencies -->

## Decisions & Clarifications
<!-- Questions asked to user and their answers -->
<!-- Omit section if no questions were needed -->
```

Omit any section that does not apply.

## Important

- Never mention sources you cannot access. If there is no Confluence skill, do not say "I could not check Confluence."
- Code is always the truth. Other sources provide context and intent.
- Keep the output concise. One line per component, one line per connection. This is input for a diagram, not a novel.
- If the user asked for a diagram and you ran discovery first, hand off to `architecture-diagram-creator` with the discovery file path after writing it.
```

**Step 3: Verify the file**

```bash
cat ~/repos/diagram-generation-plugin/skills/technical-discovery/SKILL.md | head -5
```

Expected: the frontmatter block with `name: technical-discovery`.

**Step 4: Commit**

```bash
cd ~/repos/diagram-generation-plugin
git add skills/technical-discovery/SKILL.md
git commit -m "feat: add technical-discovery skill"
```

---

### Task 2: Update architecture-diagram-creator to reference technical-discovery

**Files:**
- Modify: `skills/architecture-diagram-creator/SKILL.md:74-82`

**Step 1: Add discovery reference to the Workflow section**

In `skills/architecture-diagram-creator/SKILL.md`, the current Workflow section (lines 74-82) reads:

```markdown
## Workflow

1. Analyze project (README, code structure)
2. Extract: purpose, data sources, processing, tech stack, outputs
3. Create HTML with all 6 sections
4. Use semantic colors for visual hierarchy
5. Write to `[project]-architecture.html`
```

Replace it with:

```markdown
## Workflow

0. **If documentation is sparse or absent:** run the `technical-discovery` skill first. It will produce a structured markdown file you can use as input for the diagram.
1. Analyze project (README, code structure, or discovery document from step 0)
2. Extract: purpose, data sources, processing, tech stack, outputs
3. Create HTML with all 6 sections
4. Use semantic colors for visual hierarchy
5. Write to `[project]-architecture.html`
```

**Step 2: Verify the change**

```bash
grep -n "technical-discovery" ~/repos/diagram-generation-plugin/skills/architecture-diagram-creator/SKILL.md
```

Expected: one match in the Workflow section.

**Step 3: Commit**

```bash
cd ~/repos/diagram-generation-plugin
git add skills/architecture-diagram-creator/SKILL.md
git commit -m "feat: reference technical-discovery as pre-step in diagram creator"
```

---

### Task 3: Update plugin.json (if skill registration needed)

**Files:**
- Read: `.claude-plugin/plugin.json`

**Step 1: Check if skills are registered in plugin.json**

```bash
cat ~/repos/diagram-generation-plugin/.claude-plugin/plugin.json
```

If skills are listed explicitly, add `technical-discovery`. If skills are auto-discovered from the `skills/` directory, no change needed.

**Step 2: Commit if changed**

```bash
cd ~/repos/diagram-generation-plugin
git add .claude-plugin/plugin.json
git commit -m "feat: register technical-discovery skill in plugin.json"
```

Skip this step if no change needed.

---

### Task 4: Smoke Test

**Files:** (no changes, verification only)

**Step 1: Verify skill is discoverable**

```bash
ls ~/repos/diagram-generation-plugin/skills/technical-discovery/SKILL.md
```

Expected: file exists.

**Step 2: Verify SKILL.md parses correctly**

```bash
head -4 ~/repos/diagram-generation-plugin/skills/technical-discovery/SKILL.md
```

Expected: valid YAML frontmatter.

**Step 3: Verify diagram-creator references discovery**

```bash
grep "technical-discovery" ~/repos/diagram-generation-plugin/skills/architecture-diagram-creator/SKILL.md
```

Expected: one match.

**Step 4: Push**

```bash
cd ~/repos/diagram-generation-plugin
git push origin main
```
