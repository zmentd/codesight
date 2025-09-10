# Next Steps (Backlog with Impact Rationale)

Proposed per-project config attributes to add in `config/config-<project>.yaml`. Each item states how it helps achieve step goals and/or the end goal.

Core
- Flow/progress
  * step01_processing_time_ms_measured — Wire step_metadata.processing_time_ms to measured BaseNode execution_time (Step01 goal) → accurate runtime metrics (End goal)
  * keep Step01 statistics informational; do not use for gating downstream (see Step01 stats item)
  * use config.quality_gates.step01.unix_relative_required to validate output paths are unix-style, project‑relative (fail early)

Step01 — File System Analysis - Complete

Step02 — AST Structural Extraction  - Complete

Step03 — Embeddings & Semantic Vector Analysis - Complete

Step04 — Pattern & Configuration Analysis
- implementation
  * jsp_security_detection — use config.steps.step04.enable_jsp_security_detection and config.steps.step04.security.patterns; emit guards/securedBy with file:line evidence; map to routes/screens; count in stats
  * business_rules_extraction — guard by config.steps.step04.enable_business_rules_extraction; read rules files from config.steps.step04.rules.files; output rule {id,text,type,sources:file:line,examples,confidence} and link to routes/screens
- tech-debt/refactor (move to Step02 where appropriate)
  * Move JSP inline SQL/procedure detection from Step04 regex (builders.build_jsp_table_edges) into Step02 JSP parser/reader as structured statements/operations
  * Ensure Step02 produces JAX-RS rest_endpoints and code_mappings so Step04 JAX-RS plugin only links (jaxrs.JaxRsLinkerPlugin currently composes routes from annotations)
  * Resolve servlet/action handler methods in Step02 where possible; reduce Step04 fallback heuristics (handlers._resolve_servlet_method/_select_fallback_method)
  * Normalize JSP include/redirect targets during Step02 parsing; Step04 linker should not need basename fallbacks (linker._find_jsp_by_path)
  * Emit line spans/provenance in Step02 details for use as evidence in Step04 relations/traces

Step05 — Semantic Enrichment & Capability/Domain Assembly
- quality gates
  * min_citations_per_capability, min_capability_coverage_pct — evidence-backed, broad coverage (Step05 goal) → defensible deliverables (End goal)
- implementation
  * enforce config.quality_gates.step05.min_citations_per_capability and .min_capability_coverage_pct when assembling capability records
  * enforce config.llm.json_mode and config.llm.citation_required; allow abstain using config.llm.abstain_min_confidence

Step06 — Graph Consolidation, Relationship Mapping, Posture & Exports
- quality gates
  * min_route_chain_coverage_pct, require_iam_for_guarded_routes — journey completeness and IAM mapping (Step06 goal) → posture deliverables met (End goal)
- implementation
  * enforce config.quality_gates.step06.min_route_chain_coverage_pct; fail if below
  * enforce config.quality_gates.step06.require_iam_for_guarded_routes when routes are guarded (from Step04 security) but lack IAM mapping
  * use config.output.formats and config.output.reports_dir for exporters; include evidence bundles when config.output.include_evidence_bundles is true