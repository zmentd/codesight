# Step04 Walkthrough (ct-hr-storm) and Draft Schema

Purpose
- Provide a simple, concrete plan tailored to ct-hr-storm without re-implementing what Step02/Step03 already deliver.
- Serve as a walkthrough checklist for implementing Step04.

Scope (project-specific)
- Frameworks/features in use (from Step01/Step02 artifacts and project config):
  - Struts 2 (struts.xml, StrutsPrepareAndExecuteFilter)
  - JSP views with Struts tags; DisplayTag TableDecorator (StormDecorator)
  - Custom JDBC layer (StormPS, PreparedStatement patterns) – not JPA/Hibernate
  - web.xml present; security may exist via constraints/filters
- Not in scope for this project: Spring MVC controllers, JPA/Hibernate entities (disabled), MyBatis

What we already have (reuse, no duplication)
- Step02 output (typed models):
  - struts.xml parsed into a structured representation (framework=struts_2x)
  - web.xml indexed and chunked (available via Step03 metadata, file_path WEB-INF/web.xml)
  - Java class/method inventory with package/class/method names; references to StormPS/PreparedStatement appear in content
  - JSP inventory; known Menu names discovered in pages (e.g., ScheduleMenu, GeneralMenu, ReportsMenu, SetupMenu, CompanyMenu, ExtrasMenu, ExtraProjectsMenu, ExtraTasksMenu)
  - Subdomains (directory-based) for grouping
- Step03 artifacts:
  - Persisted FAISS index and JSON metadata for chunks
  - Typed search API (SearchFilters/SearchHit) with filters on package/class/method, file_path, subdomain, has_sql, stored_procedure_names, entity_mapping_table
  - REPL for ad-hoc validation (now with clustering browse)

Step04 objective (ct-hr-storm)
- Build an evidence graph and traces linking: Menu → JSP → Struts Action → Java methods → SQL/Table operations, with optional security constraints
- Produce CRUD classification and table impact per screen/flow, with confidence and evidence

Deliverables
- projects/{project}/output/step04_output.json (entities, relations, traces, stats)
- Optional graph export (GraphJSON) under projects/{project}/graphs
- Documentation updates (this file + API doc)

Implementation plan (straightforward)
1) Routes and screens (reusing Step02 models)
   - Read Step02 struts model to create Routes {url/namespace, action class#method, result JSP}
   - Link JSPs via result locations; if missing, use Step03 search with filters chunk_type=jsp + file_path/source_relative_path
   - Build Menu → JSP mapping from Step02 (menu names already present) and JSP includes; record edges
   - JSP coverage note: rely on Step02 `JspDetails`, and capture needed form/tag/include attributes for traces. XHTML embedded in Java string literals can be handled in Phase B (optional) by harvesting large HTML/XHTML strings as view fragments.

2) Action methods and calls
   - Identify Action classes/methods from Step02 (Struts 2); map execute/submit handlers
   - For each Action method, collect called methods if available; otherwise, use Step03 search with package/class/method filters to infer calls (attach SearchHit evidence and confidence)

3) Data access (no JDBC connection handling)
   - Consume existing parsed SQL from Step02: use JavaMethod.sql_statements, JavaMethod.sql_stored_procedures, and SQLDetails.table_operations as primary evidence for CRUD and tables.
   - Dynamic SQL in Java: when SQL is built via StringBuilder/concatenation, reconstruct inline SQL by collecting appended string literals within the same method; tokenize to classify CRUD and extract table names. If reconstruction fails, emit executesSQL with unknown text and use execute*/set* calls only as low-confidence evidence.
   - Treat StormPS as a PreparedStatement-style helper; no Storm-specific code or identifiers are required.
   - Emit relations in Step04 JSON: Method → executesSQL; Method → readsFrom/writesTo → Table; Method → invokesProcedure when applicable.

4) Security (as available)
   - Parse web.xml security-constraint/auth-constraint/role-name; map URL patterns to roles → Routes (securedBy)
   - Also consume @RolesAllowed annotations captured in Step02 JavaDetails to emit securedBy relations for annotated classes/methods.
   - Note Struts interceptors/filters with auth semantics if present; attach low-confidence securedBy when heuristic only

5) End-to-end traces
   - For each Menu/JSP: JSP → Route → ActionMethod → Service/DAO → SQL/Procedure → Table(s)
   - Summarize CRUD/table impacts, attach evidence (chunk_ids + file/line refs), and compute confidence from rules + similarity scores

