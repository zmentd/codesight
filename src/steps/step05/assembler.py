from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, cast

from config.config import Config
from config.sections import Step05Config
from llm.llm_client import LLMClient, LLMResponse
from steps.step04.evidence import EvidenceUtils
from steps.step04.models import Entity, Evidence, Relation, Step04Output, Trace
from steps.step05.models import Capability, CapabilityOutput, CapabilityRelation


class Step05Assembler:
    """Build capabilities/domains from Step04 outputs and Step03 embeddings.

    Notes:
        - Consumes Step04 entities/relations/traces and optionally Step03 vectors/clusters.
        - Uses an LLM to generate capability name, purpose, and synonyms with strict JSON.
        - Enforces quality gates for citations and coverage per config.
    """

    def __init__(self, cfg: Step05Config | None = None) -> None:
        self.cfg = cfg or Config.get_instance().steps.step05
        self.evidence = EvidenceUtils()
        # Initialize LLM lazily in assemble to honor runtime config/env; avoid failing constructor
        self._llm: Optional[LLMClient] = None

    def _get_llm(self) -> Optional[LLMClient]:
        if self._llm is None:
            try:
                # Respect step-level provider override if present
                global_cfg = Config.get_instance()
                step_provider = getattr(self.cfg, "llm_provider", None)
                if isinstance(step_provider, str) and step_provider:
                    global_cfg.llm.provider = step_provider
                self._llm = LLMClient()
            except (ImportError, RuntimeError, ValueError, TypeError, OSError):  # best effort, surfaces in provenance
                self._llm = None
        return self._llm

    def _normalize_role(self, role_id: str) -> str:
        """Normalize noisy role IDs (regex/scriptlet artifacts) into canonical role ids.
        Keeps known roles intact; collapses generic Security.* patterns to role_security.
        """
        rid = role_id
        if rid in {"role_security", "role_getSecurity"}:
            return rid
        low = rid.lower()
        if "<%" in rid or "security." in rid or "security" in low:
            return "role_security"
        return rid

    def _collect_group_members(self, route_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "routes": [route_id],
            "screens": sorted(list(data.get("screens", set()))),
            "handlers": sorted(list(data.get("methods", set()))),
            "tables": sorted(list({db for db, _ in data.get("db_relations", [])})),
            "rules": sorted(list(data.get("rules", set()))),
            "guards": sorted(list(data.get("security", set()))),
        }

    def _index_step03_chunks_by_path(self, step03: Optional[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Build a map of source_path -> list of embedding chunk dicts from Step03 output."""
        by_path: Dict[str, List[Dict[str, Any]]] = {}
        try:
            if not step03:
                return by_path
            chunks = (step03.get("step03_results") or {}).get("embedding_chunks", [])
            for ch in chunks:
                p = ch.get("source_path")
                if not isinstance(p, str):
                    continue
                by_path.setdefault(p, []).append(ch)
        except (KeyError, AttributeError, TypeError):
            return by_path
        return by_path

    def _index_step03_clusters(self, step03: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Map chunk_id -> cluster_id from Step03 semantic_clusters."""
        mapping: Dict[str, str] = {}
        try:
            clusters = ((step03 or {}).get("step03_results") or {}).get("semantic_clusters", [])
            for cl in clusters:
                cid = cl.get("cluster_id")
                for ch_id in cl.get("chunks", []) or []:
                    if isinstance(cid, str) and isinstance(ch_id, str):
                        mapping[ch_id] = cid
        except (KeyError, AttributeError, TypeError):
            return mapping
        return mapping

    def _gather_evidence_paths(self, rels: List[Relation]) -> Set[str]:
        paths: Set[str] = set()
        for r in rels:
            if r.evidence:
                for e in r.evidence:
                    if isinstance(e, Evidence) and e.file:
                        paths.add(e.file)
        return paths

    def _hash_prompt(self, prompt: str) -> str:
        try:
            return hashlib.sha1(prompt.encode("utf-8", errors="ignore")).hexdigest()  # nosec - non-crypto use
        except (UnicodeError, AttributeError, TypeError):
            return ""

    def _compose_llm_prompt(
        self,
        project: str,
        route_name: str,
        members: Dict[str, Any],
        rules: Set[str],
        roles: Set[str],
        crud: List[Tuple[str, str]],
        snippets: List[str],
    ) -> str:
        """Create a compact prompt instructing the LLM to return strict JSON for business capabilities."""
        summary: Dict[str, Any] = {
            "project": project,
            "route_or_domain": route_name,
            "members": members,
            "guards": sorted(list(roles)),
            "rules": sorted(list(rules)),
            "crud": [{"table": t, "op": op} for (t, op) in crud][:20],
            "snippets": [s[:800] for s in snippets][:5],
        }
        instruction = (
            "You are a senior business analyst. Using the provided route(s) and evidence, "
            "produce a concise business capability descriptor in strict JSON. "
            "Focus on the business purpose rather than technical implementation. "
            "If multiple routes are provided, identify the common business capability they serve together. "
            "Do not include prose outside JSON.\n"
            "Return JSON with keys: name (short, business-focused), purpose (1-2 sentences about business value), synonyms (array of up to 5 business terms)."
        )
        payload = json.dumps(summary, ensure_ascii=False)
        prompt = f"{instruction}\nINPUT:\n{payload}\nOUTPUT_JSON:"
        # Enforce max context length from config (best-effort)
        try:
            max_len = int(getattr(self.cfg, "max_context_length", 8000) or 8000)
        except (ValueError, TypeError, AttributeError):
            max_len = 8000
        if len(prompt) > max_len:
            # Truncate snippets first, then payload hard cut if needed
            trimmed: Dict[str, Any] = {**summary}
            trimmed_snips = list(summary.get("snippets", []))
            trimmed["snippets"] = [str(s)[:300] for s in trimmed_snips][:3]
            trimmed_crud = list(summary.get("crud", []))
            trimmed["crud"] = trimmed_crud[:10]
            payload = json.dumps(trimmed, ensure_ascii=False)
            prompt = f"{instruction}\nINPUT:\n{payload}\nOUTPUT_JSON:"
            if len(prompt) > max_len:
                prompt = prompt[:max_len]
        return prompt

    def _extract_first_json(self, text: str) -> Optional[str]:
        """Extract first top-level JSON object substring from text using brace matching."""
        start = text.find('{')
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(text)):
            c = text[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

    def _parse_llm_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, TypeError, ValueError):
            snippet = self._extract_first_json(text)
            if snippet:
                try:
                    parsed2 = json.loads(snippet)
                    return parsed2 if isinstance(parsed2, dict) else None
                except (json.JSONDecodeError, TypeError, ValueError):
                    return None
            return None

    def _call_llm_capability(self, prompt: str) -> Dict[str, Any]:
        client = self._get_llm()
        if client is None:
            return {}
        attempts = max(1, int(getattr(self.cfg, "retry_attempts", 1) or 1) + 1)
        last: Dict[str, Any] = {}
        # System message enforces strict JSON output
        sys_msg = (
            "You are a formatter. Return ONLY a single valid JSON object. "
            "No markdown, no code fences, no comments, no explanations. "
            "Use keys: name (string), purpose (string), synonyms (array of strings up to 5)."
        )
        for i in range(attempts):
            try:
                p = prompt if i == 0 else (prompt + "\nRespond with ONLY compact JSON for keys: name,purpose,synonyms. No prose.")
                resp: LLMResponse = client._make_request(p, system_message=sys_msg)
                if not getattr(resp, "success", False) or not isinstance(resp.content, str):
                    last = {}
                    continue
                parsed = self._parse_llm_json(resp.content.strip())
                if isinstance(parsed, dict):
                    parsed["_usage"] = resp.usage or {}
                    provider_obj = getattr(client, "provider", None)
                    provider_val = getattr(provider_obj, "value", None) if provider_obj is not None else None
                    parsed["_provider"] = provider_val
                    parsed["_model"] = getattr(client, "model", None)
                    return parsed
                last = {}
            except (RuntimeError, ValueError, TypeError, OSError):
                last = {}
        return last

    def _validate_capability_json(self, data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], List[str], Optional[str]]:
        """Validate required keys/types. Returns (name, purpose, synonyms, error_msg)."""
        name = data.get("name")
        purpose = data.get("purpose")
        syn = data.get("synonyms", [])
        if not isinstance(name, str) or not name.strip():
            return (None, None, [], "missing/invalid name")
        if not isinstance(purpose, str) or not purpose.strip():
            return (None, None, [], "missing/invalid purpose")
        synonyms: List[str] = []
        if isinstance(syn, list):
            synonyms = [str(x).strip() for x in syn if str(x).strip()][:5]
        return (name.strip(), purpose.strip(), synonyms, None)

    def _compose_rules_prompt(self, route_name: str, rules_text: List[str], roles: List[str]) -> str:
        """Prompt to paraphrase rules/guards into concise text."""
        payload = {
            "route": route_name,
            "guards": roles[:10],
            "rules": rules_text[:10],
        }
        instr = (
            "Summarize the business rules and access guards for this route into 1-3 concise sentences. "
            "Do not include code, IDs, or stack traces. Respond with plain text only."
        )
        return f"{instr}\nINPUT:\n{json.dumps(payload, ensure_ascii=False)}\nOUTPUT_TEXT:"

    def _call_llm_text(self, prompt: str) -> str:
        client = self._get_llm()
        if client is None:
            return ""
        try:
            resp: LLMResponse = client._make_request(prompt)
            if getattr(resp, "success", False) and isinstance(resp.content, str):
                return resp.content.strip()
        except (RuntimeError, ValueError, TypeError, OSError):
            return ""
        return ""

    def _classify_domain(self, tags: List[str], route_name: str, crud_pairs: List[Tuple[str, str]], roles: Set[str]) -> Optional[str]:
        """Lightweight heuristic domain labeling; can be replaced with LLM if needed."""
        t = set(x.lower() for x in tags)
        if any(op == "writesTo" or op == "deletesFrom" for (_, op) in crud_pairs):
            return "Transaction"
        if "secured" in t or len(roles) > 0:
            return "Security"
        if "screen" in t and "handler" in t:
            return "UI"
        if any(x.lower().endswith("dao") or x.lower().endswith("repository") for (x, _) in crud_pairs):
            return "Data Access"
        return None

    def _compose_domain_prompt(
        self,
        allowed_labels: List[str],
        name: str,
        purpose: str,
        tags: List[str],
        crud: List[Tuple[str, str]],
        roles: Set[str],
        route_names: Optional[List[str]] = None,
        path_fragments: Optional[List[str]] = None,
        allowed_layers: Optional[List[str]] = None,
        layer_hint: Optional[str] = None,
        subdomain_hints: Optional[List[str]] = None,
    ) -> str:
        payload = {
            "name": name,
            "purpose": purpose,
            "tags": tags[:10],
            "crud": [{"table": t, "op": op} for (t, op) in crud][:10],
            "guards": sorted(list(roles))[:10],
            "allowed_domains": allowed_labels,
        }
        if isinstance(route_names, list) and route_names:
            payload["route_paths"] = route_names[:10]
        if isinstance(path_fragments, list) and path_fragments:
            payload["path_fragments"] = path_fragments[:10]
        if isinstance(allowed_layers, list) and allowed_layers:
            payload["allowed_layers"] = allowed_layers[:10]
        if isinstance(layer_hint, str) and layer_hint:
            payload["layer_hint"] = layer_hint
        if isinstance(subdomain_hints, list) and subdomain_hints:
            payload["subdomain_hints"] = subdomain_hints[:10]
        instruction = (
            "Classify this capability into a single business domain from allowed_domains. "
            "Also infer the architectural layer from allowed_layers and the subdomain (based on directory/URL segments). "
            "Return strict JSON only with keys: domain (string from allowed_domains), layer (string from allowed_layers), subdomain (string), abstain (boolean). "
            "If uncertain, set abstain=true and leave domain/layer/subdomain empty strings."
        )
        prompt = f"{instruction}\nINPUT\n{json.dumps(payload, ensure_ascii=False)}\nOUTPUT_JSON:"
        # Bound size
        try:
            max_len = int(getattr(self.cfg, "max_context_length", 8000) or 8000)
        except (ValueError, TypeError, AttributeError):
            max_len = 8000
        if len(prompt) > max_len:
            prompt = prompt[:max_len]
        return prompt

    def _call_llm_domain(self, prompt: str) -> Dict[str, Any]:
        """Call LLM to classify domain with strict JSON response."""
        client = self._get_llm()
        if client is None:
            return {}
        attempts = max(1, int(getattr(self.cfg, "retry_attempts", 1) or 1) + 1)
        sys_msg = (
            "You are a formatter. Return ONLY a single valid JSON object. "
            "No markdown, no code fences, no comments, no explanations. "
            "Use keys: domain (string), abstain (boolean). Optional keys: layer (string), subdomain (string)."
        )
        last: Dict[str, Any] = {}
        for i in range(attempts):
            try:
                p = prompt if i == 0 else (prompt + "\nRespond with ONLY compact JSON for keys: domain,layer,subdomain,abstain. No prose.")
                resp: LLMResponse = client._make_request(p, system_message=sys_msg)
                if not getattr(resp, "success", False) or not isinstance(resp.content, str):
                    last = {}
                    continue
                parsed = self._parse_llm_json(resp.content.strip())
                if isinstance(parsed, dict):
                    parsed["_usage"] = resp.usage or {}
                    provider_obj = getattr(client, "provider", None)
                    provider_val = getattr(provider_obj, "value", None) if provider_obj is not None else None
                    parsed["_provider"] = provider_val
                    parsed["_model"] = getattr(client, "model", None)
                    return parsed
                last = {}
            except (RuntimeError, ValueError, TypeError, OSError):
                last = {}
        return last

    def _create_business_domain_groups(self, by_route: Dict[str, Dict], entities: Dict[str, Entity]) -> Dict[str, Dict[str, Any]]:
        """Group routes by business domain using URL patterns, shared tables, and security roles."""
        print(f"DEBUG: _create_business_domain_groups called with {len(by_route)} routes")
        
        # Step 1: Group routes by URL path patterns
        url_groups: Dict[str, List[str]] = {}
        
        for rid, data in by_route.items():
            r_ent = entities.get(rid)
            path = r_ent.attributes.get("path") if r_ent and r_ent.attributes else None
            route_name = path or (r_ent.name if r_ent and r_ent.name else rid.replace("route_", "", 1))
            
            # Extract business domain from URL pattern
            domain_key = self._extract_business_domain_from_path(route_name)
            url_groups.setdefault(domain_key, []).append(rid)
        
        print(f"DEBUG: URL grouping created {len(url_groups)} initial groups")
        print(f"DEBUG: URL groups distribution: {[(k, len(v)) for k, v in url_groups.items()]}")
        
        # Step 2: Further group by shared resources (tables, security roles)
        final_groups: Dict[str, Dict[str, Any]] = {}
        
        for domain_key, route_ids in url_groups.items():
            if len(route_ids) == 1:
                # Single route - check if it can be merged with similar domains
                rid = route_ids[0]
                data = by_route[rid]
                merged = False
                
                # Try to merge with existing groups based on shared tables/security
                for existing_key, existing_group in final_groups.items():
                    if self._should_merge_groups(data, existing_group):
                        existing_group["group_routes"].update({rid})
                        self._merge_group_data(existing_group, data, rid, entities)
                        merged = True
                        break
                
                if not merged:
                    # Create new group for this single route
                    final_groups[f"domain:{domain_key}"] = self._create_group_from_routes([rid], by_route, entities, domain_key)
            else:
                # Multiple routes with same URL pattern - create domain group
                final_groups[f"domain:{domain_key}"] = self._create_group_from_routes(route_ids, by_route, entities, domain_key)
        
        print(f"DEBUG: Final business domain grouping created {len(final_groups)} groups")
        print(f"DEBUG: Final group keys: {list(final_groups.keys())}")
        return final_groups
    
    def _extract_business_domain_from_path(self, route_path: str) -> str:
        """Extract business domain key from route path."""
        if not route_path:
            return "general"
        
        # Remove leading/trailing slashes and split
        path = route_path.strip("/").lower()
        segments = [s for s in path.split("/") if s]
        
        if not segments:
            return "general"
        
        first_segment = segments[0]
        
        # Map common URL patterns to business domains
        domain_mapping = {
            "employee": "employee_management", 
            "staff": "employee_management",
            "person": "employee_management",
            "schedule": "scheduling",
            "shift": "scheduling", 
            "calendar": "scheduling",
            "time": "timekeeping",
            "timesheet": "timekeeping",
            "payroll": "payroll",
            "pay": "payroll",
            "benefit": "benefits",
            "contract": "contracts",
            "labor": "labor_relations",
            "skill": "skills_qualifications",
            "approve": "approvals_workflow",
            "approval": "approvals_workflow",
            "position": "position_job_management",
            "job": "position_job_management",
            "holiday": "holidays_calendars",
            "overtime": "overtime_pay_rules",
            "report": "reporting_analytics",
            "admin": "administration",
            "config": "administration",
            "setup": "administration",
            "security": "security_access",
            "auth": "security_access",
            "integration": "integrations_interfaces",
            "interface": "integrations_interfaces",
            "api": "integrations_interfaces"
        }
        
        # Check if first segment matches known business domains
        for pattern, domain in domain_mapping.items():
            if pattern in first_segment:
                return domain
        
        # Check second segment if first didn't match
        if len(segments) > 1:
            second_segment = segments[1]
            for pattern, domain in domain_mapping.items():
                if pattern in second_segment:
                    return domain
        
        # Fallback to first segment or general
        return first_segment if len(first_segment) > 2 else "general"
    
    def _should_merge_groups(self, route_data: Dict, existing_group: Dict[str, Any]) -> bool:
        """Determine if a route should be merged with an existing group based on shared resources."""
        # Check for shared tables (strong signal for business coherence)
        route_tables = set(route_data.get("db", set()))
        group_tables = set(existing_group.get("db", set()))
        
        if route_tables and group_tables:
            shared_tables = route_tables.intersection(group_tables)
            if len(shared_tables) >= min(2, len(route_tables) * 0.5):  # At least 50% or 2 tables shared
                return True
        
        # Check for shared security roles
        route_security = set(route_data.get("security", set()))
        group_security = set(existing_group.get("security", set()))
        
        if route_security and group_security:
            shared_security = route_security.intersection(group_security)
            if len(shared_security) >= 1:  # Any shared security role
                return True
        
        return False
    
    def _create_group_from_routes(self, route_ids: List[str], by_route: Dict[str, Dict], entities: Dict[str, Entity], domain_key: str) -> Dict[str, Any]:
        """Create a group from multiple routes."""
        group = {
            "screens": set(), "methods": set(), "db": set(), "rules": set(), "security": set(),
            "relations": [], "trace_ids": set(), "db_relations": [],
            "group_routes": set(route_ids), "group_kind": "business_domain",
            "group_domain_key": domain_key, "route_names": []
        }
        
        for rid in route_ids:
            data = by_route[rid]
            self._merge_group_data(group, data, rid, entities)
        
        return group
    
    def _merge_group_data(self, group: Dict[str, Any], route_data: Dict, route_id: str, entities: Dict[str, Entity]) -> None:
        """Merge route data into a group."""
        group["screens"].update(route_data.get("screens", set()))
        group["methods"].update(route_data.get("methods", set()))
        group["db"].update(route_data.get("db", set()))
        group["rules"].update(route_data.get("rules", set()))
        group["security"].update(route_data.get("security", set()))
        group["relations"].extend(route_data.get("relations", []))
        group["trace_ids"].update(route_data.get("trace_ids", set()))
        group["db_relations"].extend(route_data.get("db_relations", []))
        
        # Add route name
        r_ent = entities.get(route_id)
        path = r_ent.attributes.get("path") if r_ent and r_ent.attributes else None
        route_name = path or (r_ent.name if r_ent and r_ent.name else route_id.replace("route_", "", 1))
        group["route_names"].append(route_name)

    def assemble(self, step04: Step04Output, step03: Optional[Dict[str, Any]] = None, on_progress: Optional[Callable[[Dict[str, Any]], None]] = None) -> CapabilityOutput:
        project_name = step04.project_name
        # Index graph
        entities: Dict[str, Entity] = {e.id: e for e in step04.entities}
        relations: List[Relation] = list(step04.relations)
        trace_list = list(step04.traces) if step04.traces else []

        # Quick lookup of Step04 relations by (from,type,to) for evidence harvesting
        rel_index: Dict[Tuple[str, str, str], Relation] = {}
        for r in relations:
            rel_index[(r.from_id, r.type, r.to_id)] = r

        # Group by Route as seed capability groups when there is either a view render or a handler
        by_route: Dict[str, Dict] = {}
        for r in relations:
            if r.type in ("renders", "handlesRoute"):
                data = by_route.setdefault(r.from_id, {
                    "screens": set(), "methods": set(), "db": set(), "rules": set(), "security": set(),
                    "relations": [], "trace_ids": set(), "db_relations": []
                })
                if r.type == "renders":
                    data["screens"].add(r.to_id)
                elif r.type == "handlesRoute":
                    data["methods"].add(r.to_id)
                data["relations"].append(r)

        # Optionally seed unlinked routes so coverage includes routes without explicit renders/handlers
        try:
            seed_unlinked = bool(getattr(self.cfg, "seed_unlinked_routes", False))
        except Exception:
            seed_unlinked = False
        if seed_unlinked:
            # Identify all Route entities
            all_routes: Set[str] = set(e.id for e in step04.entities if isinstance(e, Entity) and getattr(e, 'type', None) == 'Route')
            linked_routes: Set[str] = set(by_route.keys())
            # Some graphs may put route on the right-hand side; include those too
            for r in relations:
                if getattr(r, 'type', None) in ("renders", "handlesRoute") and isinstance(getattr(r, 'to_id', None), str):
                    if getattr(entities.get(r.to_id), 'type', None) == 'Route':
                        linked_routes.add(r.to_id)
            unlinked = all_routes - linked_routes
            for rid in sorted(unlinked):
                by_route.setdefault(rid, {
                    "screens": set(), "methods": set(), "db": set(), "rules": set(), "security": set(),
                    "relations": [], "trace_ids": set(), "db_relations": []
                })

        # Attach CRUD, rules, security to any seeded route from Step04 relations
        for r in relations:
            if r.type in {"readsFrom", "writesTo", "deletesFrom"}:
                src = r.from_id
                for rid, data in by_route.items():
                    if src in data["methods"] or src in data.get("screens", set()):
                        data["db"].add(r.to_id)
                        data["relations"].append(r)
                        data["db_relations"].append((r.to_id, r.type))
            elif r.type == "validatedBy":
                if r.from_id in by_route:
                    by_route[r.from_id]["rules"].add(r.to_id)
                    by_route[r.from_id]["relations"].append(r)
            elif r.type == "securedBy":
                if r.from_id in by_route:
                    by_route[r.from_id]["security"].add(r.to_id)
                    by_route[r.from_id]["relations"].append(r)

        # Also enrich CRUD and trace_ids from Step04 traces (covers cases where Step04 CRUD edges are indirect)
        route_to_traces: Dict[str, List[Trace]] = {}
        for tr in trace_list:
            if tr.route:
                route_to_traces.setdefault(tr.route, []).append(tr)
        for rid, data in by_route.items():
            for tr in route_to_traces.get(rid, []):
                data["trace_ids"].add(tr.id)
                crud = tr.crud_summary or {}
                for k, items in crud.items():
                    kind = k.lower()
                    if "read" in kind:
                        ctype = "readsFrom"
                    elif "write" in kind or "update" in kind or "insert" in kind:
                        ctype = "writesTo"
                    elif "delete" in kind:
                        ctype = "deletesFrom"
                    else:
                        ctype = "readsFrom"
                    for tbl in items:
                        data["db"].add(tbl)
                        data["db_relations"].append((tbl, ctype))
                if not crud and tr.tables:
                    for tbl in tr.tables:
                        data["db"].add(tbl)
                        data["db_relations"].append((tbl, "readsFrom"))

        # Step03 snippets index (optional)
        path_to_chunks = self._index_step03_chunks_by_path(step03)
        chunk_to_cluster = self._index_step03_clusters(step03)
        # Build lightweight aux indexes for suffix matching
        basename_index: Dict[str, List[Dict[str, Any]]] = {}
        tail2_index: Dict[str, List[Dict[str, Any]]] = {}
        for k, lst in path_to_chunks.items():
            nk = str(k).replace("\\", "/")
            base = nk.rsplit("/", 1)[-1]
            basename_index.setdefault(base, []).extend(lst)
            parts = nk.strip("/").split("/")
            if len(parts) >= 2:
                tail2 = "/".join(parts[-2:])
                tail2_index.setdefault(tail2, []).extend(lst)

        def _match_chunks_for_path(p: str) -> List[Dict[str, Any]]:
            if not p:
                return []
            norm = str(p).replace("\\", "/")
            # direct
            for t in (norm, norm.lstrip("/")):
                if t in path_to_chunks:
                    return path_to_chunks[t]
            # by basename
            base = norm.rsplit("/", 1)[-1]
            if base in basename_index:
                return basename_index[base]
            # by last two segments
            parts2 = norm.strip("/").split("/")
            if len(parts2) >= 2:
                tail2 = "/".join(parts2[-2:])
                if tail2 in tail2_index:
                    return tail2_index[tail2]
            return []

        # Pre-compute a primary/top semantic cluster per route from evidence paths
        route_top_cluster: Dict[str, Optional[str]] = {}
        for rid, data in by_route.items():
            evidence_paths = self._gather_evidence_paths(data["relations"]) or set()
            route_chunk_ids_seen: Set[str] = set()
            for p in sorted(list(evidence_paths)):
                for ch in _match_chunks_for_path(p)[:1]:
                    cid = ch.get("chunk_id")
                    if isinstance(cid, str):
                        route_chunk_ids_seen.add(cid)
            cluster_counts: Counter[str] = Counter()
            for ch_id in route_chunk_ids_seen:
                cid = chunk_to_cluster.get(ch_id)
                if cid:
                    cluster_counts[cid] += 1
            route_top_cluster[rid] = cluster_counts.most_common(1)[0][0] if cluster_counts else None

        # Build groups: Business domain grouping instead of per-route
        groups: Dict[str, Dict[str, Any]] = {}
        
        # Enable business domain grouping by default
        enable_business_grouping = getattr(self.cfg, "enable_business_grouping", True)
        print(f"DEBUG: enable_business_grouping = {enable_business_grouping}")
        print(f"DEBUG: Processing {len(by_route)} routes for grouping")
        
        if enable_business_grouping:
            # Business domain grouping strategy
            print(f"DEBUG: Starting business domain grouping for {len(by_route)} routes")
            try:
                groups = self._create_business_domain_groups(by_route, entities)
                # Log success for debugging
                print(f"DEBUG: Business domain grouping created {len(groups)} groups from {len(by_route)} routes")
                print(f"DEBUG: Group keys: {list(groups.keys())}")
            except Exception as e:
                print(f"DEBUG: Business domain grouping failed: {e}, falling back to cluster grouping")
                import traceback
                traceback.print_exc()
                enable_business_grouping = False
        else:
            print(f"DEBUG: Using fallback grouping (cluster or per-route) for {len(by_route)} routes")
            # Fallback to cluster groups or per-route
            cluster_to_routes: Dict[str, Set[str]] = {}
            if getattr(self.cfg, "enable_cluster_grouping", False):
                for rid, cid in route_top_cluster.items():
                    if cid:
                        cluster_to_routes.setdefault(cid, set()).add(rid)
            for rid, data in by_route.items():
                # Determine group key
                cid = route_top_cluster.get(rid)
                is_cluster_group = False
                if getattr(self.cfg, "enable_cluster_grouping", False) and cid and len(cluster_to_routes.get(cid, set())) >= 2:
                    group_key = f"cluster:{cid}"
                    is_cluster_group = True
                else:
                    group_key = f"route:{rid}"
                grp = groups.setdefault(group_key, {
                    "screens": set(), "methods": set(), "db": set(), "rules": set(), "security": set(),
                    "relations": [], "trace_ids": set(), "db_relations": [],
                    "group_routes": set(), "group_kind": ("cluster" if is_cluster_group else "route"),
                    "group_cluster_id": (cid if is_cluster_group else None), "route_names": []
                })
                # Merge
                grp["screens"].update(data.get("screens", set()))
                grp["methods"].update(data.get("methods", set()))
                grp["db"].update(data.get("db", set()))
                grp["rules"].update(data.get("rules", set()))
                grp["security"].update(data.get("security", set()))
                grp["relations"].extend(data.get("relations", []))
                grp["trace_ids"].update(data.get("trace_ids", set()))
                grp["db_relations"].extend(data.get("db_relations", []))
                grp["group_routes"].add(rid)
                # Capture a display name for this route
                r_ent = entities.get(rid)
                path = r_ent.attributes.get("path") if r_ent and r_ent.attributes else None
                route_name = path or (r_ent.name if r_ent and r_ent.name else rid.replace("route_", "", 1))
                grp["route_names"].append(route_name)

        # Emit init progress with total groups
        if on_progress:
            on_progress({"phase": "init", "groups_total": len(groups)})

        # Local helpers
        def _get_evidence(from_id: str, typ: str, to_id: str) -> List[Dict]:
            rel = rel_index.get((from_id, typ, to_id))
            if rel and rel.evidence:
                return [e.to_dict() for e in rel.evidence]
            return []

        def _get_evidence_any(from_ids: Set[str], typ: str, to_id: str) -> List[Dict]:
            for fid in sorted(list(from_ids)):
                ev = _get_evidence(fid, typ, to_id)
                if ev:
                    return ev
            return []

        def _get_crud_evidence(route_id: str, methods: Set[str], crud_type: str, db_id: str) -> List[Dict]:
            ev = _get_evidence(route_id, crud_type, db_id)
            if ev:
                return ev
            for m in methods:
                ev = _get_evidence(m, crud_type, db_id)
                if ev:
                    return ev
            ev_list: List[Dict] = []
            for tr in route_to_traces.get(route_id, []):
                appears = False
                try:
                    crud = tr.crud_summary or {}
                    for items in crud.values():
                        if db_id in items:
                            appears = True
                            break
                except (KeyError, AttributeError, TypeError):
                    pass
                if not appears:
                    try:
                        if getattr(tr, 'tables', None) and db_id in tr.tables:
                            appears = True
                    except (AttributeError, TypeError):
                        pass
                if appears and tr.evidence:
                    ev_list.extend([e.to_dict() for e in tr.evidence if isinstance(e, Evidence)])
            return ev_list

        def _get_crud_evidence_any(route_ids: Set[str], methods: Set[str], crud_type: str, db_id: str) -> List[Dict]:
            for rid in sorted(list(route_ids)):
                ev = _get_crud_evidence(rid, methods, crud_type, db_id)
                if ev:
                    return ev
            return []

        capabilities: List[Capability] = []
        cap_relations: List[CapabilityRelation] = []
        llm_calls = 0
        llm_failures = 0
        llm_abstains = 0
        caps_with_cluster = 0
        schema_failures = 0
        llm_domain_calls = 0
        llm_domain_failures = 0
        llm_domain_abstains = 0

        # New: task/progress tracking
        groups_total = 0
        tasks_total = 0
        tasks_attempted = 0
        tasks_succeeded = 0
        tasks_failed_count = 0
        tasks_abstained_count = 0
        # breakdown
        naming_total = 0
        naming_success = 0
        naming_failed = 0
        naming_abstained = 0
        rules_total = 0
        rules_success = 0
        rules_failed = 0
        domain_total = 0
        domain_success = 0
        domain_failed = 0
        domain_abstained = 0

        # Build capabilities per group (route or cluster)
        for gkey, data in sorted(groups.items(), key=lambda x: x[0]):
            groups_total += 1
            # Naming task accounting
            naming_total += 1
            tasks_total += 1
            tasks_attempted += 1

            group_routes: Set[str] = set(data.get("group_routes", set())) or set()
            representative_rid: Optional[str] = sorted(list(group_routes))[0] if group_routes else None
            if representative_rid is None:
                # Skip invalid group
                continue
            r_ent = entities.get(representative_rid)
            path = r_ent.attributes.get("path") if r_ent and r_ent.attributes else None
            rep_route_name = path or (r_ent.name if r_ent and r_ent.name else representative_rid.replace("route_", "", 1))
            # Determine group display name and capability ID
            if data.get("group_kind") == "business_domain":
                domain_key = data.get("group_domain_key", "unknown")
                route_display = ", ".join(sorted(data.get("route_names", []))[:3])
                route_name = f"{domain_key.replace('_', ' ').title()}: {route_display}" if route_display else domain_key.replace('_', ' ').title()
                cap_id = f"cap_domain_{domain_key}"
            elif data.get("group_kind") == "cluster":
                cid = data.get("group_cluster_id")
                route_display = ", ".join(sorted(data.get("route_names", []))[:3])
                route_name = f"Cluster {cid}: {route_display}" if route_display else f"Cluster {cid}"
                cap_id = f"cap_cluster_{cid}"
            else:
                route_name = rep_route_name
                cap_id = f"cap_{representative_rid}"

            # Notify group start
            if on_progress:
                on_progress({"phase": "group_start", "group_key": gkey, "route": route_name})

            # citations: collect evidence from relations and traces (across all routes in group)
            raw_evs: List[Evidence] = []
            for rel in data["relations"]:
                if rel.evidence:
                    for ev in rel.evidence:
                        if isinstance(ev, Evidence):
                            raw_evs.append(ev)
            for rid in group_routes:
                for tr in route_to_traces.get(rid, []):
                    if tr.evidence:
                        raw_evs.extend([ev for ev in tr.evidence if isinstance(ev, Evidence)])
            deduped: List[Evidence] = self.evidence.dedupe_evidence(raw_evs)
            citations: List[Dict] = [e.to_dict() for e in deduped]

            # tags
            tag_set: Set[str] = set()
            for s in data["db"]:
                ent = entities.get(s)
                etype = getattr(ent, 'type', None) if ent is not None else None
                if isinstance(etype, str):
                    tag_set.add(etype)
            if data["screens"]:
                tag_set.add("Screen")
            if data["methods"]:
                tag_set.add("Handler")
            if data["security"]:
                tag_set.add("Secured")
            if data["rules"]:
                tag_set.add("Rules")
            # Add business domain tag if applicable
            if data.get("group_kind") == "business_domain" and data.get("group_domain_key"):
                tag_set.add(f"BusinessDomain:{data['group_domain_key']}")
            # Add cluster tag if applicable
            elif data.get("group_kind") == "cluster" and data.get("group_cluster_id"):
                tag_set.add(f"Cluster:{data['group_cluster_id']}")
            # New: tag if any stored procedures are invoked in this group
            if any(getattr(rel, 'type', '') == 'invokesProcedure' for rel in (data.get('relations') or [])):
                tag_set.add("StoredProcedure")
            tags = sorted(tag_set)

            # members and snippet harvesting for LLM
            members = self._collect_group_members(representative_rid, data)
            # Override routes list to include all grouped routes
            members["routes"] = sorted(list(group_routes))

            # CRUD summary tuples for prompt
            crud_pairs = sorted(list({(tbl, ct) for (tbl, ct) in data.get("db_relations", [])}))

            # Normalize roles for prompt context
            norm_roles: Set[str] = set(self._normalize_role(r) for r in data.get("security", set()))

            evidence_paths = self._gather_evidence_paths(data["relations"]) or set()

            # Enrich members for Step06 rendering
            # Derive a simple menu path from the first route path-like string
            menu_path: Optional[str] = None
            for rn in sorted(list(data.get("route_names", []))):
                if isinstance(rn, str) and ("/" in rn or rn.startswith("/")):
                    segs = [s for s in rn.split("/") if s]
                    if segs:
                        menu_path = " > ".join(segs[:3])
                        break
            if menu_path:
                members["menu_path"] = menu_path

            # Screen details (best-effort from entity attributes)
            screens_details: List[Dict[str, Any]] = []
            for sid in sorted(list(data.get("screens", set()))):
                ent = entities.get(sid)
                if not ent:
                    continue
                screen_det: Dict[str, Any] = {"id": sid, "name": getattr(ent, "name", None) or sid}
                try:
                    attrs = getattr(ent, "attributes", None) or {}
                    for k in ("title", "path", "view", "template"):
                        if k in attrs and attrs[k]:
                            screen_det[k] = attrs[k]
                except (AttributeError, TypeError, ValueError):
                    pass
                screens_details.append(screen_det)
            if screens_details:
                members["screens_details"] = screens_details

            # Handler details (best-effort from entity attributes)
            handlers_details: List[Dict[str, Any]] = []
            for mid in sorted(list(data.get("methods", set()))):
                ent = entities.get(mid)
                if not ent:
                    continue
                handler_det: Dict[str, Any] = {"id": mid, "name": getattr(ent, "name", None) or mid}
                try:
                    attrs = getattr(ent, "attributes", None) or {}
                    for k in ("class", "method", "signature", "file"):
                        if k in attrs and attrs[k]:
                            handler_det[k] = attrs[k]
                except (AttributeError, TypeError, ValueError):
                    pass
                handlers_details.append(handler_det)
            if handlers_details:
                members["handlers_details"] = handlers_details

            # DB usage summary: counts per table by op and example evidence
            db_usage_index: Dict[str, Dict[str, Any]] = {}
            for tbl, op in data.get("db_relations", []):
                entry = db_usage_index.setdefault(tbl, {"table": tbl, "reads": 0, "writes": 0, "deletes": 0, "examples": {"readsFrom": [], "writesTo": [], "deletesFrom": []}})
                if op == "readsFrom":
                    entry["reads"] += 1
                elif op == "writesTo":
                    entry["writes"] += 1
                elif op == "deletesFrom":
                    entry["deletes"] += 1
            # Attach example evidence snippets per op (bounded)
            if db_usage_index:
                for tbl, info in db_usage_index.items():
                    for op in ("readsFrom", "writesTo", "deletesFrom"):
                        try:
                            evs = _get_crud_evidence_any(group_routes, set(data.get("methods", set())), op, tbl)
                            # Only include essential fields to keep small
                            slim = []
                            for ev in evs[:2]:
                                if isinstance(ev, dict):
                                    slim.append({k: ev.get(k) for k in ("file", "start_line", "end_line", "text") if k in ev})
                            info["examples"][op] = slim
                        except (RuntimeError, ValueError, TypeError):
                            info["examples"][op] = []
                db_usage_list: List[Dict[str, Any]] = list(db_usage_index.values())
                db_usage_list.sort(key=lambda x: str(x.get("table", "")))
                members["db_usage"] = db_usage_list

            # New: Stored procedure usage summary (calls, tables by op, and example evidence)
            proc_ids: Set[str] = set()
            for rel in (data.get("relations") or []):
                rtype = getattr(rel, 'type', None)
                to_id = getattr(rel, 'to_id', None)
                if rtype == 'invokesProcedure' and isinstance(to_id, str) and to_id.startswith('proc_'):
                    proc_ids.add(to_id)
            if proc_ids:
                proc_usage_index: Dict[str, Dict[str, Any]] = {}
                # Prepare combined from_ids to search for evidence quickly (routes + methods + screens)
                from_ids: Set[str] = set(group_routes)
                from_ids.update(set(data.get("methods", set())))
                from_ids.update(set(data.get("screens", set())))
                relations_list = list(data.get("relations") or [])
                for pid in sorted(proc_ids):
                    proc_norm = pid[len('proc_'):] if pid.startswith('proc_') else str(pid)
                    info = proc_usage_index.setdefault(proc_norm, {
                        "procedure": proc_norm,
                        "calls": 0,
                        "tables": {"reads": [], "writes": [], "deletes": []},
                        "examples": []
                    })
                    # Count calls and collect relation-level evidence examples
                    examples: List[Dict[str, Any]] = []
                    for rel in relations_list:
                        if getattr(rel, 'type', None) == 'invokesProcedure' and getattr(rel, 'to_id', None) == pid:
                            info["calls"] += 1
                            evs = getattr(rel, 'evidence', None) or []
                            for ev in evs[:2]:
                                if isinstance(ev, Evidence):
                                    examples.append({k: getattr(ev, k, None) for k in ("file", "start_line", "end_line", "text")})
                                elif isinstance(ev, dict):
                                    examples.append({k: ev.get(k) for k in ("file", "start_line", "end_line", "text") if k in ev})
                    # If no relation-level evidence, try lookup via index from multiple from_ids
                    if not examples:
                        evs2 = _get_evidence_any(from_ids, 'invokesProcedure', pid)
                        for ev in evs2[:2]:
                            if isinstance(ev, dict):
                                examples.append({k: ev.get(k) for k in ("file", "start_line", "end_line", "text") if k in ev})
                    info["examples"] = examples[:2]
                    # Associate tables touched via this procedure by scanning CRUD relations with rationale mentions
                    reads: Set[str] = set()
                    writes: Set[str] = set()
                    deletes: Set[str] = set()
                    proc_norm_lc = proc_norm.lower()
                    for rel in relations_list:
                        rtype = getattr(rel, 'type', None)
                        if rtype not in ("readsFrom", "writesTo", "deletesFrom"):
                            continue
                        rat = getattr(rel, 'rationale', None)
                        rat_lc = rat.lower() if isinstance(rat, str) else ""
                        if proc_norm_lc and proc_norm_lc not in rat_lc:
                            continue
                        to_id = getattr(rel, 'to_id', None)
                        if isinstance(to_id, str) and to_id.startswith('table_'):
                            tbl = to_id[len('table_'):]
                            if rtype == "readsFrom":
                                reads.add(tbl)
                            elif rtype == "writesTo":
                                writes.add(tbl)
                            elif rtype == "deletesFrom":
                                deletes.add(tbl)
                    info["tables"] = {
                        "reads": sorted(list(reads))[:20],
                        "writes": sorted(list(writes))[:20],
                        "deletes": sorted(list(deletes))[:20],
                    }
                if proc_usage_index:
                    members["procedures_usage"] = sorted(proc_usage_index.values(), key=lambda x: str(x.get("procedure", "")))

            # snippets for LLM
            snippets: List[str] = []
            route_chunk_ids: Set[str] = set()
            for p in sorted(list(evidence_paths)):
                file_chunks = _match_chunks_for_path(p)
                for ch in file_chunks[:1]:  # at most 1 per file to bound context
                    txt = ch.get("content")
                    if isinstance(txt, str) and txt.strip():
                        snippets.append(txt)
                    cid2 = ch.get("chunk_id")
                    if isinstance(cid2, str):
                        route_chunk_ids.add(cid2)
                if len(snippets) >= 5:
                    break

            # LLM call
            prompt = self._compose_llm_prompt(project_name, route_name, members, data.get("rules", set()), norm_roles, crud_pairs, snippets)
            prompt_hash = self._hash_prompt(prompt)
            # Progress: naming phase start
            if on_progress:
                on_progress({"phase": "naming", "route": route_name, "status": "calling_llm"})
            llm_out = self._call_llm_capability(prompt)
            llm_calls += 1
            name: Optional[str] = None
            purpose: Optional[str] = None
            synonyms: List[str] = []
            abstain_flag = False
            naming_success_flag = False
            if llm_out:
                # explicit abstain support
                if bool(llm_out.get("abstain")) or str(llm_out.get("status", "")).lower() in {"abstain", "skip", "none"}:
                    abstain_flag = True
                else:
                    n_val, p_val, syns, err = self._validate_capability_json(llm_out)
                    if err is not None:
                        schema_failures += 1
                        llm_failures += 1
                    else:
                        name = n_val
                        purpose = p_val
                        synonyms = syns
                        naming_success_flag = True
            else:
                llm_failures += 1
            
            # Update naming task results
            if naming_success_flag:
                naming_success += 1
                tasks_succeeded += 1
                if on_progress:
                    on_progress({"phase": "naming_done", "route": route_name, "result": "succeeded"})
            elif abstain_flag:
                naming_abstained += 1
                tasks_abstained_count += 1
                if on_progress:
                    on_progress({"phase": "naming_done", "route": route_name, "result": "abstained"})
            else:
                naming_failed += 1
                tasks_failed_count += 1
                if on_progress:
                    on_progress({"phase": "naming_done", "route": route_name, "result": "failed"})

            if abstain_flag or not name:
                llm_abstains += 1
                if data.get("group_kind") == "business_domain" and data.get("group_domain_key"):
                    domain_key = data["group_domain_key"]
                    name = f"{domain_key.replace('_', ' ').title()} Management"
                else:
                    name = f"Capability: {route_name}"
            if not purpose:
                if data.get("group_kind") == "business_domain":
                    route_count = len(group_routes)
                    name_display = name or "Business Function"
                    purpose = f"{name_display} encompassing {route_count} route{'s' if route_count != 1 else ''} with screens and data access"
                else:
                    purpose = f"Journey for {route_name} including screens and data access"

            # Confidence heuristic + optional boost if LLM responded
            size = (
                len(data["relations"]) + len(data["db"]) + len(data["rules"]) + len(data["security"]) +
                len(data["screens"]) + len(data["methods"]) + max(0, len(group_routes) - 1)
            )
            confidence = min(0.99, 0.4 + 0.05 * size + (0.05 if llm_out else 0.0))

            provenance: Dict[str, Any] = {}
            if llm_out:
                provenance.setdefault("llm", {})
                provenance["llm"].update({
                    "provider": llm_out.get("_provider"),
                    "model": llm_out.get("_model"),
                    "usage": llm_out.get("_usage", {}),
                    "prompt_kind": "capability_namer_v1",
                    "prompt_hash": prompt_hash,
                })

            # Attach semantic cluster context
            if data.get("group_kind") == "cluster" and data.get("group_cluster_id"):
                provenance.setdefault("semantic", {})["top_cluster_id"] = data["group_cluster_id"]
                caps_with_cluster += 1
            else:
                top_counts: Counter[str] = Counter()
                for ch_id in route_chunk_ids:
                    cid3 = chunk_to_cluster.get(ch_id)
                    if cid3:
                        top_counts[cid3] += 1
                if top_counts:
                    top_cluster, _ = top_counts.most_common(1)[0]
                    provenance.setdefault("semantic", {})["top_cluster_id"] = top_cluster
                    if top_cluster and f"Cluster:{top_cluster}" not in tags:
                        tags.append(f"Cluster:{top_cluster}")
                    caps_with_cluster += 1

            # Optional business rules paraphrasing
            rationale: Optional[str] = None
            if self.cfg.enable_business_logic_extraction and (data.get("rules") or data.get("security")):
                # Rules task accounting
                rules_total += 1
                tasks_total += 1
                tasks_attempted += 1
                
                rule_texts: List[str] = []
                for ru in sorted(list(data.get("rules", []))):
                    ent = entities.get(ru)
                    if ent is None:
                        continue
                    msg = None
                    try:
                        attrs = getattr(ent, 'attributes', None) or {}
                        msg = attrs.get('message') or attrs.get('description')
                    except (AttributeError, TypeError, KeyError):
                        msg = None
                    rule_texts.append(str(msg or ent.name or ru))
                roles_list = sorted(list(norm_roles))
                rules_prompt = self._compose_rules_prompt(route_name, rule_texts, roles_list)
                if on_progress:
                    on_progress({"phase": "rules", "route": route_name, "status": "summarizing"})
                rules_text = self._call_llm_text(rules_prompt)
                if rules_text:
                    rationale = rules_text
                    rules_success += 1
                    tasks_succeeded += 1
                    if "llm" in provenance:
                        provenance["llm"]["rules_paraphrase"] = True
                    if on_progress:
                        on_progress({"phase": "rules_done", "route": route_name, "result": "succeeded"})
                else:
                    rules_failed += 1
                    tasks_failed_count += 1
                    if on_progress:
                        on_progress({"phase": "rules_done", "route": route_name, "result": "failed"})

            # Optional domain classification (heuristic-first with LLM fallback)
            domain_label: Optional[str] = None
            domain_layer: Optional[str] = None
            domain_subdomain: Optional[str] = None
            if self.cfg.enable_domain_classification:
                domain_total += 1
                tasks_total += 1
                tasks_attempted += 1
                if on_progress:
                    on_progress({"phase": "domain", "route": route_name, "status": "classifying"})
                
                # Strategy: always_llm | llm_first | heuristic_first (default to always_llm for accuracy)
                strategy = str(getattr(self.cfg, "domain_strategy", "always_llm") or "always_llm").lower()
                if strategy not in {"always_llm", "llm_first", "heuristic_first"}:
                    strategy = "always_llm"

                # Heuristic quick pass (used as guardrail/override or fallback)
                heuristic_label = self._classify_domain(tags, route_name, crud_pairs, norm_roles)

                def _mark_success() -> None:
                    nonlocal domain_success, tasks_succeeded
                    domain_success += 1
                    tasks_succeeded += 1
                    if on_progress:
                        on_progress({"phase": "domain_done", "route": route_name, "result": "succeeded"})

                def _mark_failed() -> None:
                    nonlocal domain_failed, tasks_failed_count
                    domain_failed += 1
                    tasks_failed_count += 1
                    if on_progress:
                        on_progress({"phase": "domain_done", "route": route_name, "result": "failed"})

                def _mark_abstained() -> None:
                    nonlocal domain_abstained, tasks_abstained_count
                    domain_abstained += 1
                    tasks_abstained_count += 1
                    if on_progress:
                        on_progress({"phase": "domain_done", "route": route_name, "result": "abstained"})

                # If heuristic-first and we have a label, short-circuit without LLM
                if strategy == "heuristic_first" and heuristic_label:
                    domain_label = heuristic_label
                    _mark_success()
                else:
                    # Prepare LLM domain prompt
                    allowed_labels = list(getattr(self.cfg, "domain_labels", []) or [])
                    if not allowed_labels:
                        allowed_labels = [
                            "Employee Management", "Scheduling", "Timekeeping", "Payroll", "Benefits",
                            "Labor Relations", "Contracts", "Skills and Qualifications", "Approvals and Workflow",
                            "Position and Job Management", "Holidays and Calendars", "Overtime and Pay Rules",
                            "Reporting and Analytics", "Security and Access Control", "Administration and Configuration",
                            "Integrations and Interfaces"
                        ]
                    try:
                        allowed_layers = list(Config.get_instance().classification.layers or [])
                    except (AttributeError, TypeError, ValueError):
                        allowed_layers = [
                            "UI", "Service", "Database", "Integration", "Configuration", "Reporting", "Utility", "Other"
                        ]
                    # Derive lightweight layer hint from tags/CRUD
                    layer_hint: Optional[str] = None
                    if any(op in {"writesTo", "deletesFrom"} for (_, op) in crud_pairs):
                        layer_hint = "Database"
                    elif "Screen" in tags or "Handler" in tags:
                        layer_hint = "UI"
                    elif "Rules" in tags or "Secured" in tags:
                        layer_hint = "Service"

                    route_names_list = list(data.get("route_names", []))

                    # Build path fragments and subdomain hints from evidence paths and route segments
                    path_frags: List[str] = []
                    for pth in sorted(list(evidence_paths))[:20]:
                        try:
                            normp = str(pth).replace("\\", "/")
                            segs = [s for s in normp.strip("/").split("/") if s]
                            if len(segs) >= 3:
                                path_frags.append("/".join(segs[-3:]))
                            elif len(segs) >= 2:
                                path_frags.append("/".join(segs[-2:]))
                            elif segs:
                                path_frags.append(segs[-1])
                        except (AttributeError, TypeError, ValueError, UnicodeError):
                            continue
                    sub_hints_set: Set[str] = set()
                    for rp in route_names_list:
                        if isinstance(rp, str):
                            try:
                                segs = [s for s in str(rp).split("/") if s]
                                sub_hints_set.update(segs[:2])
                            except (AttributeError, TypeError, ValueError, UnicodeError):
                                pass
                    for pth in list(evidence_paths)[:20]:
                        try:
                            normp = str(pth).replace("\\", "/")
                            segs = [s for s in normp.strip("/").split("/") if s]
                            sub_hints_set.update(segs[:2])
                        except (AttributeError, TypeError, ValueError, UnicodeError):
                            pass
                    sub_hints = sorted(list(sub_hints_set))[:10]

                    # Compose and call LLM
                    d_prompt = self._compose_domain_prompt(
                        allowed_labels=allowed_labels,
                        name=(name or route_name),
                        purpose=(purpose or ""),
                        tags=tags,
                        crud=crud_pairs,
                        roles=norm_roles,
                        route_names=route_names_list,
                        path_fragments=path_frags,
                        allowed_layers=allowed_layers,
                        layer_hint=layer_hint,
                        subdomain_hints=sub_hints,
                    )
                    d_prompt_hash = self._hash_prompt(d_prompt)
                    d_out = self._call_llm_domain(d_prompt)
                    llm_domain_calls += 1

                    if not d_out:
                        llm_domain_failures += 1
                        # If LLM failed and we have a heuristic label, use it
                        if heuristic_label:
                            domain_label = heuristic_label
                            provenance.setdefault("llm", {})
                            provenance["llm"]["domain_classifier"] = False
                            provenance["llm"]["domain_prompt_hash"] = d_prompt_hash
                            provenance.setdefault("domain_source", "heuristic_fallback_after_llm_failure")
                            _mark_success()
                        else:
                            _mark_failed()
                    else:
                        # Attach LLM provenance
                        provenance.setdefault("llm", {})
                        provenance["llm"].update({
                            "domain_classifier": True,
                            "domain_prompt_hash": d_prompt_hash,
                        })
                        # Record provider/model/usage specifically for domain call
                        provenance["llm"].setdefault("domain_call", {}).update({
                            "provider": d_out.get("_provider"),
                            "model": d_out.get("_model"),
                            "usage": d_out.get("_usage", {}),
                        })

                        abstain_val = bool(d_out.get("abstain"))
                        dom_val = d_out.get("domain")
                        layer_val = d_out.get("layer")
                        sub_val = d_out.get("subdomain")
                        if abstain_val or not isinstance(dom_val, str) or not dom_val.strip():
                            llm_domain_abstains += 1
                            # If LLM abstains but heuristic has a label, use heuristic
                            if heuristic_label:
                                domain_label = heuristic_label
                                provenance.setdefault("domain_source", "heuristic_fallback_after_llm_abstain")
                                _mark_success()
                            else:
                                _mark_abstained()
                        else:
                            domain_label = dom_val.strip()
                            domain_layer = layer_val.strip() if isinstance(layer_val, str) and layer_val.strip() else None
                            domain_subdomain = sub_val.strip() if isinstance(sub_val, str) and sub_val.strip() else None
                            # Conflict annotation if heuristic disagrees
                            if heuristic_label and heuristic_label != domain_label:
                                provenance.setdefault("domain_conflict", {}).update({
                                    "heuristic": heuristic_label,
                                    "llm": domain_label,
                                })
                            # Tag with layer/subdomain for downstream rendering
                            if domain_layer and f"Layer:{domain_layer}" not in tags:
                                tags.append(f"Layer:{domain_layer}")
                            if domain_subdomain and f"Subdomain:{domain_subdomain}" not in tags:
                                tags.append(f"Subdomain:{domain_subdomain}")
                            _mark_success()

            # Build capability object
            cap = Capability(
                id=cap_id,
                name=name or (rep_route_name or cap_id),
                purpose=purpose or "",
                confidence=float(confidence),
                citations=citations,
                synonyms=synonyms,
                members=members,
                tags=tags,
                domain=domain_label,
                rationale=rationale,
                trace_ids=sorted(list(data.get("trace_ids", set()))),
                provenance=provenance,
            )
            capabilities.append(cap)

            # Notify group done
            if on_progress:
                on_progress({"phase": "group_done", "group_key": gkey, "route": route_name, "result": "completed"})

        # Compute coverage: how many routes represented by capabilities vs total routes in Step04
        total_routes = sum(1 for e in step04.entities if isinstance(e, Entity) and getattr(e, 'type', None) == 'Route')
        covered_routes = len(capabilities)
        route_coverage_pct = float(covered_routes / total_routes) if total_routes > 0 else 1.0

        # Aggregate stats
        progress_pct = float((tasks_succeeded + tasks_abstained_count) / tasks_total) * 100.0 if tasks_total > 0 else 100.0
        stats: Dict[str, Any] = {
            "llm_calls": llm_calls,
            "llm_failures": llm_failures,
            "llm_abstains": llm_abstains,
            "schema_failures": schema_failures,
            "llm_domain_calls": llm_domain_calls,
            "llm_domain_failures": llm_domain_failures,
            "llm_domain_abstains": llm_domain_abstains,
            "groups_total": groups_total,
            "tasks_total": tasks_total,
            "tasks_attempted": tasks_attempted,
            "tasks_succeeded": tasks_succeeded,
            "tasks_failed": tasks_failed_count,
            "tasks_abstained": tasks_abstained_count,
            "naming_total": naming_total,
            "naming_success": naming_success,
            "naming_failed": naming_failed,
            "naming_abstained": naming_abstained,
            "rules_total": rules_total,
            "rules_success": rules_success,
            "rules_failed": rules_failed,
            "domain_total": domain_total,
            "domain_success": domain_success,
            "domain_failed": domain_failed,
            "domain_abstained": domain_abstained,
            "progress_pct": progress_pct,
            "capabilities_with_cluster": caps_with_cluster,
            "route_coverage_pct": route_coverage_pct,
        }

        return CapabilityOutput(
            project_name=project_name,
            capabilities=capabilities,
            relations=cap_relations,
            stats=stats,
        )
