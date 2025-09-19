from __future__ import annotations

import re
from typing import Dict, List, Tuple

from domain.config_details import ConfigurationDetails, ValidationRule
from domain.step02_output import Step02AstExtractorOutput
from steps.step02.source_inventory_query import SourceInventoryQuery
from steps.step04.evidence import EvidenceUtils
from steps.step04.models import Entity, Relation


class BusinessRulesBuilder:
    """Build Rule entities from Step02 validation rules and link them to Routes.

    Strategy:
    - Read ConfigurationDetails.validation_rules from Step02 (validation.xml / validator annotations).
    - Create Rule entities with stable IDs and attributes (form, field, type, variables, framework).
    - Link Routes (built earlier) to Rule via relation type 'validatedBy'.
      Primary join: routes whose source_refs originate from the SAME configuration file.
      Fallback join (new): when rules come from validation.xml (separate file), join routes by directory,
      i.e., any routes whose source config (e.g., struts-config.xml) is in the same folder. This mirrors
      typical Struts layouts where validation.xml sits next to struts-config.xml.
    - Attach file evidence from the configuration file.
    """

    def __init__(self) -> None:
        self.evidence = EvidenceUtils()

    @staticmethod
    def _slug(text: str) -> str:
        if not text:
            return ""
        s = str(text).strip()
        return re.sub(r"[^A-Za-z0-9_:\-\.]+", "_", s)

    def build_rules(self, step02: Step02AstExtractorOutput, routes_by_id: Dict[str, Entity]) -> Tuple[Dict[str, Entity], List[Relation]]:
        rule_entities: Dict[str, Entity] = {}
        relations: List[Relation] = []

        files = SourceInventoryQuery(step02.source_inventory).files().detail_type("configuration").execute().items
        # Build quick index: routes by config file path and by directory (normalized)
        routes_by_file: Dict[str, List[Entity]] = {}
        routes_by_dir: Dict[str, List[Entity]] = {}
        for r in routes_by_id.values():
            for ref in (getattr(r, 'source_refs', []) or []):
                f = (ref or {}).get('file')
                if not f:
                    continue
                norm = self.evidence.normalize_path(f)
                if not isinstance(norm, str) or not norm:
                    continue
                key = norm
                routes_by_file.setdefault(key, []).append(r)
                # Directory key
                try:
                    dir_key = key.rsplit('/', 1)[0] if '/' in key else '/'
                    routes_by_dir.setdefault(dir_key, []).append(r)
                except Exception:  # pylint: disable=broad-except
                    pass

        # New: build global index form_name -> routes using Step02 CodeMappings (action mappings)
        form_to_routes: Dict[str, List[Entity]] = {}
        try:
            cfg_files = files
            for f in cfg_files:
                details = getattr(f, 'details', None)
                if not isinstance(details, ConfigurationDetails):
                    continue
                for cm in getattr(details, 'code_mappings', []) or []:
                    try:
                        if getattr(cm, 'mapping_type', None) != 'action':
                            continue
                        attrs = getattr(cm, 'attributes', {}) or {}
                        form_name = (attrs.get('form_name') or '').strip()
                        if not form_name:
                            continue
                        # find a matching route by same config file (best-effort), fall back by name match on action path
                        cfg_path = self.evidence.normalize_path(getattr(f, 'path', None) or '')
                        cfg_key = cfg_path or ''
                        candidate_routes = list(routes_by_file.get(cfg_key, []))
                        if not candidate_routes:
                            # try to find by action path match
                            act = (getattr(cm, 'from_reference', '') or '').strip().lstrip('/')
                            if act:
                                for r in routes_by_id.values():
                                    a = ((r.attributes or {}).get('action') or '').lstrip('/') if r.attributes else ''
                                    if a.lower() == act.lower():
                                        candidate_routes.append(r)
                        if candidate_routes:
                            form_to_routes.setdefault(form_name, []).extend(candidate_routes)
                    except Exception:  # pylint: disable=broad-except
                        pass
        except Exception:  # pylint: disable=broad-except
            pass

        created_rel_ids: set[str] = set()

        for f in files:
            details = f.details
            if not isinstance(details, ConfigurationDetails):
                continue
            cfg_path = self.evidence.normalize_path(getattr(f, 'path', None) or '')
            if not cfg_path:
                continue
            routes_here = list(routes_by_file.get(cfg_path, []))

            # Fallback: if no direct same-file routes and we do have rules, try directory match
            if not routes_here and getattr(details, 'validation_rules', None):
                try:
                    dir_key = cfg_path.rsplit('/', 1)[0] if '/' in cfg_path else '/'
                except Exception:  # pylint: disable=broad-except
                    dir_key = '/'
                # Only apply fallback for typical Struts validation files
                is_validation_file = cfg_path.lower().endswith('/validation.xml') or 'validation' in cfg_path.lower()
                if is_validation_file:
                    routes_here = list(routes_by_dir.get(dir_key, []))

            if not getattr(details, 'validation_rules', None):
                continue

            for vr in list(details.validation_rules or []):
                # Entity id and name
                rid_slug = self._slug(f"{vr.form_name}:{vr.field_reference}:{vr.validation_type}")
                rule_id = f"rule_{rid_slug}"
                if rule_id not in rule_entities:
                    rule_entities[rule_id] = Entity(
                        id=rule_id,
                        type="Rule",
                        name=f"{vr.form_name}.{vr.field_reference} {vr.validation_type}",
                        attributes={
                            "framework": getattr(vr, 'framework', None),
                            "form": vr.form_name,
                            "field": vr.field_reference,
                            "type": vr.validation_type,
                            "variables": dict(getattr(vr, 'validation_variables', {}) or {}),
                            "source": getattr(vr, 'validation_source', 'xml'),
                        },
                        source_refs=[{"file": cfg_path}],
                    )

                # Preferred: global form-name join
                candidates: List[Entity] = []
                form = (getattr(vr, 'form_name', '') or '').strip()
                if form and form in form_to_routes:
                    candidates = form_to_routes.get(form, []) or []
                # Fallback: same file/dir routes
                if not candidates:
                    candidates = routes_here

                action_method = (getattr(vr, 'action_method', None) or '').strip() or None
                for r_ent in candidates:
                    try:
                        meth = None
                        attrs = getattr(r_ent, 'attributes', {}) or {}
                        if isinstance(attrs, dict):
                            meth = (attrs.get('method') or '').strip() or None
                        if action_method and meth and action_method != meth:
                            continue
                        rel_id = f"rel_{r_ent.id}->validatedBy:{rule_id}"
                        if rel_id in created_rel_ids:
                            continue
                        created_rel_ids.add(rel_id)
                        relations.append(
                            Relation(
                                id=rel_id,
                                from_id=r_ent.id,
                                to_id=rule_id,
                                type="validatedBy",
                                confidence=0.9,
                                evidence=[self.evidence.build_evidence_from_file(cfg_path)],
                                rationale="From validation rules (form-name/global join; fallback: same file/dir)",
                            )
                        )
                    except (AttributeError, TypeError, ValueError):
                        pass

        return rule_entities, relations
