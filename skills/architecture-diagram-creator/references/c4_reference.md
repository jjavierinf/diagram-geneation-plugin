# C4 Model Reference

## C4 Levels

### Level 1 — System Context
- **Scope:** A single software system.
- **Shows:** The system in scope, the people who use it, and the other systems it interacts with.
- **Elements:** Person, Software System (internal), Software System (external).
- **Audience:** Everyone — technical and non-technical.

### Level 2 — Container
- **Scope:** A single software system.
- **Shows:** The high-level technical building blocks (containers) inside the system and how they communicate.
- **Elements:** Person, Container (web app, API, database, message bus, file system, etc.), Software System (external).
- **Audience:** Technical people inside and outside the development team.

### Level 3 — Component
- **Scope:** A single container.
- **Shows:** The components inside a container and their relationships.
- **Elements:** Person, Component (service, module, controller, repository, etc.), Container, Software System (external).
- **Audience:** Developers working on or with that container.

## Required Metadata per Element

Every element must include:

| Field         | Required | Example                          |
|---------------|----------|----------------------------------|
| `name`        | Yes      | "API Gateway"                    |
| `type`        | Yes      | "Container", "Component", etc.   |
| `technology`  | When applicable | "Python / FastAPI", "PostgreSQL" |
| `description` | Yes      | "Routes requests to microservices" |

## Color Scheme

Standard C4-PlantUML colors:

| Element              | Fill Color | Text   |
|----------------------|-----------|--------|
| Person               | `#08427B` | White  |
| Software System      | `#1168BD` | White  |
| Container            | `#438DD5` | White  |
| Component            | `#85BBF0` | Black  |
| External System      | `#999999` | White  |
| External Person      | `#999999` | White  |

All external elements use gray (`#999999`) to visually distinguish them from in-scope elements.

## SVG Data Attribute Conventions

### On the SVG root element

```html
<svg data-c4-level="context|container|component" ...>
```

### On shape elements (rect, circle, etc.)

```html
<rect data-c4-type="person|system|container|component|external-system"
      data-c4-name="API Gateway"
      data-c4-description="Routes requests to microservices"
      data-c4-technology="Kong" />
```

### On relationship paths

```html
<path data-c4-label="Makes API calls using"
      data-c4-technology="JSON/HTTPS" />
```

## Diagram Title Format

Every diagram must include a title in this format:

```
[Type] diagram for [Scope]
```

Examples:
- `[System Context] diagram for Saga ELT Platform`
- `[Container] diagram for Saga ELT Platform`
- `[Component] diagram for Ingestion Service`

## Common Mistakes to Avoid

1. **Don't mix levels.** A Context diagram must not contain containers or components. A Container diagram must not contain components. Each level has its own set of allowed element types.

2. **Don't use vague labels.** Every element and relationship needs a concrete name and description. Avoid "Service A", "sends data", or "processes things" — be specific about what and how.

3. **Don't show the internals of external systems.** External systems are opaque boxes. If you need to show their internals, create a separate diagram for that system.

4. **Containers are runtime things, not code modules.** A container is a separately deployable/runnable unit (API, database, SPA, queue). A Python package or class is not a container — it is a component.

5. **Always include a legend.** The diagram must have a legend box that maps colors and shapes to element types so any reader can understand it without prior C4 knowledge.

6. **External elements must be gray.** Never use the blue palette for systems, people, or containers that are outside the scope boundary. Gray signals "we don't own/control this."
