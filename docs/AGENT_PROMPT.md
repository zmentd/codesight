# CodeSight Agent Prompt (Concise)

**Version:** 1.0  •  **Updated:** Aug 15, 2025  
**Purpose:** Operating rules for AI agents and developers working on the 6‑step CodeSight pipeline.

---

## What this is
- A normative, short guide to keep work aligned with specs, quality gates, and existing code. Use this before writing code.

## Authority order (read first)
1) `docs/CODESIGHT_GOAL_AND_REQUIREMENTS.md`
2) `docs/REQUIREMENTS_DERIVATION_SPEC.md` (steps, data shapes, quality gates)
3) Runtime config: `config/config.yaml`, `config/config-<project>.yaml`
4) Existing behavior/tests for Steps 01–04
5) `docs/old - to be deleted/` (reference only)

## Canonical pipeline
- Step01 File System Analysis
- Step02 AST Structural Extraction
- Step03 Embeddings & Semantic Vector Analysis
- Step04 Pattern & Configuration Analysis
- Step05 Semantic Enrichment & Capability/Domain Assembly
- Step06 Graph Consolidation, Relationship Mapping, Posture & Exports

## Non‑negotiables
- **Paths:** Unix-style, project‑relative only; never absolute or backslashes
- **Config:** use Config singleton + dot‑notation (typed dataclasses), never raw dicts
- **Gates:** enforce defaults; project overrides allowed; do not lower without approval
- **Types:** use existing domain models; keep provenance and confidence on derived records. Use domain models not Dicts for typesafety
- **Simplicity:** add only what specs require; avoid flourishments Allow for future enhancements
- **Linting:** Ensure all linting issues are fixed as code changes are made

## Code reuse first
- Search `src/**` and reuse before creating new code
- Prefer existing patterns and error handling; keep changes minimal and justified
- Do not build optional helpers without a concrete consumer and spec link or discussion

## Configuration quick reference
- **Access pattern**
  - If not started by main: `Config.initialize(project_name="<name>")`
  - Everywhere else: `config = Config.get_instance()`
  - Dot‑notation only (examples):
    - `config.steps.step03.faiss.similarity_threshold`
    - `config.project.output_path`
    - `config.llm.provider`
- **Where sections live** (`src/config/sections.py`)
  - Top: `analysis`, `project`, `environment`, `threading`, `performance`, `validation`, `parsers`, `output`, `framework`, `pattern`, `debug`, `steps`, `classification`, `database`, `languages_patterns`, `frameworks`, `architectural_patterns`, `llm`, `jsp_analysis`
  - Steps: `config.steps.step01..step07` (dataclasses)
- **Project overrides**
  - File: `config/config-<project>.yaml` (same structure as dot paths)
  - Override only existing, type‑safe keys (e.g., `steps.step03.faiss.similarity_threshold`)
- **Adding new config**
  - Add field/dataclass in `sections.py` with defaults and types
  - Wire in `Config.__init__` (`self.<section>`)
  - If needed, extend loaders/validators; document briefly; then use via dot‑notation
- **Helpers**
  - Paths: `config.get_output_dir_for_step("step03")`, `config.get_output_path_for_step("step03")`, `config.get_project_embeddings_path()`
  - Placeholders: support `{project_name}` in paths (e.g., `steps.step03.storage.embeddings_directory`)
- **Testing**
  - ct-hr-storm-test is a project defined for concrete testing. Source code is stored under the test directory and copied from actual project ct-hr-storm. It can be referenced, without mocking, in test cases (Config.initialize(project_name="ct-hr-storm-test"))

## LLM/Embeddings (minimal)
- **LLM:** JSON‑only outputs with citations; allow abstain on low confidence
- **Embeddings:** cosine via L2‑normalized inner product; persist under `projects/<project>/embeddings`

## Escalate (stop and ask) when
- Spec gaps/conflicts; schema or contract/output changes; cross‑step impacts
- Need to hard‑code patterns or lower quality gates

## Testing
- Write real asserts on outputs; follow existing fixtures under `test/`
- In tests not launched via `main.py`: `Config.initialize(project_name="ct-hr-storm"); Config.get_instance()`
- test_utils provides directory paths to the test and src directory. It should be used on all tests.
- prefer test_jsp_reader.py or test_jsp_parser.py as template for test cases.
- Do NOT assert general cases as in asserting some list has a length greater than 2. Assert exactly what is expected, not just the list count but what exactly the list contains, all attributes and values

