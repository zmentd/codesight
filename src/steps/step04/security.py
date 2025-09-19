from __future__ import annotations

import os
import re
from typing import Dict, List, Set, Tuple

from config.config import Config
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

    # Shared role canonicalizer for consistent IDs/names across sources
    @staticmethod
    def canonicalize_role_name(name: str | None) -> str | None:
        if not name:
            return None
        s = name.strip()
        # Strip leading 'role_' prefix (case-insensitive) while preserving case of the remainder
        if s.lower().startswith("role_"):
            s = s[len("role_"):]
        # Preserve original case for ordinary roles (Admin, Manager, Auditor, HR, etc.)
        # Clean up surrounding punctuation/whitespace only
        cleaned = re.sub(r"[^A-Za-z0-9_:\.-]+", "", s)
        key_lower = cleaned.lower()
        # Known aliases/helpers map to specific casing
        aliases = {
            "getsecurity": "getSecurity",
            "unauthorizeduse": "unauthorizedUse",
            "security": "security",
        }
        return aliases.get(key_lower, cleaned)

    def build_roles_allowed(self, java: JavaDetails) -> List[Relation]:
        relations: List[Relation] = []
        for cls in java.classes:
            class_roles = self._extract_roles(cls.annotations)
            if class_roles:
                cls_id = f"class_{cls.package_name}.{cls.class_name}"
                for role in class_roles:
                    canon = self.canonicalize_role_name(role)
                    if not canon:
                        continue
                    relations.append(
                        Relation(
                            id=f"rel_{cls_id}->securedBy:{canon}",
                            from_id=cls_id,
                            to_id=f"role_{canon}",
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
                        canon = self.canonicalize_role_name(role)
                        if not canon:
                            continue
                        relations.append(
                            Relation(
                                id=f"rel_{method_id}->securedBy:{canon}",
                                from_id=method_id,
                                to_id=f"role_{canon}",
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
                                if isinstance(val, (list, set)) and val:
                                    val = next(iter(val))
                                if val is None:
                                    val = toks[0] if toks else None
                                if val is not None:
                                    role_name = f"group_{str(val)}"
                                    roles.add(role_name)
                            except (AttributeError, TypeError, ValueError, KeyError):
                                continue
                        elif token_type == 'helper_call':
                            try:
                                helper = (attrs.get('helper') or '').strip()
                                if helper:
                                    # include args if present (not needed directly); synthesize role name from helper
                                    safe = helper.replace('.', '_')
                                    role_name = f"helper_{safe}"
                                    roles.add(role_name)
                            except (AttributeError, TypeError, ValueError, KeyError):
                                continue
                    except (AttributeError, TypeError, ValueError, KeyError):
                        continue
            except (AttributeError, TypeError, ValueError):
                # best-effort; ignore mapping consumption failures
                pass

            if not roles:
                continue

            # Canonicalize roles now
            roles = {r for r in (SecurityBuilder.canonicalize_role_name(x) for x in roles) if r}

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
                                    except (re.error, AttributeError, TypeError, ValueError):
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
                        except (AttributeError, TypeError, ValueError, KeyError):
                            continue
                except (AttributeError, TypeError, ValueError):
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
                            except (AttributeError, TypeError, ValueError, KeyError):
                                continue
                    except (AttributeError, TypeError, ValueError):
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
                            except (AttributeError, TypeError, ValueError, KeyError):
                                continue
                    except (AttributeError, TypeError, ValueError):
                        pass

                # 4) Fallback to CodeMappings span info
                if not evs:
                    try:
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
                                if token_type == 'role' and any(str(role) == str(tk) or str(role) in str(tk) for tk in toks):
                                    line = attrs.get('line')
                                    end_line = attrs.get('end_line')
                                    evs.append(self.evidence.build_evidence_from_file(f.path, line, end_line))
                                    break
                                if token_type in ('group_level', 'helper_call'):
                                    if token_type == 'group_level':
                                        val = attrs.get('value') if isinstance(attrs.get('value'), int) else (attrs.get('tokens') or None)
                                        candidate = None
                                        try:
                                            if isinstance(val, (list, set)) and val:
                                                candidate = f"group_{next(iter(val))}"
                                            elif val is not None:
                                                candidate = f"group_{str(val)}"
                                        except (AttributeError, TypeError, ValueError):
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
                            except (AttributeError, TypeError, ValueError, KeyError):
                                continue
                    except (AttributeError, TypeError, ValueError):
                        pass

                if not evs:
                    evs = [self.evidence.build_evidence_from_source_ref({"file": f.path})]

                relations.append(
                    Relation(
                        id=rel_id,
                        from_id=jsp_id,
                        to_id=f"role_{role}",
                        type="securedBy",
                        confidence=0.9,
                        evidence=evs,
                        rationale="JSP security tag/EL or Step02 jsp_security mapping",
                    )
                )
        return jsp_entities, relations

    def build_java_security(self, java: JavaDetails) -> List[Relation]:
        """Consume Step02 Java code_mappings with mapping_type == 'java_security' and emit securedBy relations.
        - Uses CodeMapping.from_reference as the method FQN (pkg.Class.method) to build method_ IDs.
        - Maps token_type 'role' to role_{token}, 'group_level' to role_group_{value}, 'helper_call' to role_helper_{helper}.
        - Adds file:line evidence from CodeMapping.attributes where available.
        """
        relations: List[Relation] = []
        try:
            code_maps = getattr(java, 'code_mappings', []) or []
            for cm in code_maps:
                try:
                    mtype = getattr(cm, 'mapping_type', None) or cm.__dict__.get('mapping_type')
                    if mtype != 'java_security':
                        continue
                    from_ref = getattr(cm, 'from_reference', None) or cm.__dict__.get('from_reference') or ''
                    attrs = getattr(cm, 'attributes', {}) or cm.__dict__.get('attributes', {}) or {}
                    # Build method ID from from_reference like pkg.Class.method
                    cls_part = ''
                    method_name = ''
                    if isinstance(from_ref, str) and '.' in from_ref:
                        parts = from_ref.split('.')
                        method_name = parts[-1]
                        cls_part = '.'.join(parts[:-1])
                    else:
                        method_name = from_ref
                        cls_part = ''
                    if not method_name:
                        continue
                    method_id = f"method_{cls_part}#{method_name}" if cls_part else f"method_{method_name}"
                    # Determine token(s)
                    token_type = attrs.get('token_type')
                    toks = attrs.get('tokens')
                    if isinstance(toks, (str, int)):
                        toks = [str(toks)]
                    elif not isinstance(toks, list):
                        toks = []
                    role_names: List[str] = []
                    if token_type == 'role':
                        role_names = [str(t) for t in toks if str(t)]
                    elif token_type == 'group_level':
                        val = attrs.get('value')
                        if isinstance(val, (int, float, str)):
                            role_names = [f"group_{str(val)}"]
                        elif toks:
                            role_names = [f"group_{str(toks[0])}"]
                    elif token_type == 'helper_call':
                        helper = (attrs.get('helper') or '').strip()
                        if helper:
                            role_names = [f"helper_{helper.replace('.', '_')}"]
                    # Canonicalize role names
                    role_names = [r for r in (SecurityBuilder.canonicalize_role_name(x) for x in role_names) if r]
                    # Evidence and confidence
                    file_path = attrs.get('file_path')
                    line = attrs.get('line')
                    end_line = attrs.get('end_line')
                    emits_xhtml_flag = str(attrs.get('emits_xhtml', '')).lower() in ('true', '1')
                    confidence = 0.92 if emits_xhtml_flag else 0.86
                    for role in role_names:
                        rel_id = f"rel_{method_id}->securedBy:{role}"
                        relations.append(
                            Relation(
                                id=rel_id,
                                from_id=method_id,
                                to_id=f"role_{role}",
                                type='securedBy',
                                confidence=confidence,
                                evidence=[self.evidence.build_evidence_from_file(file_path, line, end_line)] if file_path else [],
                                rationale='Java XHTML/security check'
                            )
                        )
                except (AttributeError, TypeError, ValueError, KeyError):
                    continue
        except (AttributeError, TypeError, ValueError):
            return []
        return relations

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
        """Collect roles from JSP details, including tag attributes, EL, scriptlets, configured patterns, and Step02 pattern hits."""
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
        except (AttributeError, TypeError, ValueError):
            pass
        # From EL expressions
        try:
            for el in getattr(details, 'el_expressions', []) or []:
                expr = getattr(el, 'expression', '') or ''
                if not expr:
                    continue
                roles.update(SecurityBuilder._extract_roles_from_expression(expr))
        except (AttributeError, TypeError, ValueError):
            pass
        # From embedded Java/scriptlets
        try:
            for blk in getattr(details, 'embedded_java', []) or []:
                code = getattr(blk, 'code', '') or ''
                if not code:
                    continue
                # isUserInRole('ROLE') or hasRole('ROLE') or hasAnyRole('A','B')
                roles.update(SecurityBuilder._extract_roles_from_expression(code))
        except (AttributeError, TypeError, ValueError):
            pass
        # From configured patterns in global config (capture groups preferred)
        try:
            cfg = Config.get_instance()
            patterns = getattr(cfg.steps.step04.security, 'patterns', []) or []
            for pat in patterns:
                try:
                    rx = re.compile(pat)
                except re.error:
                    continue
                # Scan tag full_text
                for t in getattr(details, 'jsp_tags', []) or []:
                    fx = getattr(t, 'full_text', '') or ''
                    if not fx:
                        continue
                    for m in rx.finditer(fx):
                        if m and m.groups():
                            roles.add(m.group(1))
                        elif m:
                            roles.add(m.group(0))
                # Scan EL full_text if available
                for el in getattr(details, 'el_expressions', []) or []:
                    fx = getattr(el, 'full_text', '') or ''
                    if not fx:
                        continue
                    for m in rx.finditer(fx):
                        if m and m.groups():
                            roles.add(m.group(1))
                        elif m:
                            roles.add(m.group(0))
                # Scan embedded Java/scriptlets full_text
                for blk in getattr(details, 'embedded_java', []) or []:
                    fx = getattr(blk, 'full_text', '') or ''
                    if not fx:
                        continue
                    for m in rx.finditer(fx):
                        if m and m.groups():
                            roles.add(m.group(1))
                        elif m:
                            roles.add(m.group(0))
        except Exception:
            # best-effort; ignore configuration or scanning errors
            pass
        # From configured patterns in Step02 (pattern_hits.security)
        try:
            ph = getattr(details, 'pattern_hits', None)
            if ph and getattr(ph, 'security', None):
                for tok in ph.security:
                    if isinstance(tok, str) and tok:
                        roles.add(tok)
        except (AttributeError, TypeError, ValueError):
            pass
        return roles

    @staticmethod
    def _split_roles(val: str) -> Set[str]:
        parts = re.split(r"[,\s]+", val.strip()) if val else []
        return {p.strip().strip("'\"") for p in parts if p and p.strip()}

    @staticmethod
    def _extract_roles_from_expression(expr: str) -> Set[str]:
        roles: Set[str] = set()
        if not expr:
            return roles
        # hasRole('A'), isUserInRole('A'), hasAnyRole('A','B')
        try:
            for m in re.finditer(r"hasRole\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", expr):
                roles.add(m.group(1))
            for m in re.finditer(r"isUserInRole\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", expr):
                roles.add(m.group(1))
            any_m = re.search(r"hasAnyRole\s*\(([^\)]*)\)", expr)
            if any_m:
                inside = any_m.group(1)
                roles.update(SecurityBuilder._split_roles(inside))
        except re.error:
            return roles
        return roles
