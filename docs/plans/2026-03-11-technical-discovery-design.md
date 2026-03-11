# Design: Technical Discovery Skill

**Date:** 2026-03-11
**Status:** Approved
**Repo:** diagram-generation-plugin

## Problem

The `architecture-diagram-creator` skill produces good diagrams when fed well-structured documentation (e.g., Confluence pages). But when documentation is sparse, inconsistent, or absent, it guesses — and the diagrams suffer. There is no systematic phase for understanding a system before diagramming it.

## Decision: Separate Discovery Skill (Approach A — Lightweight)

A new `technical-discovery` skill that runs a single-pass scan of all available sources, consolidates findings into a structured markdown file, and asks the user only when critical information cannot be inferred. The diagram-creator invokes it before graphing when no clear input doc exists.

## Architecture

```
User pide diagrama (o discovery directo)
  │
  ├─ Fase 1: Scan paralelo (silencioso)
  │   ├─ Codigo: imports, configs, DAG defs, SQL DDLs, README
  │   ├─ Confluence: si hay skill disponible, busca paginas relevantes
  │   ├─ Jira: si hay skill disponible, busca tickets del epic/proyecto
  │   └─ Memoria: si hay claude-mem, busca trabajo previo
  │
  ├─ Fase 2: Consolidar
  │   ├─ Cruza fuentes, codigo es la verdad
  │   ├─ Marca contradicciones (Confluence dice X, codigo dice Y → usa Y, avisa)
  │   └─ Identifica huecos criticos (componentes sin conexion clara, flujos ambiguos)
  │
  ├─ Fase 3: Preguntar (solo si hay huecos criticos)
  │   └─ Maximo 5 preguntas, solo cosas que van al diagrama y no se pueden inferir
  │
  └─ Fase 4: Output
      ├─ Escribe markdown a current_task/<system>-discovery.md (default)
      ├─ Si el usuario pidio documentacion: docs/<system>-architecture.md
      └─ Retorna al diagram-creator con el path del archivo
```

## Source Detection

The skill does not hardcode dependencies. At startup it checks what is available:

| Source | How detected | What it extracts |
|--------|-------------|-----------------|
| Code (always) | glob, grep, read | imports, configs, DAG defs, SQL DDLs, README, directory structure |
| Confluence | confluence-explorer skill exists | pages, tables, attachments, data models |
| Jira | jira-explorer skill exists | ticket descriptions, comments, attachments, epic context |
| Memory | mem-search skill exists | previous session findings, decisions, architecture notes |

If only code is available, it works with code. It never mentions missing sources — just uses what it has.

## Output Format

```markdown
# [System Name] — Technical Discovery

## Components
- Name, technology, responsibility (1 line each)

## Connections
- Component A → Component B: protocol/method, what data flows

## Data Flow
- Source → processing → destination (end-to-end pipeline)

## Technologies
- Stack summary (languages, frameworks, DBs, queues, cloud)

## External Integrations
- External systems, APIs, third-party services

## Inconsistencies Found
- "Confluence says X but code shows Y — used Y (code is truth)"

## Decisions & Clarifications
- Questions asked to user and their answers
```

Sections are optional — omitted if not applicable.

## Question Rules

- Only ask if the data is **critical for the diagram** and **cannot be inferred from code**
- Maximum 5 questions, all in a single message
- Format: numbered list with context explaining why the question matters
- Example: "1. Does service X connect to the DB via JDBC or API? (code imports both drivers but only uses one)"
- If everything can be inferred, no questions — write the markdown directly

## Integration with Diagram Creator

The `architecture-diagram-creator` SKILL.md gets a new line:

> If you don't have clear documentation of the system, use the `technical-discovery` skill first. It will produce a structured markdown file you can use as input.

The discovery skill is also usable standalone for documentation purposes.

## Files to Create

| File | Purpose |
|------|---------|
| `skills/technical-discovery/SKILL.md` | Skill instructions |

## Files to Modify

| File | Changes |
|------|---------|
| `skills/architecture-diagram-creator/SKILL.md` | Add reference to technical-discovery as pre-step |
