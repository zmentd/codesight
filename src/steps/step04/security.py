from __future__ import annotations

import os
import re
from typing import Dict, List, Set, Tuple

from domain.java_details import JavaClass, JavaDetails
from domain.jsp_details import JspDetails
from domain.step02_output import Step02AstExtractorOutput
from steps.step02.source_inventory_query import SourceInventoryQuery
from steps.step04.evidence import EvidenceUtils
from steps.step04.models import Entity, Relation


class SecurityBuilder:
    """Build security relations from @RolesAllowed and JSP security signals."""

    def __init__(self) -> None:
        self.evidence = EvidenceUtils()

    def build_roles_allowed(self, java: JavaDetails) -> List[Relation]:
        relations: List[Relation] = []
        for cls in java.classes:
            class_roles = self._extract_roles(cls.annotations)
            if class_roles:
                cls_id = f"class_{cls.package_name}.{cls.class_name}"
                for role in class_roles:
                    relations.append(
                        Relation(
                            id=f"rel_{cls_id}->securedBy:{role}",
                            from_id=cls_id,
                            to_id=f"role_{role}",
                            type="securedBy",
                            confidence=0.9,
                            rationale="@RolesAllowed on class",
                        )
                    )
            for m in cls.methods:
                method_roles = self._extract_roles(m.annotations)
                if method_roles:
                    method_id = f"method_{cls.package_name}.{cls.class_name}#{m.name}"
                    for role in method_roles:
                        relations.append(
                            Relation(
                                id=f"rel_{method_id}->securedBy:{role}",
                                from_id=method_id,
                                to_id=f"role_{role}",
                                type="securedBy",
                                confidence=0.95,
                                rationale="@RolesAllowed on method",
                            )
                        )
        return relations

    def build_jsp_security(self, step02: Step02AstExtractorOutput) -> Tuple[Dict[str, Entity], List[Relation]]:
        """Scan JSP details in Step02 for security tags/expressions and emit securedBy relations.
        - Detect roles from tags with prefixes sec: or security:, attributes role/roles/access, and from EL/scriptlets using isUserInRole()/hasRole().
        - Also consume conservative Step02 CodeMapping entries mapping_type == 'jsp_security' produced by JSPParser.
        - Attach file:line evidence when Step02 recorded spans on tags/EL/scriptlets or CodeMapping attributes.
        - Returns minimal JSP entities (if not already present) and relations.
        """
        jsp_entities: Dict[str, Entity] = {}
        relations: List[Relation] = []
        rel_ids: Set[str] = set()

        # Query JSP files from Step02
        files = SourceInventoryQuery(step02.source_inventory).files().detail_type("jsp").execute().items
        for f in files:
            details = f.details
            if not isinstance(details, JspDetails):
                continue

            # Collect roles using existing heuristics
            roles = self._collect_jsp_roles(details)

            # Also inspect conservative CodeMappings recorded by Step02 (mapping_type 'jsp_security')
            try:
                for cm in getattr(details, 'code_mappings', []) or []:
                    try:
                        mtype = getattr(cm, 'mapping_type', None) or cm.__dict__.get('mapping_type')
                        if mtype != 'jsp_security':
                            continue
                        attrs = getattr(cm, 'attributes', {}) or cm.__dict__.get('attributes', {}) or {}
                        token_type = attrs.get('token_type')
                        # tokens may be list or single
                        toks = attrs.get('tokens') or attrs.get('token') or []
                        if isinstance(toks, (str, int)):
                            toks = [str(toks)]
                        if token_type == 'role':
                            for tk in toks:
                                if isinstance(tk, str) and tk:
                                    roles.add(tk)
                        elif token_type == 'group_level':
                            # Conservative mapping: create a synthetic role name for group level checks
                            # Example key: role_group_>_2 or role_group_2
                            # Prefer numeric 'value' in attributes if present
                            try:
                                val = attrs.get('value') if isinstance(attrs.get('value'), int) else attrs.get('tokens') or None
                                # normalize to string
                                if isinstance(val, (list, set)) and val:
                                    val = next(iter(val))
                                if val is None:
                                    # fallback to tokens
                                    val = toks[0] if toks else None
                                if val is not None:
                                    role_name = f"group_{str(val)}"
                                    roles.add(role_name)
                            except Exception:
                                continue
                        elif token_type == 'helper_call':
                            # Map helper calls conservatively to a helper-based role id
                            try:
                                helper = (attrs.get('helper') or '').strip()
                                if helper:
                                    # include args if present (not needed directly); synthesize role name from helper
                                    safe = helper.replace('.', '_')
                                    role_name = f"helper_{safe}"
                                    roles.add(role_name)
                            except Exception:
                                continue
                    except Exception:
                        continue
            except Exception:
                # best-effort; ignore mapping consumption failures
                pass

            if not roles:
                continue

            # Ensure a JSP entity for this file
            stem = os.path.splitext(os.path.basename(f.path))[0]
            jsp_id = f"jsp_{stem}"
            if jsp_id not in jsp_entities:
                jsp_entities[jsp_id] = Entity(
                    id=jsp_id,
                    type="JSP",
                    name=stem,
                    attributes={"file_path": self.evidence.normalize_path(f.path)},
                    source_refs=[{"file": f.path}],
                )

            # For each detected role emit securedBy and include best-effort line evidence
            for role in sorted(roles):
                rel_id = f"rel_{jsp_id}->securedBy:{role}"
                if rel_id in rel_ids:
                    continue
                rel_ids.add(rel_id)

                # Collect evidence: prefer span-level evidence from JSP parsed elements (tags, EL, scriptlets) when available
                evs: List = []

                try:
                    # 1) Check parsed JSP tags for a match and use their line/end_line when present
                    for t in getattr(details, 'jsp_tags', []) or []:
                        try:
                            # Role may appear in attribute values (access/role/roles) or in full_text
                            attrs = getattr(t, 'attributes', {}) or {}
                            found = False
                            # check role/roles/access explicitly
                            for key in ('role', 'roles', 'access'):
                                v = attrs.get(key)
                                if isinstance(v, str):
                                    # prefer parsing via extractor for access-like expressions
                                    try:
                                        parsed = SecurityBuilder._extract_roles_from_expression(v)
                                    except Exception:
                                        parsed = set()
                                    # look for quoted role tokens or parsed roles or simple substring match
                                    if role in parsed or f"'{role}'" in v or f'"{role}"' in v or role in v:
                                        found = True
                                        break
                            # fallback: check full_text for role appearance or helper patterns
                            if not found:
                                fx = getattr(t, 'full_text', '') or ''
                                if fx and (f"'{role}'" in fx or f'"{role}"' in fx or role in fx or ("hasRole" in fx and role in fx) or ("hasAnyRole" in fx and role in fx)):
                                    found = True
                            if found:
                                line = getattr(t, 'line', None)
                                end_line = getattr(t, 'end_line', None)
                                evs.append(self.evidence.build_evidence_from_file(f.path, line, end_line))
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

                # 2) Check EL expressions
                if not evs:
                    try:
                        for el in getattr(details, 'el_expressions', []) or []:
                            try:
                                expr = getattr(el, 'expression', '') or ''
                                fx = getattr(el, 'full_text', '') or ''
                                if expr and (f"'{role}'" in expr or f'"{role}"' in expr or role in expr or ("hasRole" in expr and role in expr) or ("isUserInRole" in expr and role in expr)):
                                    line = getattr(el, 'line', None)
                                    end_line = getattr(el, 'end_line', None)
                                    evs.append(self.evidence.build_evidence_from_file(f.path, line, end_line))
                                    break
                                # also check full_text if available
                                if fx and (f"'{role}'" in fx or f'"{role}"' in fx or role in fx or ("hasRole" in fx and role in fx)):
                                    line = getattr(el, 'line', None)
                                    end_line = getattr(el, 'end_line', None)
                                    evs.append(self.evidence.build_evidence_from_file(f.path, line, end_line))
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                # 3) Check embedded Java/scriptlet blocks
                if not evs:
                    try:
                        for blk in getattr(details, 'embedded_java', []) or []:
                            try:
                                code = getattr(blk, 'code', '') or ''
                                fx = getattr(blk, 'full_text', '') or ''
                                if code and (("isUserInRole" in code and role in code) or f"'{role}'" in code or f'"{role}"' in code or role in code):
                                    line = getattr(blk, 'line', None)
                                    end_line = getattr(blk, 'end_line', None)
                                    evs.append(self.evidence.build_evidence_from_file(f.path, line, end_line))
                                    break
                                if fx and (("isUserInRole" in fx and role in fx) or f"'{role}'" in fx or f'"{role}"' in fx or role in fx):
                                    line = getattr(blk, 'line', None)
                                    end_line = getattr(blk, 'end_line', None)
                                    evs.append(self.evidence.build_evidence_from_file(f.path, line, end_line))
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                # 4) If still no parsed-element span evidence, fall back to scanning CodeMappings for span info (existing behavior)
                if not evs:
                    try:
                        # Scan CodeMappings for a matching role token to get span info
                        for cm in getattr(details, 'code_mappings', []) or []:
                            try:
                                mtype = getattr(cm, 'mapping_type', None) or cm.__dict__.get('mapping_type')
                                if mtype != 'jsp_security':
                                    continue
                                attrs = getattr(cm, 'attributes', {}) or cm.__dict__.get('attributes', {}) or {}
                                token_type = attrs.get('token_type')
                                toks = attrs.get('tokens') or []
                                if isinstance(toks, (str, int)):
                                    toks = [str(toks)]
                                # match role tokens
                                if token_type == 'role' and any(str(role) == str(tk) or str(role) in str(tk) for tk in toks):
                                    line = attrs.get('line')
                                    end_line = attrs.get('end_line')
                                    evs.append(self.evidence.build_evidence_from_file(f.path, line, end_line))
                                    break
                                # group_level and helper_call: match by synthesized role name
                                if token_type in ('group_level', 'helper_call'):
                                    # attempt to synthesize same role_name mapping as above
                                    if token_type == 'group_level':
                                        val = attrs.get('value') if isinstance(attrs.get('value'), int) else (attrs.get('tokens') or None)
                                        candidate = None
                                        try:
                                            if isinstance(val, (list, set)) and val:
                                                candidate = f"group_{next(iter(val))}"
                                            elif val is not None:
                                                candidate = f"group_{str(val)}"
                                        except Exception:
                                            candidate = None
                                        if candidate and candidate == role:
                                            line = attrs.get('line')
                                            end_line = attrs.get('end_line')
                                            evs.append(self.evidence.build_evidence_from_file(f.path, line, end_line))
                                            break
                                    else:
                                        helper = (attrs.get('helper') or '').strip()
                                        if helper:
                                            candidate = f"helper_{helper.replace('.', '_')}"
                                            if candidate == role:
                                                line = attrs.get('line')
                                                end_line = attrs.get('end_line')
                                                evs.append(self.evidence.build_evidence_from_file(f.path, line, end_line))
                                                break
                            except Exception:
                                continue
                    except Exception:
                        pass

                # If we found no span-level evidence, fall back to file-level source_ref evidence
                if not evs:
                    evs = [self.evidence.build_evidence_from_source_ref({"file": f.path})]

                relations.append(
                    Relation(
                        id=rel_id,
                        from_id=jsp_id,
                        to_id=f"role_{role}",
                        type="securedBy",
                        confidence=0.75,
                        evidence=evs,
                        rationale="JSP security tag/EL or Step02 jsp_security mapping",
                    )
                )
        return jsp_entities, relations

    @staticmethod
    def _extract_roles(annotations: List) -> List[str]:
        roles: List[str] = []
        for ann in annotations:
            if getattr(ann, 'name', '') in ("RolesAllowed", "javax.annotation.security.RolesAllowed"):
                attrs = getattr(ann, 'attributes', {}) or {}
                val = attrs.get("value")
                if isinstance(val, list):
                    roles.extend([str(v) for v in val])
                elif isinstance(val, str):
                    roles.append(val)
        return roles

    def _collect_jsp_roles(self, details: JspDetails) -> Set[str]:
        """Collect roles from JSP details, including tag attributes, EL, scriptlets, and configured patterns.
        Instance method so we can consult config via self.evidence.cfg if present.
        """
        roles: Set[str] = set()
        # From namespaced security tags
        try:
            for t in getattr(details, 'jsp_tags', []) or []:
                tag = (getattr(t, 'tag_name', '') or '').lower()
                if ':' in tag and tag.split(':', 1)[0] in {"sec", "security"}:
                    attrs = getattr(t, 'attributes', {}) or {}
                    # role/roles direct attributes
                    for key in ("role", "roles"):
                        val = attrs.get(key)
                        if isinstance(val, str):
                            roles.update(SecurityBuilder._split_roles(val))
                    # access attribute may contain hasRole()/hasAnyRole()
                    access = attrs.get('access')
                    if isinstance(access, str):
                        roles.update(SecurityBuilder._extract_roles_from_expression(access))
                    # Fallback: scan full_text for role expressions
                    fx = getattr(t, 'full_text', '') or ''
                    if fx:
                        roles.update(SecurityBuilder._extract_roles_from_expression(fx))
        except (AttributeError, TypeError, ValueError, re.error):
            pass
        # From EL expressions
        try:
            for el in getattr(details, 'el_expressions', []) or []:
                expr = getattr(el, 'expression', '') or ''
                if expr:
                    roles.update(SecurityBuilder._extract_roles_from_expression(expr))
        except (AttributeError, TypeError, ValueError, re.error):
            pass
        # From embedded Java/scriptlets
        try:
            for blk in getattr(details, 'embedded_java', []) or []:
                code = getattr(blk, 'code', '') or ''
                if code:
                    roles.update(SecurityBuilder._extract_roles_from_expression(code))
        except (AttributeError, TypeError, ValueError, re.error):
            pass

        # From configured extra patterns (optional)
        try:
            cfg = getattr(self.evidence, 'cfg', None)
            if cfg is not None:
                patterns: List[str] = []
                try:
                    patterns = getattr(cfg.steps.step04.security, 'patterns', []) or []
                except (AttributeError, TypeError):
                    patterns = []
                for pat in patterns:
                    try:
                        cre = re.compile(pat, re.IGNORECASE)
                        # scan tag full_text, el expressions, embedded java
                        for t in getattr(details, 'jsp_tags', []) or []:
                            fx = getattr(t, 'full_text', '') or ''
                            for m in cre.finditer(fx):
                                # capture group 1 preferred, else whole match
                                cap = m.group(1) if m.groups() else m.group(0)
                                roles.update(SecurityBuilder._split_roles(cap))
                        for el in getattr(details, 'el_expressions', []) or []:
                            fx = getattr(el, 'full_text', '') or ''
                            for m in cre.finditer(fx):
                                cap = m.group(1) if m.groups() else m.group(0)
                                roles.update(SecurityBuilder._split_roles(cap))
                        for blk in getattr(details, 'embedded_java', []) or []:
                            fx = getattr(blk, 'full_text', '') or ''
                            for m in cre.finditer(fx):
                                cap = m.group(1) if m.groups() else m.group(0)
                                roles.update(SecurityBuilder._split_roles(cap))
                    except re.error:
                        continue
        except (AttributeError, TypeError, ValueError):
            pass

        return {r for r in roles if r}

    @staticmethod
    def _split_roles(val: str) -> Set[str]:
        parts = [p.strip() for p in re.split(r"[,;]", val or "")]
        return {p.strip("'\"") for p in parts if p}

    @staticmethod
    def _extract_roles_from_expression(text: str) -> Set[str]:
        roles: Set[str] = set()
        if not isinstance(text, str) or not text:
            return roles
        # hasRole('ROLE_X')
        for m in re.finditer(r"hasRole\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", text, re.IGNORECASE):
            roles.add(m.group(1))
        # hasAnyRole('A','B')
        for m in re.finditer(r"hasAnyRole\s*\(\s*([^\)]*)\)", text, re.IGNORECASE):
            inside = m.group(1) or ''
            roles.update(SecurityBuilder._split_roles(inside))
        # isUserInRole('X')
        for m in re.finditer(r"isUserInRole\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", text, re.IGNORECASE):
            roles.add(m.group(1))
        # access="ROLE_A,ROLE_B" direct values (if no hasRole wrapper)
        for m in re.finditer(r"\baccess\s*=\s*['\"]([^'\"]+)['\"]", text, re.IGNORECASE):
            roles.update(SecurityBuilder._split_roles(m.group(1)))
        return roles
