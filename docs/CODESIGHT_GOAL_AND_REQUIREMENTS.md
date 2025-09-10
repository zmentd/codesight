## **Mission Statement**
CodeSight is an AI-powered reverse engineering pipeline designed to automatically extract comprehensive business and technical requirements from legacy applications. The system transforms unstructured legacy codebases into structured, application specifications and tutorial documentation suitable for modernization efforts.

> Related: See `docs/REQUIREMENTS_DERIVATION_SPEC.md` for pipeline steps, high-level HOW, step→artifact map, and quality gates.

## Business Requirements Definition
- Capability catalogue: named features inferred from routes/actions/JSPs with purpose summaries.
- End-to-end user journeys: route → screen chains, redirects/includes, wizards; triggers and outcomes.
  - Includes CRUD: per-step tables and operations (reads/writes/deletes) and invoked procedures, plus a journey-level rollup.
- Business rules: validations, required fields, constraints from Java/JSP/SQL (WHERE/CASE, proc logic), with evidence and confidence.
- Reporting and batch: report/export screens, scheduled jobs (Quartz), outbound files/emails; inputs/outputs summarized.
- Security posture (business view): guarded screens/flows, role names, unauthorized paths, conditional UI behavior.
- Compliance signals: retention/table names, audit tables/fields, PII-like fields where detectable. Derived from code/config signals (audit/history tables; purge/archive jobs via Quartz/procedures/triggers; PII-like column names such as ssn/dob/email; encryption/hash/masking calls; user-action logging). Indicators, not authoritative—flag for SME confirmation.
- Assumptions/gaps: items needing SME confirmation clearly flagged with prompts.
- Entity glossary: core business entities from DB schemas/procs, key attributes, relationships, ownership signals. Consolidate to business entities (not one per table); expect roughly 30–80 prioritized by frequency and FK hubs; group synonyms/prefix families.

## Technical Requirements Definition
- Architecture map: frameworks, modules, layers, filters/interceptors, servlet mounts; dependency graph (directed graph of components/modules and external systems; edges are calls/data-access/config dependencies; weighted by usage counts; metrics such as fan-in/out and cycles expose coupling). Delivered as CSV/adjacency (no diagrams).
- API and route catalog: endpoint catalog grouped by component—path, verb, handler, key params, status codes where detectable; includes Struts actions and REST routes.
- Integrations inventory: DBs, queues, schedulers, external HTTP/SOAP, filesystems/emails; endpoints and configs.
- Data model and CRUD: schemas, keys (inferred from joins), CRUD matrices per route/method/JSP; lineage across flows. Complementary to ERD: ERD is the static schema; CRUD/lineage adds behavior (who reads/writes/deletes and how data moves).
- Security architecture: authn/authz mechanisms, roles, guards, crypto/secrets usage, network/security configs.
- Role→permission matrix and IAM mapping plan:
  - Role inventory from code/JSP security signals and annotations
  - Permission catalog: resource-level CRUD/actions (routes, tables, procedures)
  - Route/endpoint → role mappings with evidence and confidence
  - Least-privilege targets and documented exceptions
  - Draft IAM policy templates (principals, actions, resources, conditions)
  - Migration mapping from legacy roles to IAM roles/policies
- Componentization proposals: cohesion/coupling analysis, suggested service boundaries, dependency cut-lines.
- Risk/tech-debt: high-churn/hotspot areas, God classes, tight couplings, direct DB from UI, legacy APIs.
- Performance/scale signals: pagination, batch sizes, timeouts, caching, threadpools, heavy queries/procs.
- Operability: logging/audit patterns, error handling/retries, feature flags/config, scheduled tasks, health-like endpoints.
- Environments/deployment: web.xml/struts.xml topology, properties/env vars, drivers/versions, packaging.

## Domains vs Components
- Business Requirements: capture business domains and subdomains (capability-centric). Include domain purpose, key user journeys, core entities/terms, and outcomes.
- Technical Requirements: capture logical components (implementation-centric). Include responsibilities, boundaries/APIs, data touched, and dependencies.
- Domain↔Component crosswalk: which components primarily implement which domains, and shared utilities.

### Mid-level developer documentation (not file-level)
- Per domain (1 page each):
  - Purpose and scope
  - Top user journeys (routes→screens)
  - Core entities (business names, not every table)
  - Key screens/pages and notable rules
- Per component (1 page each):
  - Responsibilities and key capabilities
  - Public APIs/routes and inbound events
  - Data it owns/touches (tables/procs) and CRUD summary
  - Upstream/downstream dependencies (internal/external)
  - Security considerations and known risks/tech debt
- Cross-cutting summaries:
  - Route and service catalog (high level, grouped by component)
  - CRUD-by-component matrix (behavior tied to data)
  - Integrations inventory (systems, queues, files, schedules)
  - Security posture by component (roles/guards)
  - Trace samples for critical flows (evidence-backed)
- Notes:
  - We do not generate or ingest diagrams. Deliver tabular catalogs and textual summaries; existing diagrams may be referenced externally if needed.
  - Target scale: 5–15 domains, 10–30 components; keep each summary concise, link to evidence (graph queries/traces).

## Artifacts Delivered
- Business Requirements (this section)
- Technical Requirements (this section)
- Knowledge graph (entities, relations, traces) with provenance/confidence.
- Human-readable reports (CSV/HTML) for routes, CRUD, security, dependencies, traces, jobs.
- Tabular catalogs and textual summaries for flows, components, and integrations (no diagrams ingested or generated).
- Queryable outputs to support change impact, modernization planning, and audits.
- Evidence per claim (source refs/snippets) and confidence annotations for auditability.

