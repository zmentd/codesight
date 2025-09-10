from __future__ import annotations

from typing import Dict, List, Optional, Set

from config.sections import Step04Config
from domain.java_details import JavaDetails
from domain.jsp_details import JspDetails
from domain.sql_details import SQLDetails
from domain.step02_output import Step02AstExtractorOutput
from steps.step02.source_inventory_query import SourceInventoryQuery
from steps.step04.builders import DataAccessBuilder, RouteBuilder
from steps.step04.evidence import EvidenceUtils
from steps.step04.handlers import ActionLinker
from steps.step04.jaxrs import JaxRsLinkerPlugin
from steps.step04.linker import Linker
from steps.step04.models import Entity, Evidence, Relation, Step04Output
from steps.step04.plugins import LinkerPlugin
from steps.step04.security import SecurityBuilder
from steps.step04.tracer import TraceBuilder


class Step04Assembler:
    """Assemble Step04 entities and relations from Step02 models. No file re-parsing."""

    def __init__(self, cfg: Step04Config | None = None) -> None:
        self.route_builder = RouteBuilder()
        self.linker = Linker()
        self.data_builder = DataAccessBuilder()
        self.security_builder = SecurityBuilder()
        self.tracer = TraceBuilder()
        self.action_linker = ActionLinker()
        self.evidence = EvidenceUtils()
        self.cfg: Step04Config | None = cfg
        # Extensible plugin list for framework/linker extensions (guarded by toggles)
        self.plugins: List[LinkerPlugin] = []
        if not self.cfg or getattr(self.cfg, 'enable_jaxrs', True):
            self.plugins.append(JaxRsLinkerPlugin())

    def _is_servlet_route(self, e: Entity) -> bool:
        fw = (e.attributes or {}).get("framework") if e and e.attributes is not None else None
        if not isinstance(fw, str):
            return False
        fw_l = fw.lower()
        return fw_l in ("web_xml", "servlet", "servlet_container")

    def assemble(self, step02: Step02AstExtractorOutput, project_name: str) -> Step04Output:
        output = Step04Output.create(project_name=project_name)

        # Routes and views
        routes: Dict[str, Entity] = self.route_builder.build_routes(step02)
        # Respect enable_servlet toggle by filtering out servlet-only routes
        if self.cfg and self.cfg.enable_servlet is False:
            routes = {k: v for k, v in routes.items() if not self._is_servlet_route(v)}

        jsp_entities, render_rels = self.linker.link_routes_to_jsps(routes, step02)
        # Add evidence to renders from config file if available
        for rr in render_rels:
            frm = routes.get(rr.from_id)
            if frm and frm.source_refs:
                src_ref = frm.source_refs[0]
                ev = self.evidence.build_evidence_from_source_ref(src_ref)
                rr.evidence.append(ev)
        # New: JSP -> JSP links via code_mappings (includes, iframes, redirects) — guarded by enable_jsp_links
        jsp2_entities: Dict[str, Entity] = {}
        jsp2_rels: List[Relation] = []
        if not self.cfg or getattr(self.cfg, 'enable_jsp_links', True):
            jsp2_entities, jsp2_rels = self.linker.link_jsps_to_jsps(step02)

        # New: attempt to resolve JSP action_call mappings to routes
        jsp_action_entities: Dict[str, Entity] = {}
        jsp_action_rels: List[Relation] = []
        try:
            jsp_action_entities, jsp_action_rels = self.linker.link_jsps_to_routes(step02, routes)
        except Exception:
            jsp_action_entities, jsp_action_rels = {}, []

        entity_index: Dict[str, Entity] = {}
        for e in routes.values():
            entity_index[e.id] = e
        for e in jsp_entities.values():
            entity_index[e.id] = e
        for e in jsp2_entities.values():
            entity_index[e.id] = e
        for e in jsp_action_entities.values():
            entity_index[e.id] = e
        relations: List[Relation] = []
        relations.extend(render_rels)
        relations.extend(jsp2_rels)
        relations.extend(jsp_action_rels)

        # Link routes to handler methods (Struts/servlet)
        method_entities, handle_rels = self.action_linker.link_routes_to_methods(routes, step02)
        # Add evidence to handlesRoute from method entity source when present, else route source
        for hr in handle_rels:
            m_ent = method_entities.get(hr.to_id)
            added = False
            if m_ent and m_ent.source_refs:
                ev = self.evidence.build_evidence_from_source_ref(m_ent.source_refs[0])
                hr.evidence.append(ev)
                added = True
            if not added:
                r_ent = routes.get(hr.from_id)
                if r_ent and r_ent.source_refs:
                    ev = self.evidence.build_evidence_from_source_ref(r_ent.source_refs[0])
                    hr.evidence.append(ev)
        for e in method_entities.values():
            entity_index[e.id] = e
        relations.extend(handle_rels)

        # Apply extensible linker plugins (e.g., JAX-RS) — already guarded in constructor
        for plugin in self.plugins:
            new_routes, new_rels, new_methods = plugin.apply(routes, step02)
            # Merge new routes
            for e in new_routes.values():
                routes[e.id] = e
                entity_index[e.id] = e
            # Merge new methods
            for e in new_methods.values():
                entity_index[e.id] = e
            # Merge relations
            # Add evidence to new handlesRoute and mountedUnder from route/method source
            for r in new_rels:
                if r.type in ("handlesRoute", "mountedUnder"):
                    frm = routes.get(r.from_id) or new_routes.get(r.from_id)
                    if frm and frm.source_refs:
                        ev = self.evidence.build_evidence_from_source_ref(frm.source_refs[0])
                        r.evidence.append(ev)
            relations.extend(new_rels)

        # Build SP -> table operation map once from Step02 output
        self.data_builder.build_procedure_map(step02)

        # Data access: Java files (guarded by enable_sql_edges_java)
        if not self.cfg or getattr(self.cfg, 'enable_sql_edges_java', True):
            java_files = SourceInventoryQuery(step02.source_inventory).files().detail_type("java").execute().items
            for f in java_files:
                if isinstance(f.details, JavaDetails):
                    rels = self.data_builder.build_method_table_edges(f.details, getattr(f, 'path', None))
                    relations.extend(rels)
                    # Security edges (@RolesAllowed) — optional
                    if not self.cfg or getattr(self.cfg, 'enable_security_roles', True):
                        relations.extend(self.security_builder.build_roles_allowed(f.details))
                    # Ensure method entities exist for from_id
                    for r in rels:
                        if r.from_id not in entity_index and r.from_id.startswith("method_"):
                            entity_index[r.from_id] = Entity(id=r.from_id, type="JavaMethod")

        # Data access: SQL files (optional, guarded by enable_sql_edges_sqlfiles)
        if not self.cfg or getattr(self.cfg, 'enable_sql_edges_sqlfiles', True):
            sql_files = SourceInventoryQuery(step02.source_inventory).files().detail_type("sql").execute().items
            for f in sql_files:
                if isinstance(f.details, SQLDetails):
                    rels = self.data_builder.build_sql_file_table_edges(f.details)
                    relations.extend(rels)

        # Data access: JSP files (inline SQL and stored procedures) — guarded by enable_sql_edges_jsp
        if not self.cfg or getattr(self.cfg, 'enable_sql_edges_jsp', True):
            jsp_files = SourceInventoryQuery(step02.source_inventory).files().detail_type("jsp").execute().items
            for f in jsp_files:
                if isinstance(f.details, JspDetails):
                    rels = self.data_builder.build_jsp_table_edges(f.details, f.path)
                    relations.extend(rels)
                    # Ensure JSP entities exist for from_id
                    for r in rels:
                        if r.from_id not in entity_index and r.from_id.startswith("jsp_"):
                            # Build minimal JSP entity if linker didn't already
                            stem = r.from_id[len("jsp_"):]
                            entity_index[r.from_id] = Entity(id=r.from_id, type="JSP", name=stem, attributes={"file_path": self.evidence.normalize_path(f.path)})

        # New: JSP security detection (Step02 signals) — guarded by enable_jsp_security_detection
        if self.cfg and getattr(self.cfg, 'enable_jsp_security_detection', False):
            jsp_sec_entities, jsp_sec_rels = self.security_builder.build_jsp_security(step02)
            # Merge JSP entities discovered via security scan
            for e in jsp_sec_entities.values():
                if e.id not in entity_index:
                    entity_index[e.id] = e
            relations.extend(jsp_sec_rels)

            # Build adjacency for JSP->JSP links (includes/redirects/etc.)
            jsp_adj: Dict[str, Set[str]] = {}
            # Build direct route->jsp renders map
            route_renders: Dict[str, Set[str]] = {}
            for r in relations:
                # collect renders for route->jsp
                if r.type == "renders":
                    route_renders.setdefault(r.from_id, set()).add(r.to_id)
                # collect jsp->jsp adjacency for any cross-jsp relations
                if isinstance(r.from_id, str) and isinstance(r.to_id, str) and r.from_id.startswith("jsp_") and r.to_id.startswith("jsp_"):
                    jsp_adj.setdefault(r.from_id, set()).add(r.to_id)

            # Helper: compute reachable JSPs via adjacency (depth-first)
            def reachable_jsps(start_jsps: Set[str]) -> Set[str]:
                seen: Set[str] = set()
                stack = list(start_jsps)
                while stack:
                    cur = stack.pop()
                    if cur in seen:
                        continue
                    seen.add(cur)
                    for nb in jsp_adj.get(cur, set()):
                        if nb not in seen:
                            stack.append(nb)
                return seen

            # Map JSP securedBy relations for quick lookup: jsp_id -> set(role_id) and evidence
            jsp_roles: Dict[str, List[Relation]] = {}
            for r in jsp_sec_rels:
                if r.type != "securedBy":
                    continue
                jsp_roles.setdefault(r.from_id, []).append(r)

            # For each route, compute transitive JSP set (rendered + included/redirected) and propagate roles
            existing_ids = {r.id for r in relations}
            added_route_relations = 0
            for route_id, direct_jsps in route_renders.items():
                # reachable includes starting from direct_jsps
                all_jsps = set(direct_jsps) | reachable_jsps(set(direct_jsps))
                # aggregate roles from all reachable JSPs
                roles_seen: Set[str] = set()
                evidence_by_role: Dict[str, List] = {}
                for jsp_id in all_jsps:
                    for r in jsp_roles.get(jsp_id, []):
                        role_id = r.to_id
                        # normalize role string like 'role_Admin'
                        role_name = role_id[len('role_'):] if role_id.startswith('role_') else role_id
                        if role_name in roles_seen:
                            # still collect evidence
                            evidence_by_role.setdefault(role_name, []).extend(r.evidence or [])
                            continue
                        roles_seen.add(role_name)
                        evidence_by_role.setdefault(role_name, []).extend(r.evidence or [])

                # Emit route securedBy relations from aggregated roles
                for role_name, evs_list in evidence_by_role.items():
                    new_id = f"rel_{route_id}->securedBy:{role_name}"
                    if new_id in existing_ids:
                        continue
                    existing_ids.add(new_id)
                    # Prefer route source evidence; fallback to aggregated JSP evidence
                    evs: List[Evidence] = []
                    route_ent = entity_index.get(route_id)
                    if route_ent and getattr(route_ent, 'source_refs', None):
                        evs.append(self.evidence.build_evidence_from_source_ref(route_ent.source_refs[0]))
                    else:
                        # attach deduped JSP evidence
                        evs = self.evidence.dedupe_evidence(self.evidence.maybe_sample_evidence(evs_list, new_id))
                    relations.append(
                        Relation(
                            id=new_id,
                            from_id=route_id,
                            to_id=f"role_{role_name}",
                            type="securedBy",
                            confidence=0.7,
                            evidence=evs,
                            rationale="propagated from rendered JSP security",
                        )
                    )
                    added_route_relations += 1

            # Optionally track stats: store temporary counters on assembler instance for later aggregation
            # We'll compute final stats near the end from relations/entities.

        # Ensure target resource entities exist
        for r in relations:
            if r.to_id.startswith("table_") and r.to_id not in entity_index:
                table_name = r.to_id[len("table_"):]
                entity_index[r.to_id] = Entity(id=r.to_id, type="Table", name=table_name)
            elif r.to_id.startswith("proc_") and r.to_id not in entity_index:
                proc_name = r.to_id[len("proc_"):]
                entity_index[r.to_id] = Entity(id=r.to_id, type="StoredProcedure", name=proc_name)
            elif r.to_id.startswith("role_") and r.to_id not in entity_index:
                role_name = r.to_id[len("role_"):]
                entity_index[r.to_id] = Entity(id=r.to_id, type="Role", name=role_name)

        # Attach/normalize/sample evidence per relation using config.provenance.evidence_sampling_rate
        for r in relations:
            if not r.id:
                r.id = f"rel_{r.from_id}->{r.type}:{r.to_id}"
            frm_ent = entity_index.get(r.from_id)
            # If no evidence, best-effort from from-entity source_ref
            if (not r.evidence) and frm_ent and frm_ent.source_refs:
                ev = self.evidence.build_evidence_from_source_ref(frm_ent.source_refs[0])
                if ev.file:
                    r.evidence = [ev]
            # Normalize existing evidence and propagate chunk_id if available on entity
            ent_chunk: Optional[str] = None
            if frm_ent and frm_ent.source_refs:
                cand = self.evidence.build_evidence_from_source_ref(frm_ent.source_refs[0])
                ent_chunk = cand.chunk_id
            if r.evidence:
                normalized: List[Evidence] = []
                for ev in r.evidence:
                    nev = self.evidence.build_evidence_from_file(ev.file, ev.line, ev.end_line, ev.chunk_id or ent_chunk)
                    normalized.append(nev)
                r.evidence = self.evidence.dedupe_evidence(self.evidence.maybe_sample_evidence(normalized, r.id))
            else:
                # Even if no source_refs, ensure empty list is consistent after sampling
                r.evidence = []

        # Deduplicate relations by ID to avoid repeats
        rel_index: Dict[str, Relation] = {}
        for r in relations:
            if r.id not in rel_index:
                rel_index[r.id] = r
        dedup_relations = list(rel_index.values())

        # Finalize entities/relations
        output.entities = list(entity_index.values())
        output.relations = dedup_relations

        # Build traces from assembled graph (always on; enrichment toggle applies for evidence aggregation)
        output.traces = self.tracer.build_traces({e.id: e for e in output.entities}, output.relations)

        # Optional: aggregate relation evidence into trace evidence when enabled
        if not self.cfg or getattr(self.cfg, 'enable_trace_enrichment', True):
            # Build quick indexes
            by_type_from: Dict[tuple[str, str], List[Relation]] = {}
            for rel in output.relations:
                by_type_from.setdefault((rel.type, rel.from_id), []).append(rel)
            for tr in output.traces:
                evs: List[Evidence] = []
                rid = tr.route
                scr = tr.screen
                # renders
                if rid and scr:
                    for rel in by_type_from.get(("renders", rid), []):
                        if rel.to_id == scr:
                            evs.extend(rel.evidence)
                            break
                # handlesRoute + CRUD when present
                method_id = None
                if tr.path and len(tr.path) >= 2 and tr.path[1].startswith("method_"):
                    method_id = tr.path[1]
                if rid and method_id:
                    for rel in by_type_from.get(("handlesRoute", rid), []):
                        if rel.to_id == method_id:
                            evs.extend(rel.evidence)
                            break
                    # CRUD edges from method
                    for t in ("readsFrom", "writesTo", "deletesFrom"):
                        for rel in by_type_from.get((t, method_id), []):
                            evs.extend(rel.evidence)
                # CRUD edges from JSPs in path (screen + chain)
                jsp_ids: List[str] = [scr] if scr else []
                if tr.path:
                    for nid in tr.path:
                        if isinstance(nid, str) and nid.startswith("jsp_") and nid not in jsp_ids:
                            jsp_ids.append(nid)
                for t in ("readsFrom", "writesTo", "deletesFrom"):
                    for jsp_id in jsp_ids:
                        for rel in by_type_from.get((t, jsp_id), []):
                            evs.extend(rel.evidence)
                tr.evidence = self.evidence.dedupe_evidence(evs)

        # Compute coverage stats
        routes_total = sum(1 for e in output.entities if e.type == "Route")
        handles_by_route = {r.from_id for r in output.relations if r.type == "handlesRoute"}
        renders_by_route = {r.from_id for r in output.relations if r.type == "renders"}
        # Consider routes that have an action_class, explicit servlet mapping, or a declared method
        # as valid handler endpoints even if a handlesRoute relation was not produced. This
        # covers streaming/forward-null handlers where we should not create JSP stubs.
        for e in output.entities:
            if getattr(e, 'type', None) == "Route":
                try:
                    attrs = getattr(e, 'attributes', {}) or {}
                except Exception:
                    attrs = {}
                # If route already has a handlesRoute relation, skip; otherwise infer handler
                if e.id not in handles_by_route:
                    action_class = attrs.get('action_class') if isinstance(attrs, dict) else None
                    method = attrs.get('method') if isinstance(attrs, dict) else None
                    result_jsp = attrs.get('result_jsp') if isinstance(attrs, dict) else None
                    # If there's an action_class or an explicit method or no result_jsp but an action is present,
                    # consider this route handled (streaming or servlet mapping)
                    if action_class or (method and str(method).strip()) or (attrs.get('action') and not result_jsp):
                        handles_by_route.add(e.id)

        routes_with_handler = len(handles_by_route)
        routes_with_view = len(renders_by_route)
        route_resolution_rate = (routes_with_handler / routes_total) if routes_total > 0 else 0.0
        jsp_link_coverage = (routes_with_view / routes_total) if routes_total > 0 else 0.0

        # DB edge coverage: proportion of method/JSP entities that have any DB relation
        db_ops = {"readsFrom", "writesTo", "deletesFrom"}
        db_sources_with_edges = {r.from_id for r in output.relations if r.type in db_ops}
        method_or_jsp_entities = {e.id for e in output.entities if e.type in ("JavaMethod", "JSP")}
        db_sources_total = len(method_or_jsp_entities)
        db_edge_coverage = (len(db_sources_with_edges & method_or_jsp_entities) / db_sources_total) if db_sources_total > 0 else 0.0

        roles_applied_count = sum(1 for r in output.relations if r.type == "securedBy")

        # Additional JSP-security counters (NEXT_STEPS requirement)
        # Count JSP files present in entities and how many have securedBy relations
        jsp_files_total = sum(1 for e in output.entities if e.type == "JSP")
        jsp_sec_rels = [r for r in output.relations if r.type == "securedBy" and isinstance(r.from_id, str) and r.from_id.startswith("jsp_")]
        jsp_files_secured = len({r.from_id for r in jsp_sec_rels})
        unique_secured_roles_count = len({r.to_id for r in output.relations if r.type == "securedBy"})
        # Routes secured by propagation from JSPs — we mark propagated relations with rationale containing 'propagated'
        routes_secured_from_jsps = sum(1 for r in output.relations if r.type == "securedBy" and isinstance(r.from_id, str) and r.from_id.startswith("route_") and (r.rationale or "").lower().find("propagated") != -1)

        output.stats = {
            "entity_count": len(output.entities),
            "relation_count": len(output.relations),
            "trace_count": len(output.traces),
            "routes_total": routes_total,
            "routes_with_view": routes_with_view,
            "routes_with_handler": routes_with_handler,
            "route_resolution_rate": route_resolution_rate,
            "jsp_link_coverage": jsp_link_coverage,
            "db_edge_coverage": db_edge_coverage,
            "roles_applied_count": roles_applied_count,
            # JSP-security stats
            "jsp_files_total": jsp_files_total,
            "jsp_files_secured": jsp_files_secured,
            "unique_secured_roles_count": unique_secured_roles_count,
            "routes_secured_from_jsps": routes_secured_from_jsps,
        }
        return output
