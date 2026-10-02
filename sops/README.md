# Standard Operating Procedures (SOPs)

> **Form Rationale**: SOPs are authored as standalone YAML documents with machine-verifiable numeric thresholds because safety verdicts must be evaluated deterministically in code—never left to LLM probability or hallucination.

Each SOP defines:
- `id`: Unique identifier (e.g. `SOP-001`)
- `title` & `intent`: Human-readable summary and intent for semantic catalog routing
- `category` & `severity`: Classification (`critical`, `high`, `moderate`, `low`)
- `override`: Boolean flag indicating universal weather overrides
- `applies_to`: Target activities or demographic groups
- `conditions`: Machine-evaluated compound/threshold rules against Open-Meteo telemetry
- `advice`: Verbatim authoritative guidance rendered to the user
