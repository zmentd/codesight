from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

from domain.jsp_details import JspDetails
from domain.step02_output import Step02AstExtractorOutput
from steps.step02.source_inventory_query import SourceInventoryQuery
from steps.step04.evidence import EvidenceUtils
from steps.step04.models import Entity as Step04Entity
from steps.step04.models import Evidence
from steps.step04.models import Relation as Step04Relation
from steps.step04.security import SecurityBuilder

logger = logging.getLogger(__name__)


class Linker:
    """Link Route entities to JSP entities using Step02 inventory via SourceInventoryQuery."""

    def __init__(self) -> None:
        self.evidence = EvidenceUtils()

    def _build_jsp_entity(self, file_path: str, details: Optional[JspDetails]) -> Step04Entity:
        # Normalize path for consistent evidence and attribute formatting
        norm_path = self.evidence.normalize_path(file_path) if file_path else None
        stem = os.path.splitext(os.path.basename(file_path or ""))[0]
        return Step04Entity(
            id=f"jsp_{stem}",
            type="JSP",
            name=stem,
            attributes={
                "file_path": norm_path,
                "page_type": getattr(details, "page_type", None) if details else None,
            },
            source_refs=[{"file": norm_path}],
        )

    def _find_jsp_by_path(self, step02: Step02AstExtractorOutput, jsp_path: str) -> Optional[Step04Entity]:
        if not jsp_path:
            return None
        logger.debug("Attempting to resolve JSP path: %s", jsp_path)
        # Build a set of candidate suffixes to try (robust to many forward shapes)
        raw = jsp_path.strip().replace('\\', '/')
        # strip leading slash variant used in many forwards
        raw_no_lead = raw.lstrip('/') if raw.startswith('/') else raw
        # ensure .jsp extension
        if not raw_no_lead.lower().endswith('.jsp'):
            raw_no_lead = f"{raw_no_lead}.jsp"

        candidates: List[str] = []
        candidates.append(raw_no_lead)
        # basename-only
        candidates.append(os.path.basename(raw_no_lead))

        # normalized form using EvidenceUtils (strip leading slash for query)
        try:
            norm = self.evidence.normalize_path(raw_no_lead) or ""
            norm_no_lead = norm.lstrip('/') if norm.startswith('/') else norm
            if norm_no_lead:
                if not norm_no_lead.lower().endswith('.jsp'):
                    norm_no_lead = f"{norm_no_lead}.jsp"
                candidates.append(norm_no_lead)
                candidates.append(os.path.basename(norm_no_lead))
        except Exception:
            # Be robust if normalization fails
            pass

        # Deduplicate while preserving order
        seen = set()
        cand_ordered: List[str] = []
        for c in candidates:
            if not c:
                continue
            if c in seen:
                continue
            seen.add(c)
            cand_ordered.append(c)

        # Try each candidate as a suffix match
        for cand in cand_ordered:
            q = SourceInventoryQuery(step02.source_inventory).files().detail_type("jsp").path_endswith(cand)
            try:
                res = q.execute()
            except Exception:
                continue
            if res.total_count > 0:
                f = res.items[0]
                details = f.details if isinstance(f.details, JspDetails) else None
                logger.debug("Found JSP by suffix match: %s -> %s", jsp_path, f.path)
                return self._build_jsp_entity(f.path, details)

        # Fallbacks: try a few common prefix variants and finally a substring scan over JSP inventory
        fallback_prefixes = ("jsp/", "web/", "WEB-INF/jsp/")
        for cand in cand_ordered:
            for pfx in fallback_prefixes:
                try:
                    cand_prefixed = pfx + cand.lstrip('/')
                    q = SourceInventoryQuery(step02.source_inventory).files().detail_type("jsp").path_endswith(cand_prefixed)
                    res = q.execute()
                    if res.total_count > 0:
                        f = res.items[0]
                        details = f.details if isinstance(f.details, JspDetails) else None
                        logger.debug("Found JSP by prefixed suffix match: %s -> %s", jsp_path, f.path)
                        return self._build_jsp_entity(f.path, details)
                except Exception:
                    continue

        # As a last resort, scan all JSPs and look for a candidate substring (case-insensitive)
        try:
            files = SourceInventoryQuery(step02.source_inventory).files().detail_type("jsp").execute().items
        except Exception:
            logger.debug("JSP inventory scan failed for path (could not list JSPs): %s", jsp_path)
            return None

        # First pass: substring (existing behavior)
        low_candidates = [c.lower() for c in cand_ordered]
        for f in files:
            try:
                fpath = (f.path or "")
                fpath_low = fpath.lower()
                for lc in low_candidates:
                    if lc and lc in fpath_low:
                        details = f.details if isinstance(f.details, JspDetails) else None
                        logger.debug("Found JSP by substring match: %s -> %s (matched '%s')", jsp_path, fpath, lc)
                        return self._build_jsp_entity(fpath, details)
            except Exception:
                continue

        # Additional conservative heuristics to help diagnose misses
        # - try exact equality (normalized)
        # - try startswith on path
        # - try variants removing common suffixes like 'Page'
        try:
            # build normalized candidate forms
            norm_candidates = set()
            for c in cand_ordered:
                if not c:
                    continue
                nc = c.lower().lstrip('/')
                norm_candidates.add(nc)
                # variant without 'page' suffix
                if nc.endswith('page.jsp'):
                    norm_candidates.add(nc.replace('page.jsp', '.jsp'))
                # variants with dashed/underscores removed
                norm_candidates.add(nc.replace('-', '').replace('_', ''))

            for f in files:
                try:
                    fpath = (f.path or "")
                    fpath_low = fpath.lower().lstrip('/')
                    # equality
                    if fpath_low in norm_candidates:
                        details = f.details if isinstance(f.details, JspDetails) else None
                        logger.debug("Found JSP by exact-normalized match: %s -> %s", jsp_path, fpath)
                        return self._build_jsp_entity(fpath, details)
                    # startswith
                    for nc in norm_candidates:
                        if nc and fpath_low.startswith(nc):
                            details = f.details if isinstance(f.details, JspDetails) else None
                            logger.debug("Found JSP by startswith match: %s -> %s (matched '%s')", jsp_path, fpath, nc)
                            return self._build_jsp_entity(fpath, details)
                except Exception:
                    continue
        except Exception:
            # never fail the entire match procedure because of our heuristics
            logger.debug("Additional heuristics failed for JSP path: %s", jsp_path)

        # If we reach here, we could not match. Emit diagnostic details to help troubleshooting.
        try:
            sample = [getattr(f, 'path', None) for f in files[:10]]
        except Exception:
            sample = None
        logger.debug("Could not resolve JSP path '%s'. Tried candidates: %s. JSP sample: %s", jsp_path, cand_ordered, sample)
        return None

    def link_routes_to_jsps(self, routes: Dict[str, Step04Entity], step02: Step02AstExtractorOutput) -> Tuple[Dict[str, Step04Entity], List[Step04Relation]]:
        jsp_entities: Dict[str, Step04Entity] = {}
        relations: List[Step04Relation] = []
        for r in routes.values():
            jsp_path = r.attributes.get("result_jsp") if r.attributes else None
            if not jsp_path:
                continue
            jsp_entity = self._find_jsp_by_path(step02, jsp_path)
            if jsp_entity:
                jsp_entities[jsp_entity.id] = jsp_entity
                rel_id = f"rel_{r.id}->renders:{jsp_entity.id}"
                if any(rel.id == rel_id for rel in relations):
                    continue
                evid = []
                if r.source_refs:
                    evid = [self.evidence.build_evidence_from_source_ref(r.source_refs[0])]
                relations.append(
                    Step04Relation(
                        id=rel_id,
                        from_id=r.id,
                        to_id=jsp_entity.id,
                        type="renders",
                        confidence=0.9,
                        evidence=evid,
                        rationale="struts result mapping to JSP",
                    )
                )
        return jsp_entities, relations

    # New: link JSP -> JSP relations using Step02 code mappings (includes, iframe, redirect)
    def link_jsps_to_jsps(self, step02: Step02AstExtractorOutput) -> Tuple[Dict[str, Step04Entity], List[Step04Relation]]:
        jsp_entities: Dict[str, Step04Entity] = {}
        relations: List[Step04Relation] = []
        rel_ids: set = set()

        files = SourceInventoryQuery(step02.source_inventory).files().detail_type("jsp").execute().items
        for f in files:
            details = f.details
            if not isinstance(details, JspDetails):
                continue

            # Ensure source JSP entity exists
            from_entity = self._build_jsp_entity(f.path, details)
            jsp_entities[from_entity.id] = from_entity

            code_mappings = getattr(details, "code_mappings", []) or []
            # Process code_mappings if present; do not skip handling includes below when empty.
            # (Previously an early continue prevented includes recorded in JspDetails from being linked.)
            for cm in code_mappings:
                try:
                    mtype = getattr(cm, "mapping_type", None) or cm.__dict__.get("mapping_type")
                    if mtype not in ("jsp_include", "iframe", "redirect"):
                        continue
                    # Resolve target JSP entity
                    to_ref = getattr(cm, "to_reference", None) or cm.__dict__.get("to_reference") or ""
                    target = self._find_jsp_by_path(step02, to_ref)
                    if not target:
                        # If we cannot resolve, skip (only linking JSP pages)
                        continue
                    jsp_entities[target.id] = target

                    # Map mapping type -> relation type
                    rel_type = (
                        "includesView" if mtype == "jsp_include" else
                        "embedsView" if mtype == "iframe" else
                        "redirectsTo"
                    )
                    rel_id = f"rel_{from_entity.id}->{rel_type}:{target.id}"
                    if rel_id in rel_ids:
                        continue
                    rel_ids.add(rel_id)

                    confidence = 0.85 if mtype in ("jsp_include", "iframe") else 0.8
                    rationale = f"Step02 JSP code_mappings {mtype}"
                    evid = [self.evidence.build_evidence_from_source_ref({"file": f.path})]
                    relations.append(
                        Step04Relation(
                            id=rel_id,
                            from_id=from_entity.id,
                            to_id=target.id,
                            type=rel_type,
                            confidence=confidence,
                            evidence=evid,
                            rationale=rationale,
                        )
                    )
                except (AttributeError, KeyError, TypeError, ValueError):
                    # Be robust to unexpected mapping shapes
                    continue

            # Also handle explicit includes recorded in JspDetails (Step02 may record includes)
            includes = getattr(details, 'includes', []) or []
            for inc in includes:
                try:
                    target = self._find_jsp_by_path(step02, inc)
                    if not target:
                        continue
                    jsp_entities[target.id] = target
                    rel_type = 'includesView'
                    rel_id = f"rel_{from_entity.id}->{rel_type}:{target.id}"
                    if rel_id in rel_ids:
                        continue
                    rel_ids.add(rel_id)
                    evid = [self.evidence.build_evidence_from_source_ref({"file": f.path})]
                    relations.append(
                        Step04Relation(
                            id=rel_id,
                            from_id=from_entity.id,
                            to_id=target.id,
                            type=rel_type,
                            confidence=0.9,
                            evidence=evid,
                            rationale="Step02 JSP includes",
                        )
                    )
                except (AttributeError, TypeError, ValueError):
                    continue

        return jsp_entities, relations

    def link_jsps_to_routes(self, step02: Step02AstExtractorOutput, routes: Dict[str, Step04Entity]) -> Tuple[Dict[str, Step04Entity], List[Step04Relation]]:
        """Resolve JSP 'action_call' CodeMappings to existing Route entities.

        Conservative matching:
        - normalize target by stripping leading '/' and common suffixes (.action, .do)
        - case-insensitive comparison to Route.attributes['action'] (already normalized by RouteBuilder)
        """
        jsp_entities: Dict[str, Step04Entity] = {}
        relations: List[Step04Relation] = {}

        try:
            files = SourceInventoryQuery(step02.source_inventory).files().detail_type("jsp").execute().items
        except Exception:
            return jsp_entities, relations

        unmatched: List[Dict[str, object]] = []

        for f in files:
            details = f.details
            if not isinstance(details, JspDetails):
                continue

            from_entity = self._build_jsp_entity(f.path, details)
            jsp_entities[from_entity.id] = from_entity

            code_mappings = getattr(details, "code_mappings", []) or []
            for cm in code_mappings:
                try:
                    mtype = getattr(cm, "mapping_type", None) or cm.__dict__.get("mapping_type")
                    if mtype != "action_call":
                        continue
                    to_ref = getattr(cm, "to_reference", None) or cm.__dict__.get("to_reference") or ""
                    if not to_ref:
                        continue
                    tok = to_ref.strip()
                    if tok.startswith('/'):
                        tok = tok.lstrip('/')
                    # strip common action/file suffixes
                    for suf in ('.action', '.do', '.html', '.htm'):
                        if tok.lower().endswith(suf):
                            tok = tok[: -len(suf)]
                    tok_cmp = tok.lower()
                    if not tok_cmp:
                        continue

                    # Try to find a matching route by comparing normalized action attribute
                    matched_route: Optional[Step04Entity] = None
                    # basename of token (last path segment)
                    tok_base = tok_cmp.split('/')[-1]
                    for r in routes.values():
                        try:
                            action_attr = (r.attributes or {}).get('action') or ''
                            act_norm = (action_attr or '').strip().lstrip('/').lower()
                            # Conservative match conditions:
                            # 1) exact normalized equality
                            # 2) basename equality (handles context prefix like 'Storm2/..')
                            # 3) tok endswith action (handles suffixing)
                            # 4) action appears inside token (best-effort, lower priority)
                            if act_norm == tok_cmp or act_norm == tok_base or tok_cmp.endswith('/' + act_norm) or tok_cmp.endswith(act_norm) or (act_norm and act_norm in tok_cmp):
                                matched_route = r
                                break
                        except Exception:
                            continue

                    if not matched_route:
                        # Collect diagnostics for unmatched token
                        try:
                            candidates: List[Dict[str, str]] = []
                            seen_actions = set()
                            for r2 in routes.values():
                                try:
                                    a = (r2.attributes or {}).get('action') or ''
                                    a_norm = (a or '').strip()
                                    if not a_norm:
                                        continue
                                    if a_norm in seen_actions:
                                        continue
                                    seen_actions.add(a_norm)
                                    candidates.append({"route_id": r2.id, "action": a_norm})
                                    if len(candidates) >= 12:
                                        break
                                except Exception:
                                    continue
                        except Exception:
                            candidates = []
                        token_entry = {"token": tok, "source": getattr(f, 'path', None), "candidates": candidates}
                        unmatched.append(token_entry)
                        # No authoritative match; skip creating a relation
                        continue

                    rel_id = f"rel_{from_entity.id}->invokesRoute:{matched_route.id}"
                    if any(rr.id == rel_id for rr in relations):
                        continue

                    # Attempt to resolve placeholder methods like '{1}' using preserved raw action pattern
                    try:
                        route_attrs = matched_route.attributes or {}
                        # prefer method_raw (from Step02) for substitution; fallback to method
                        method_template = route_attrs.get('method_raw') or route_attrs.get('method')
                        raw_action = route_attrs.get('action_raw') or ''
                        if method_template and isinstance(method_template, str) and ('{' in method_template and '}' in method_template) and raw_action:
                            # Normalize raw_action (strip leading slash) so '/Foo' matches token 'Foo'
                            raw_action_norm = str(raw_action).strip().lstrip('/')
                            if not raw_action_norm:
                                raise ValueError('empty normalized action')
                            # Build a conservative regex from normalized raw_action: replace '*' with ([^/]+), escape other chars
                            patt = re.escape(raw_action_norm)
                            # Replace escaped wildcard patterns (\*) back to regex capture
                            patt = patt.replace(re.escape('*'), '([^/]+)')
                            # Allow optional leading slash in the token when matching; anchor pattern
                            if not patt.startswith('^'):
                                patt = '^' + patt
                            # Permit an optional leading slash in the token (tok is typically without leading slash)
                            patt = '^/?' + patt.lstrip('^')
                            if not patt.endswith('$'):
                                patt = patt + '$'

                            try:
                                cre = re.compile(patt)
                                m = cre.match(tok)
                                if m:
                                    # Substitute {1},{2}... in method_template
                                    resolved = method_template
                                    for i, g in enumerate(m.groups(), start=1):
                                        resolved = resolved.replace(f"{{{i}}}", g or '')
                                    # If braces remain unresolved, skip
                                    if '{' not in resolved and '}' not in resolved and resolved:
                                        # Store resolved method in route attributes for downstream consumers
                                        matched_route.attributes['method_resolved'] = resolved
                                        # Also update the canonical 'method' attribute so downstream exports reflect the resolution
                                        try:
                                            matched_route.attributes['method'] = resolved
                                        except Exception:
                                            # be robust if attributes structure is unexpected
                                            matched_route.attributes.update({'method': resolved})
                            except re.error:
                                pass
                    except Exception:
                        pass

                    # Prefer span evidence from the CodeMapping attributes when present
                    evid = []
                    try:
                        # mapping attributes may include 'line'/'end_line' recorded by Step02
                        line = None
                        end_line = None
                        try:
                            attrs = getattr(cm, 'attributes', {}) or cm.__dict__.get('attributes', {}) or {}
                            line = attrs.get('line')
                            end_line = attrs.get('end_line')
                        except Exception:
                            line = None
                            end_line = None

                        if line is not None:
                            evid = [self.evidence.build_evidence_from_file(f.path, line, end_line)]
                        else:
                            evid = [self.evidence.build_evidence_from_source_ref({"file": f.path})]
                    except Exception:
                        evid = [self.evidence.build_evidence_from_source_ref({"file": f.path})]

                    relations.append(
                        Step04Relation(
                            id=rel_id,
                            from_id=from_entity.id,
                            to_id=matched_route.id,
                            type="invokesRoute",
                            confidence=0.85,
                            evidence=evid,
                            rationale="Step02 JSP action_call mapping to Route",
                        )
                    )

                    # Propagate JSP-detected roles to the matched Route (conservative)
                    try:
                        sb = SecurityBuilder()
                        jsp_roles = sb._collect_jsp_roles(details) if details else set()
                    except Exception:
                        jsp_roles = set()

                    for role in sorted(jsp_roles):
                        try:
                            sec_rel_id = f"rel_{matched_route.id}->securedBy:{role}"
                            if any(rr.id == sec_rel_id for rr in relations):
                                continue
                            sec_evid = evid or [self.evidence.build_evidence_from_source_ref({"file": f.path})]
                            relations.append(
                                Step04Relation(
                                    id=sec_rel_id,
                                    from_id=matched_route.id,
                                    to_id=f"role_{role}",
                                    type="securedBy",
                                    confidence=0.75,
                                    evidence=sec_evid,
                                    rationale="Propagated from JSP securedBy via invokesRoute",
                                )
                            )
                        except Exception:
                            continue




