# QA Checklist and Runbook (1-page)

Purpose
- Provide a concise, repeatable QA checklist and minimal runbook to validate pipeline runs per project.

Cross-refs
- See `docs/REQUIREMENTS_DERIVATION_SPEC.md` for step contracts and quality gates.
- See `docs/CODESIGHT_GOAL_AND_REQUIREMENTS.md` for artifact expectations.

---

## QA Checklist (per project/run)

1) Configuration
- Config files present and loaded: `config/config.yaml`, `config/config-<project>.yaml`
- Paths normalized to Unix-style relative (spot-check in step01_output.json)

2) Step 01 — File System Analysis
- Output exists: `projects/<project>/output/step01_output.json`
- Gate: 100% Unix-relative; ≥95% config files readable

3) Step 02 — AST Structural Extraction
- Output exists: `projects/<project>/output/step02_output.json`
- Gate: ≥90% parse success; ≥95% route↔handler consistency; <5% unresolved refs

4) Step 03 — Embeddings & Semantic Vector Analysis
- Outputs exist: `projects/<project>/output/step03_output.json`, `projects/<project>/embeddings/*`
- Gate: ≥80% routable/JSP items embedded; cluster cohesion ≥ threshold

5) Step 04 — Pattern & Configuration Analysis
- Outputs exist: `projects/<project>/output/step04_output.json`, summary if applicable
- Gate: ≥90% config parse success; key patterns confidence ≥0.7

6) Step 05 — Semantic Enrichment
- Output exists: `projects/<project>/output/step05_output.json`
- Gate: capability items have ≥2 citations; ≥70% route/JSP coverage; LLM outputs include citations/abstain

7) Step 06 — Graph Consolidation and Exports
- Outputs exist: `final_output.json`, `validation_report.json`, `processing_log.json`, optional CSV/HTML under reports/
- Gate: route chains ≥70% coverage; CRUD matrices non-empty for majority; IAM matrix populated for guarded routes; schema validation passes

8) Evidence and Provenance
- Randomly sample items for file:line/source_refs integrity
- Confidence present for derived links and summaries

9) Exceptions and Abstentions
- Review abstain cases; ensure appropriate follow-ups are listed
- Confirm no silent failures in logs

---

## Runbook (minimal)

1) Initialize
- Ensure Python/venv is active; install dependencies as needed
- Initialize config in main entrypoint or test harness
  - In code: `config = config.get_instance()`
  - In tests: `Config.initialize(project_name="<project>"); config = config.get_instance()`

2) Execute Steps
- Run steps sequentially or via orchestrator (01→06)
- Prefer project-specific overrides where necessary

3) Validate
- Execute QA Checklist above
- Review `validation_report.json` and logs for issues

4) Review Artifacts
- Use catalogs/traces/CRUD matrices for stakeholder review
- Capture SME feedback for flagged items (compliance signals, ambiguous guards)

5) Remediation
- Tune `config-<project>.yaml` thresholds/patterns if needed
- Re-run affected steps; re-validate gates

6) Archive Outputs
- Commit or store outputs under `projects/<project>/output/` and `reports/` as required by the project

Notes
- This is an agile process; discuss proposed changes to gates/steps before adoption
- No diagrams are produced; use tabular/text artifacts with citations and confidence