6) Domains and grouping
   - Seed domains from Menu groups and subdomains (directory-based)
   - Use Step03 clusters to group functionally similar methods; attach cluster IDs as supplemental evidence only

Reuse and non-duplication rules
- Do not re-parse files from disk in Step04; always consume Step02 typed output and Step03 search
- Use SearchFilters to narrow candidates (chunk_type, package_name, class_name, method_name, file_path, subdomain_name)
- Keep SQL parsing minimal and focused on CRUD/table names; prefer Step02 outputs, and only reconstruct dynamic SQL when necessary

Phased delivery
- Phase A (MVP): Routes↔JSP linking, CRUD/table extraction from Step02 outputs, dynamic SQL reconstruction heuristic, basic traces, JSON output
- Phase B: Security mapping from web.xml and @RolesAllowed, XHTML-in-Java view fragments, graph export
- Phase C: Confidence tuning, menu grouping, optional clustering insights

---

## Appendix A: Step04 JSON Schema (draft)

Top-level
```json
{
  "version": "1.0",
  "project_name": "ct-hr-storm",
  "generated_at": "2025-08-13T00:00:00Z",
  "config": { "evidence_top_k": 10, "min_confidence": 0.5 },
  "entities": [],
  "relations": [],
  "traces": [],
  "stats": {}
}
```

Entity (examples)
```json
{
  "id": "route_Storm_ApproveTime",
  "type": "Route",                     
  "name": "/storm/approveTime",
  "attributes": {
    "framework": "struts_2x",
    "namespace": "/storm",
    "action": "ApproveTimeAction",
    "method": "execute",
    "result_jsp": "/WEB-INF/jsp/approveTime.jsp"
  },
  "source_refs": [ {"file": "Deployment/Storm2/src/struts.xml", "line": 1234} ]
}
```

Relation
```json
{
  "id": "r1",
  "from": "route_Storm_ApproveTime",
  "to": "jsp_approveTime",
  "type": "renders",
  "confidence": 0.9,
  "evidence": [
    { "chunk_id": "config_struts_123", "score": 0.98 },
    { "file": "WEB-INF/jsp/approveTime.jsp", "line": 1 }
  ],
  "rationale": "struts result mapping to JSP"
}
```

Trace
```json
{
  "id": "t_approveTime_flow",
  "screen": "jsp_approveTime",
  "route": "route_Storm_ApproveTime",
  "path": ["route_Storm_ApproveTime", "action_ApproveTimeAction_execute", "method_Service_process", "sql_update_TimeTable"],
  "crud_summary": { "reads": ["TimeTable"], "writes": ["TimeTable"] },
  "tables": ["TimeTable"],
  "evidence": [ {"chunk_id": "method_ApproveTime_execute_123", "score": 0.87} ],
  "confidence": 0.76
}
```

Evidence type
```json
{ "chunk_id": "...", "score": 0.0 }
{ "file": "path", "line": 10, "end_line": 20 }
```

Allowed entity types
- Menu, JSP, Route, ActionMethod, JavaMethod, SQLStatement, StoredProcedure, Table, Role

Allowed relation types
- renders, linksTo, submitsTo, handlesRoute, calls, delegatesTo, usesDAO, executesSQL, invokesProcedure, readsFrom, writesTo, securedBy

---

## Appendix B: Detailed Plan Notes (source)

Context validated for ct-hr-storm
- Struts 2 present (struts.xml, StrutsPrepareAndExecuteFilter)
- JSP views; DisplayTag with StormDecorator
- Custom JDBC via StormPS / PreparedStatement patterns; many methods named createPreparedStatement/execute*
- web.xml present; Hibernate/JPA disabled; no Spring MVC

Step04 goal and approach
- Build an evidence graph and traces from Menu/JSP through Struts to Java and DB
- Reuse Step02 parsed models and Step03 typed search; avoid duplicating parsing
- Focus on CRUD classification and table impact; map security if present

Work items
- Route builder from Step02 struts
- JSP linker and Menu mapping from Step02 artifacts
- CRUD/table extraction from Step02 SQL models + dynamic SQL reconstruction (no Storm-specific code)
- Security mapping from web.xml and @RolesAllowed
- Tracer to assemble end-to-end flows with evidence and confidence
- Outputs: step04_output.json (+ optional GraphJSON)
