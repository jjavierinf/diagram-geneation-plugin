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
