# Requirements Derivation Specification

Purpose
- Define how each Business and Technical requirement is produced from the codebase and inventories.
- Specify outputs, inputs, processing capabilities, assembly logic, and acceptance signals.
- No low-level implementation specs; only what each stage should provide.

Common inputs (from inventories/graph)
- Entities: Route, JSP, JavaMethod, Table, StoredProcedure, ConfigArtifact, Job/Schedule.
- Relations: renders, includesView, embedsView, redirectsTo, handlesRoute, readsFrom, writesTo, deletesFrom, invokesProcedure, mountedUnder.
- Signals: JSP titles/headings/labels, i18n strings, security pattern_hits, config keys, HTTP/SOAP/JMS/file endpoints.

Conventions
- Techniques: Parsing (deterministic), Embeddings (FAISS) for similarity/cluster, LLM (prompted summarization with citations).
- Outputs are JSON/CSV records with provenance and confidence.
- See also: `docs/CODESIGHT_GOAL_AND_REQUIREMENTS.md` for business/technical deliverables and terminology.

---

## Business requirements

### Capability catalogue
- Output: capability {id, name, purpose, members:{routes[], jsps[]}, synonyms[], evidence[], confidence}
- Inputs: route paths/names, action/method names, JSP titles/headings/labels, menu/i18n strings.
- Processing: parsing for candidates; embeddings+FAISS to group; graph-aware merge; LLM to name/purpose with citations.
- Assembly: attach member IDs, synonyms, and evidence snippets; compute confidence from cohesion and signal count.
- Acceptance: ≥ target coverage of routes/JSPs in some capability; each capability has ≥2 evidence items; low false-merge rate.

### End-to-end journeys with CRUD
- Output: trace {id, path:[route→(handler?)→jsp…], stepCRUD[], rollup:{tables, crud, procedures}, evidence[], confidence}
- Inputs: renders/includes/redirects, handlesRoute, reads/writes/deletes, invokesProcedure, proc→table map.
- Processing: compose route→screen chains; aggregate CRUD per step; expand procedures to underlying tables when known.
- Assembly: link evidence to relations; compute journey-level rollup; set confidence by linkage strength.
- Acceptance: traces exist for most routes; non-empty CRUD for majority; evidence attached per step.

