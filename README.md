# CodeSight

CodeSight is a multi-step analysis pipeline for large enterprise codebases.

- Step01: File system analysis
- Step02: AST structural extraction
- Step03: Embeddings and semantic vector analysis
- Step04+: Higher-level semantic and relationship mapping


## Step03: Embeddings, Search, and REPL

Documentation: see docs/STEP03_OUTPUTS_AND_SEARCH_API.md

Highlights
- Persists FAISS index and JSON metadata under projects/{project_name}/embeddings
- Typed search API with filters (SearchFilters, SearchHit)
- Interactive REPL with free-text search, filters, stats, and cluster browsing

Quickstart (Windows cmd)
- Build/persist embeddings via Step03
- Launch REPL:
  - python scripts\embedding_repl.py --project ct-hr-storm-test
- In REPL:
  - :stats
  - :subdomains; :subdomain service; :type method
  - :where package_name=com.storm.user
  - approvals by manager
  - :clusters 12; :cluster cluster_003

Troubleshooting
- Ensure Config.initialize(project_name=...) is called by your entrypoints
- If IVF index is used on small data, the manager auto-adjusts nlist/nprobe
- Make sure model dimension matches steps.step03.faiss.dimension

---

## Key Documentation
- Goals and deliverables: `docs/CODESIGHT_GOAL_AND_REQUIREMENTS.md`
- Derivation spec (pipeline steps, step→artifact map, quality gates): `docs/REQUIREMENTS_DERIVATION_SPEC.md`
- QA checklist and runbook: `docs/QA_CHECKLIST_AND_RUNBOOK.md`

Canonical pipeline (authoritative)
- STEP 01 — File System Analysis
- STEP 02 — AST Structural Extraction
- STEP 03 — Embeddings & Semantic Vector Analysis
- STEP 04 — Pattern & Configuration Analysis
- STEP 05 — Semantic Enrichment and Capability/Domain Assembly
- STEP 06 — Graph Consolidation, Relationship Mapping, Posture, and Exports