### Business rules
- Output: rule {id, text, type:validation|constraint|policy, sources:[file#line], examples[], confidence}
- Inputs: JSP form constraints (required, regex), Java guards/branching, SQL WHERE/CASE, proc logic markers.
- Processing: parsing+regex mining; optional embeddings to group similar rules; LLM to paraphrase with caveats.
- Assembly: deduplicate, group by capability/journey; attach examples.
- Acceptance: rules cite files/lines; low false-positive rate on samples.

### Reporting and batch
- Output: job {id, purpose, trigger, inputs, outputs, impactedTables[], evidence[], confidence}
- Inputs: scheduler configs (Quartz), email/file sinks, proc invocations, report JSPs.
- Processing: parse configs/call sites; join to lineage to find impacted tables; heuristics for purpose (report/cleanup/sync).
- Assembly: normalize triggers (cron vs event), summarize inputs/outputs.
- Acceptance: each job has purpose and downstream data mapped.

### Security posture (business view)
- Output: guard {screen/flow, role/condition, outcome(allow/deny/hide), evidence[], confidence}
- Inputs: JSP security checks, Java annotations/guards, unauthorized redirects, menu conditionals.
- Processing: extract checks and map to routes/screens; group by role/condition.
- Assembly: consolidate per screen/flow; add evidence links.
- Acceptance: matrix of guarded screens vs roles populated with citations.

### Compliance signals
- Output: complianceSignal {entity/flow, type:audit|PII|retention, indicator, evidence[], confidence}
- Inputs: audit/history tables, purge/archive jobs, PII-like column names (ssn, dob, email, etc.), crypto/masking calls, audit logs.
- Processing: heuristics classifier; flag for SME confirmation.
- Assembly: bucket by type; track rationale and evidence.
- Acceptance: signals are present with confidence and SME-required flags.

### Entity glossary
- Output: businessEntity {id, name, keyAttributes[], relatedEntities[], memberTables[], evidence[], confidence}
- Inputs: table/proc clusters, FK hubs, naming families, usage frequency across flows.
- Processing: clustering+normalization; synonym folding; LLM to propose human-friendly names with citations.
- Assembly: map multiple tables to one business entity; record relations.
- Acceptance: 30–80 consolidated entities; members/evidence traceable.

---

## Technical requirements

### Architecture map
- Output: component {id, name, responsibilities, modules[], deps:{in,out}, metrics{fanin,fannot,cycles}, evidence[]}
- Inputs: package/module structure, imports, filters/interceptors, servlet mounts.
- Processing: build dependency graph; compute metrics; cluster modules to components.
- Assembly: CSV/adjacency for deps; component summaries.
- Acceptance: cycles detected; top couplings highlighted with evidence.

### API and route catalog
- Output: endpoint {id, component, path, verb, handler, keyParams[], statusCodes?, evidence[]}
- Inputs: routes/verbs/mounts, handler links, parameter mappings.
- Processing: parse configs/annotations; resolve handlers; infer params from form fields/query usage.
- Assembly: group by component; add evidence.
- Acceptance: endpoints round-trip to handlers; parameter coverage sufficient.

### Integrations inventory
- Output: integration {id, type:HTTP|SOAP|JMS|File|Email|DB, endpoint, auth?, retries?, components[], evidence[]}
- Inputs: HTTP/SOAP clients, JMS configs, SMTP usage, file I/O paths, DB connection strings.
- Processing: config/code scan; classify by type; infer auth/retry where visible.
- Assembly: link to using components; record endpoints.
- Acceptance: each integration has endpoint and usage evidence.

### Data model, CRUD, and lineage
- Output: crudMatrix {actor:route|method|jsp, tables:{read[], write[], delete[]}, procedures[], lineagePaths[], evidence[]}
- Inputs: table ops, proc map, traces.
- Processing: aggregate per actor; construct lineage across flows.
- Assembly: expose CSV/JSON; link to traces.
- Acceptance: top entities show consistent readers/writers; evidence present.

### Security architecture
- Output: securityFacet {mechanism(authn/authz), roles[], guards[], secrets/crypto usage, evidence[]}
- Inputs: annotations, filters/interceptors, JSP checks, crypto/secrets calls, network/security configs.
- Processing: extract and categorize; map to components/routes.
- Assembly: concise per-component security summary.
- Acceptance: role/guard coverage with citations.

### Role→permission matrix and IAM mapping plan
- Output: rolePermission {role, permissions:{routes,tables,procedures}, mappings, iamDraftPolicies[], evidence[], confidence}
- Inputs: role checks/signals, guarded routes/screens, resource lists.
- Processing: map roles to resources actions (CRUD); LLM may suggest least-privilege names; generate draft policy templates.
- Assembly: matrix (CSV) and JSON drafts.
- Acceptance: coverage of key routes/tables; gaps flagged for SMEs.

### Componentization proposals
- Output: proposal {componentsBoundary, rationale, affectedDeps, expectedBenefits, evidence[]}
- Inputs: dependency graph metrics, CRUD cohesion/coupling, shared DB access.
- Processing: clustering/scoring; cut-line analysis.
- Assembly: concise proposals with before/after metrics (text/CSV).
- Acceptance: reduces cycles and cross-component DB writes.

### Risk/tech-debt
- Output: riskItem {type:hotspot|godClass|tightCoupling|uiDbDirect|legacyApi, location, rationale, evidence[], confidence}
- Inputs: size/complexity proxies, centrality, direct SQL in views, deprecated APIs.
- Processing: heuristics + graph metrics.
- Assembly: prioritized list.
- Acceptance: concrete examples with citations.

### Performance/scale signals
- Output: perfSignal {area, indicator:pagination|timeout|cache|heavyProc, location, rationale, evidence[]}
- Inputs: timeouts, batch sizes, caches, heavy queries/procs, threadpools.
- Processing: scan configs/SQL; frequency weighting.
- Assembly: top-N signals per component.
- Acceptance: evidence-backed list with likely impact.

### Operability
- Output: operFacet {logging, auditing, errorHandling, retries, featureFlags, scheduledTasks, evidence[]}
- Inputs: logging patterns, audit tables/fields, retry loops, config flags, scheduler configs.
- Processing: extract and categorize per component.
- Assembly: checklists and summaries.
- Acceptance: coverage of core operability practices.

### Environments/deployment
- Output: envInventory {web.xml mounts, properties/env vars, drivers/versions, packaging, evidence[]}
- Inputs: web.xml/struts.xml, properties, classpath/manifest hints.
- Processing: config harvesting; normalization.
- Assembly: per-environment facet inventory.
- Acceptance: clear, queryable inventory with citations.

### Domains ↔ Components crosswalk
- Output: crosswalk {domain, primaryComponents[], sharedUtilities[], evidence[]}
- Inputs: capability→routes/screens, component responsibilities, CRUD ownership.
- Processing: map capabilities to components via member overlaps and data ownership.
- Assembly: concise table per domain.
- Acceptance: domains cover major capabilities; minimal ambiguous ownership.

---

## Data elements (I/O shapes)
- Embedding item: {id, text, type:route|jsp|menu|i18n, weight, sourceIds[]}
- FAISS index: built over embeddings; supports nearest-neighbor queries for clustering.
- LLM input (per cluster): {memberSummaries[], representativeSnippets[], ask:{name,purpose,synonyms,citations}}
- LLM output (per cluster): {name, purpose, synonyms[], citations:[memberIds], abstain?:bool}
- Provenance: every record carries {sourceId, file, line?, relationId?} and confidence.

---

## Pipeline steps (goals, inputs, outputs)

### STEP 01 — File System Analysis
- Goal: discover source/config/build assets, collect project metadata, and framework hints.
- Inputs: repository root(s).
- Outputs (step01_output.json): file inventory with Unix-relative paths, config files (web.xml, struts.xml, *.properties, *.yml), build files and dependency hints, directory/package structure, framework hints, provenance.
- How (high-level):
  - Crawl the repo(s) recursively; ignore binaries/VCS; capture basic metadata (size, ext, checksum, path).
  - Parse build files (Maven/Gradle/Ant) to infer modules, targets, and dependency coordinates.
  - Detect frameworks/config types via lightweight content scans (e.g., spring/struts/hibernate signatures).
  - Normalize all paths to Unix-style relative; attach provenance to each record.

### STEP 02 — AST Structural Extraction
- Goal: parse source into structural facts and relationships.
- Inputs: step01_output.json + source files.
- Outputs (step02_output.json): classes/methods/annotations; routes/handlers and servlet mounts; JSP includes/renders/redirects; SQL/proc references; relations (handlesRoute, renders, includesView, embedsView, redirectsTo, invokesProcedure, readsFrom/writesTo/deletesFrom); signals (titles, labels, security annotations); provenance.
- How (high-level):
  - Use language parsers to build ASTs for Java and parse JSP/taglibs; extract classes, methods, annotations, imports.
  - Resolve routes/handlers from annotations and config (web.xml/struts.xml) plus servlet/filter mappings.
  - Mine SQL/JDBC usage and stored procedure calls with pattern-based extraction; map to table/proc references.
  - From JSP, collect view links (includes/renders/redirects) and UI signals (title, H1/H2, i18n keys).

### STEP 03 — Embeddings & Semantic Vector Analysis
- Goal: build embeddings and semantic similarity to enrich step02 data.
- Inputs: step02_output.json + selected code/config snippets.
- Outputs (step03_output.json): same schema as step02 plus embedding vectors/IDs (out-of-band), similarity scores, clusters/labels, representative snippets per entity, index metadata.
- How (high-level):
  - Compose normalized text per item (route | handler | JSP title | labels) and generate sentence embeddings.
  - Build a FAISS index; run KNN queries and thresholded clustering to group semantically similar items.
  - Score cluster cohesion; select representative snippets; attach lightweight labels; carry confidence.

### STEP 04 — Pattern & Configuration Analysis
- Goal: parse configuration files and detect framework/architectural patterns; extract business/security/transaction rules.
- Inputs: step01_output.json + step02_output.json + configuration files discovered in step01.
- Outputs (step04_output.json): framework_analysis (Spring, persistence, web, validation) with config paths; architectural_patterns (MVC/layering/DI/overrides); business_rules_extracted (validation, security, transaction) with file:line; environment_configurations; configuration_quality and validation_results; provenance. All paths Unix-relative.
- How (high-level):
  - Parse XML/properties/YAML with tolerant readers; extract Spring beans, MVC/view resolvers, DI, TX, security, persistence, and web.xml mappings.
  - Detect architecture patterns (MVC, layered, DI strategy) via rule-based matchers and package/directory hints.
  - Extract validation/security/transaction rules with file:line evidence; normalize environment/profile settings.
  - Cross-validate with Step 02 AST/annotations to adjust confidences and resolve ambiguities.

### STEP 05 — Semantic Enrichment and Capability/Domain Assembly
- Goal: synthesize capability catalogue, component/domain summaries, and paraphrased rules using LLM + FAISS with citations.
- Inputs: step01–step04 outputs.
- Outputs (step05_output.json): capability catalogue (id, name, purpose, synonyms, members, citations); component and capability summaries; domain tags per component/route; paraphrased business rules with evidence and confidence.
- How (high-level):
  - Use embedding clusters and graph adjacency (route⇄view/menu) to propose capability groupings.
  - Prompt an LLM with member summaries and representative snippets to name and describe capabilities; require JSON and citations; allow abstain.
  - Tag components/routes with domains via heuristic mapping (CRUD ownership, package names) refined by LLM suggestions.
  - Paraphrase business rules succinctly while preserving references and caveats.

### STEP 06 — Graph Consolidation, Relationship Mapping, Posture, and Exports
- Goal: consolidate the knowledge graph; build route chains and CRUD rollups; enumerate integrations; derive security/compliance/risk/performance/operability facets; generate exports with validation.
- Inputs: step02–step05 outputs.
- Outputs: knowledge graph with traces; CRUD matrices and lineage (including proc→table expansion); integrations inventory (HTTP/SOAP/JMS/File/Email/DB); security facets and role→permission matrix with IAM draft policies; compliance signals; risk/tech-debt and performance signals; operability checklists; final JSON/CSV/HTML exports; validation and processing logs; evidence bundles.
- How (high-level):
  - Assemble entities/relations into a unified graph; dedupe/normalize IDs; compute metrics.
  - Compose route→screen chains from renders/includes/redirects; aggregate per-step and journey CRUD from reads/writes/deletes and proc→table maps.
  - Scan code/config for external calls (HTTP/SOAP/JMS/Email/File/DB) to build an integrations inventory.
  - Derive security facets and role→permission mappings from guards/annotations/config; draft least-privilege IAM policies.
  - Surface compliance, risk, performance, and operability signals via rules and heuristics; validate schema; generate exports and reports with provenance.

---

## Step→Artifact map
- STEP 01 — File System Analysis
  - Artifacts: `projects/<project>/output/step01_output.json`, processing logs
- STEP 02 — AST Structural Extraction
  - Artifacts: `projects/<project>/output/step02_output.json`, processing logs
- STEP 03 — Embeddings & Semantic Vector Analysis
  - Artifacts: `projects/<project>/output/step03_output.json`, `projects/<project>/embeddings/*` (FAISS index + metadata)
- STEP 04 — Pattern & Configuration Analysis
  - Artifacts: `projects/<project>/output/step04_output.json`, `projects/<project>/output/step04_summary.txt`
- STEP 05 — Semantic Enrichment and Capability/Domain Assembly
  - Artifacts: `projects/<project>/output/step05_output.json`
- STEP 06 — Graph Consolidation, Relationship Mapping, Posture, and Exports
  - Artifacts: `projects/<project>/output/final_output.json`, `projects/<project>/output/validation_report.json`, `projects/<project>/output/processing_log.json`, `projects/<project>/output/error_report.json`, CSV/HTML reports under `projects/<project>/reports/`, evidence bundles

> Cross-reference: for the business/technical artifact descriptions, see `docs/CODESIGHT_GOAL_AND_REQUIREMENTS.md` → “Artifacts Delivered”.

---

## Minimal operational guidance

### LLM prompts (general)
- Purpose: convert clustered evidence into human-friendly names/purposes with citations; paraphrase rules succinctly.
- Input content: for each cluster, provide 5–10 short member summaries (route path, JSP title, 2–3 labels) and 1–2 representative snippets with file:line.
- Instruction constraints:
  - Return: {name, purpose(1–2 sentences), synonyms[], citations:[memberIds]}.
  - Must cite memberIds used; abstain if uncertain or conflicting.
  - Do not invent APIs or behaviors beyond provided evidence.
- Parameters (guidance): low temperature, deterministic settings; bounded output tokens; JSON-only responses.

### Embeddings/FAISS queries (general)
- Embedding text per item: "routePath | action/method | JSP title | top labels" (normalized, de-suffixed).
- Index: sentence-level embeddings; build FAISS index over all candidate items.
- Query patterns:
  - KNN (k≈20) with similarity threshold (≈0.7) to assemble candidate clusters.
  - Prefer merges that also co-occur in graph links (route→render/menu); penalize cross-module merges.
  - Use anchors (menu/i18n labels) to seed cluster names; fold plural/synonym variants.

### Step dependencies and contracts (succinct)
- 01 → 02; 02 → 03; 01+02 → 04; 02–04 → 05; 02–05 → 06.
- Contract note: all records carry provenance and confidence; paths are Unix-relative; abstain on low-confidence links; missing dependencies should fail fast with clear messages.

---

## Quality gates and acceptance thresholds (concise)

- STEP 01
  - 100% Unix-relative paths; 0 absolute paths (fail fast if present).
  - ≥95% discovered configuration files accessible/readable.

- STEP 02
  - ≥90% parse success on analyzed files.
  - ≥95% route↔handler resolution consistency.
  - Unresolved/unknown references <5%.

- STEP 03
  - ≥80% of routable/JSP items embedded.
  - Cluster cohesion above project threshold; abstain on low-confidence labels.

- STEP 04
  - ≥90% configuration parsing success.
  - Security/transaction rules extracted when configurations exist.
  - Key pattern detection confidence ≥0.7.

- STEP 05
  - Capability entries each have ≥2 independent evidence citations.
  - Coverage: ≥70% of routes/JSPs assigned to some capability.
  - LLM outputs conform to schema and include citations; abstain allowed on low confidence.

- STEP 06
  - Route chains present for ≥70% of routable paths.
  - CRUD matrices non-empty for majority of actors; lineage resolves known procedures to tables when mappings exist.
  - Role→permission matrix covers all guarded routes/screens detected.
  - Exports generated without schema/format errors; validation report passes configured checks.

- Note: Thresholds are defaults; tune per project in configuration while preserving provenance and confidence in all artifacts.
