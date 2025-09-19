import posixpath
import re
from typing import Any, Dict, List

from config import Config
from domain.config_details import CodeMapping, SemanticCategory

# Imports for JSP domain mapping
from domain.jsp_details import (
    ElExpressionEntry,
    EmbeddedJavaBlock,
    IframeRef,
    JspDetails,
    JspDirective,
    JspTagHit,
    ParsedForm,
    PatternHits,
)
from domain.source_inventory import FileDetailsBase, FileInventoryItem

from .base_parser import BaseParser
from .jsp_reader import JSPReader


class JSPParser(BaseParser):
    """
    JSP parser that uses JSPReader to extract structure and builds JSPDetails.
    
    Responsible for converting structural data to domain objects and generating
    CodeMapping objects for cross-file relationship analysis.
    """
    
    def __init__(self, config: Config) -> None:
        """
        Initialize JSP parser.

        Args:
            config: Configuration instance
        """
        super().__init__(config)

        # Create JSP reader for structural extraction
        self.reader = JSPReader(config)

    def _clean_target(self, raw: str) -> str:
        s = (raw or '').strip()
        # Strip query and fragment
        if '#' in s:
            s = s.split('#', 1)[0]
        if '?' in s:
            s = s.split('?', 1)[0]
        return s

    def can_parse(self, file_item: FileInventoryItem) -> bool:
        """
        Check if this parser can handle the given file.
        
        Args:
            file_item: FileInventoryItem to check
            
        Returns:
            True if this parser can handle the file
        """
        file_info = {
            "path": file_item.path,
            "type": file_item.type
        }
        return self.reader.can_parse(file_info)

    def _normalize_target(self, source_location: str, including_path: str, raw_path: str) -> str:
        """Normalize a JSP target path to a project-relative posix path under the source_location."""
        raw_path = self._clean_target(raw_path)
        src = (source_location or '').replace('\\', '/').strip('/')
        inc = (including_path or '').replace('\\', '/')
        inc_dir = posixpath.dirname(inc)
        # If absolute (starts with '/'), resolve from the web root (source_location)
        if raw_path.startswith('/'):
            target_rel = raw_path.lstrip('/')
        else:
            target_rel = posixpath.normpath(posixpath.join(inc_dir, raw_path))
        normalized = posixpath.normpath(posixpath.join(src, target_rel))
        return normalized

    def _emit_include_mappings(self, raw: Dict[str, Any], file_item: FileInventoryItem) -> List[CodeMapping]:
        mappings: List[CodeMapping] = []
        seen = set()
        # Directive includes: directives with type == include and attributes.file
        for d in raw.get("directives", []) or []:
            try:
                if (d.get("type") or '').lower() != 'include':
                    continue
                attrs = d.get("attributes", {}) or {}
                raw_path = attrs.get('file')
                if not raw_path:
                    continue
                to_ref = self._normalize_target(file_item.source_location, file_item.path, raw_path)
                # Only link JSP targets
                if not to_ref.lower().endswith(('.jsp', '.jspx')):
                    continue
                key = (to_ref, 'directive')
                if key in seen:
                    continue
                seen.add(key)
                mappings.append(CodeMapping(
                    from_reference=file_item.path,
                    to_reference=to_ref,
                    mapping_type='jsp_include',
                    framework='jsp',
                    semantic_category=SemanticCategory.VIEW_RENDER,
                    attributes={'include_kind': 'directive', 'raw_path': raw_path}
                ))
            except (KeyError, ValueError, TypeError):
                continue
        # Action includes: jsp:include tags with page attribute
        for tag in raw.get("jsp_tags", []) or []:
            try:
                if (tag.get('tag_name') or '').lower() != 'jsp:include':
                    continue
                attrs = tag.get('attributes', {}) or {}
                raw_path = attrs.get('page')
                if not raw_path:
                    continue
                to_ref = self._normalize_target(file_item.source_location, file_item.path, raw_path)
                if not to_ref.lower().endswith(('.jsp', '.jspx')):
                    continue
                key = (to_ref, 'action')
                if key in seen:
                    continue
                seen.add(key)
                mappings.append(CodeMapping(
                    from_reference=file_item.path,
                    to_reference=to_ref,
                    mapping_type='jsp_include',
                    framework='jsp',
                    semantic_category=SemanticCategory.VIEW_RENDER,
                    attributes={'include_kind': 'action', 'raw_path': raw_path}
                ))
            except (KeyError, ValueError, TypeError):
                continue
        return mappings

    def _emit_iframe_mappings(self, raw: Dict[str, Any], file_item: FileInventoryItem) -> List[CodeMapping]:
        mappings: List[CodeMapping] = []
        seen = set()
        for iframe in raw.get('iframes', []) or []:
            src = iframe.get('src')
            if not isinstance(src, str) or not src:
                continue
            s = self._clean_target(src)
            # skip external/null-like targets
            if s.lower().startswith(('http://', 'https://', 'about:')):
                continue
            to_ref = self._normalize_target(file_item.source_location, file_item.path, s)
            # Only capture iframe targets that are JSP pages
            if not to_ref.lower().endswith(('.jsp', '.jspx')):
                continue
            if to_ref in seen:
                continue
            seen.add(to_ref)
            mappings.append(CodeMapping(
                from_reference=file_item.path,
                to_reference=to_ref,
                mapping_type='iframe',
                framework='jsp',
                semantic_category=SemanticCategory.VIEW_RENDER,
                attributes={'raw_path': src}
            ))
        return mappings

    def _emit_redirect_mappings(self, raw: Dict[str, Any], file_item: FileInventoryItem) -> List[CodeMapping]:
        mappings: List[CodeMapping] = []
        seen = set()
        redir_re = re.compile(r"sendRedirect\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
        for block in raw.get('embedded_java', []) or []:
            code = block.get('code') or ''
            if not isinstance(code, str) or not code:
                continue
            for m in redir_re.finditer(code):
                raw_path = m.group(1)
                clean = self._clean_target(raw_path)
                to_ref = self._normalize_target(file_item.source_location, file_item.path, clean)
                if not to_ref.lower().endswith(('.jsp', '.jspx')):
                    continue
                if to_ref in seen:
                    continue
                seen.add(to_ref)
                mappings.append(CodeMapping(
                    from_reference=file_item.path,
                    to_reference=to_ref,
                    mapping_type='redirect',
                    framework='jsp',
                    semantic_category=SemanticCategory.VIEW_RENDER,
                    attributes={'raw_path': raw_path}
                ))
        return mappings

    def _emit_dispatcher_mappings(self, raw: Dict[str, Any], file_item: FileInventoryItem) -> List[CodeMapping]:
        mappings: List[CodeMapping] = []
        seen = set()
        for call in raw.get('dispatcher_calls', []) or []:
            try:
                kind = (call.get('kind') or '').lower()  # forward|include
                raw_path = call.get('target')
                if not raw_path:
                    continue
                clean = self._clean_target(raw_path)
                to_ref = self._normalize_target(file_item.source_location, file_item.path, clean)
                if not to_ref.lower().endswith(('.jsp', '.jspx')):
                    continue
                mtype = 'jsp_forward' if kind == 'forward' else 'jsp_include'
                key = (to_ref, mtype)
                if key in seen:
                    continue
                seen.add(key)
                mappings.append(CodeMapping(
                    from_reference=file_item.path,
                    to_reference=to_ref,
                    mapping_type=mtype,
                    framework='jsp',
                    semantic_category=SemanticCategory.VIEW_RENDER,
                    attributes={'raw_path': raw_path, 'via': 'RequestDispatcher'}
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return mappings

    def _emit_meta_refresh_mappings(self, raw: Dict[str, Any], file_item: FileInventoryItem) -> List[CodeMapping]:
        mappings: List[CodeMapping] = []
        seen = set()
        for mr in raw.get('meta_refresh', []) or []:
            try:
                raw_path = mr.get('url')
                if not raw_path:
                    continue
                clean = self._clean_target(raw_path)
                to_ref = self._normalize_target(file_item.source_location, file_item.path, clean)
                if not to_ref.lower().endswith(('.jsp', '.jspx')):
                    continue
                if to_ref in seen:
                    continue
                seen.add(to_ref)
                mappings.append(CodeMapping(
                    from_reference=file_item.path,
                    to_reference=to_ref,
                    mapping_type='redirect',
                    framework='jsp',
                    semantic_category=SemanticCategory.VIEW_RENDER,
                    attributes={'raw_path': raw_path, 'via': 'meta_refresh'}
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return mappings

    def _emit_js_nav_mappings(self, raw: Dict[str, Any], file_item: FileInventoryItem) -> List[CodeMapping]:
        mappings: List[CodeMapping] = []
        seen = set()
        for nav in raw.get('js_navigations', []) or []:
            try:
                raw_path = nav.get('target')
                if not raw_path:
                    continue
                clean = self._clean_target(raw_path)
                to_ref = self._normalize_target(file_item.source_location, file_item.path, clean)
                if not to_ref.lower().endswith(('.jsp', '.jspx')):
                    continue
                if to_ref in seen:
                    continue
                seen.add(to_ref)
                mappings.append(CodeMapping(
                    from_reference=file_item.path,
                    to_reference=to_ref,
                    mapping_type='redirect',
                    framework='jsp',
                    semantic_category=SemanticCategory.VIEW_RENDER,
                    attributes={'raw_path': raw_path, 'via': 'js_location'}
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return mappings

    def _emit_action_call_mappings(self, raw: Dict[str, Any], file_item: FileInventoryItem) -> List[CodeMapping]:
        """Emit CodeMapping entries for form actions and simple anchor/form targets that look like action invocations.

        Conservative: only emit when a static target string is present and it does not point to a JSP file or an external URL.
        The to_reference is the cleaned raw target (query/fragment stripped). Step04 will attempt to resolve this to Route entities.
        """
        mappings: List[CodeMapping] = []
        seen = set()

        def _is_external(t: str) -> bool:
            tl = (t or '').lower()
            return tl.startswith(('http://', 'https://', 'mailto:', 'javascript:', 'data:')) or tl.startswith('#')

        # HTML forms
        for form in raw.get('form_elements', []) or []:
            try:
                attrs = form.get('attributes', {}) or {}
                raw_action = attrs.get('action')
                if not raw_action or not isinstance(raw_action, str):
                    continue
                clean = self._clean_target(raw_action)
                if not clean or _is_external(clean):
                    continue
                # Skip explicit JSP targets (we handle JSP includes/redirects elsewhere)
                if clean.lower().endswith(('.jsp', '.jspx')):
                    continue
                # normalize target to a simple form (preserve leading slash if present)
                to_ref = clean
                key = (file_item.path, to_ref)
                if key in seen:
                    continue
                seen.add(key)
                # include span evidence if present on the parsed form
                line = form.get('line')
                end_line = form.get('end_line')
                attrs_copy = {'http_method': (attrs.get('method') or '').upper(), 'raw_path': raw_action}
                if line is not None:
                    attrs_copy['line'] = line
                if end_line is not None:
                    attrs_copy['end_line'] = end_line
                mappings.append(CodeMapping(
                    from_reference=file_item.path,
                    to_reference=to_ref,
                    mapping_type='action_call',
                    framework='jsp',
                    semantic_category=SemanticCategory.ENTRY_POINT,
                    attributes=attrs_copy
                ))
            except (KeyError, TypeError, ValueError):
                continue

        # Try simple anchor hrefs if present in html_elements counts are not sufficient; attempt to parse anchors from jsp_tags if any
        for tag in raw.get('jsp_tags', []) or []:
            try:
                # Some custom tags may include 'href' or 'action' attributes
                attrs = tag.get('attributes', {}) or {}
                raw_action = attrs.get('href') or attrs.get('action') or attrs.get('url')
                if not raw_action or not isinstance(raw_action, str):
                    continue
                clean = self._clean_target(raw_action)
                if not clean or _is_external(clean):
                    continue
                if clean.lower().endswith(('.jsp', '.jspx')):
                    continue
                to_ref = clean
                key = (file_item.path, to_ref)
                if key in seen:
                    continue
                seen.add(key)
                # attach tag span evidence if available
                line = tag.get('line')
                end_line = tag.get('end_line')
                attrs_copy = {'raw_path': raw_action, 'tag': tag.get('tag_name')}
                if line is not None:
                    attrs_copy['line'] = line
                if end_line is not None:
                    attrs_copy['end_line'] = end_line
                mappings.append(CodeMapping(
                    from_reference=file_item.path,
                    to_reference=to_ref,
                    mapping_type='action_call',
                    framework='jsp',
                    semantic_category=SemanticCategory.ENTRY_POINT,
                    attributes=attrs_copy
                ))
            except (KeyError, TypeError, ValueError):
                continue

        return mappings

    def _emit_jsp_security_mappings(self, raw: Dict[str, Any], file_item: FileInventoryItem) -> List[CodeMapping]:
        """Conservative JSP security extractor.

        Scans recorded JSP tags, EL expressions and embedded Java for:
        - literal role mentions via attributes (role/roles/access) and expressions (hasRole/isUserInRole/hasAnyRole)
        - simple helper calls like Security.getSecurityLevels/getSecurityGroups and numeric comparisons

        Emits CodeMapping entries with mapping_type 'jsp_security' and attributes describing the token(s)
        and best-effort line/span evidence for Step04 to consume.
        """
        mappings: List[CodeMapping] = []
        seen = set()

        # helper functions
        def _add_mapping(key_tuple, token_type, tokens, raw_text, line=None, end_line=None, extra=None):
            if key_tuple in seen:
                return
            seen.add(key_tuple)
            attrs = {'token_type': token_type, 'tokens': list(tokens) if isinstance(tokens, (list, set)) else [tokens], 'raw_text': raw_text}
            if line is not None:
                attrs['line'] = line
            if end_line is not None:
                attrs['end_line'] = end_line
            if extra:
                attrs.update(extra)
            mappings.append(CodeMapping(
                from_reference=file_item.path,
                to_reference=file_item.path,
                mapping_type='jsp_security',
                framework='jsp',
                semantic_category=SemanticCategory.CROSS_CUTTING,
                attributes=attrs
            ))

        # regexes
        has_role_re = re.compile(r"hasRole\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.IGNORECASE)
        has_any_re = re.compile(r"hasAnyRole\s*\(\s*([^\)]*)\)", re.IGNORECASE)
        is_user_in_re = re.compile(r"isUserInRole\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.IGNORECASE)
        access_attr_re = re.compile(r"\baccess\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
        helper_levels_re = re.compile(r"(getSecurityLevels|getSecurityGroups|getSecurity)\s*\([^\)]*\)\s*([<>]=?|==)\s*(\d+)", re.IGNORECASE)
        helper_call_re = re.compile(r"\b(getSecurityLevels|getSecurityGroups|getSecurity)\s*\(([^\)]*)\)", re.IGNORECASE)

        # 1) Inspect JSP tag attributes and full_text
        for t in raw.get('jsp_tags', []) or []:
            try:
                attrs = t.get('attributes', {}) or {}
                full = t.get('full_text', '') or ''
                line = t.get('line')
                end_line = t.get('end_line')
                # direct role/roles attributes
                for key in ("role", "roles"):
                    val = attrs.get(key)
                    if isinstance(val, str) and val.strip():
                        parts = [p.strip().strip('"\'') for p in re.split(r"[,;]", val) if p.strip()]
                        if parts:
                            _add_mapping((file_item.path, 'tag_roles', full, line), 'role', parts, full, line, end_line)
                # access attribute may contain hasRole or comma list
                acc = attrs.get('access')
                if isinstance(acc, str) and acc.strip():
                    # try extract roles from access
                    roles = []
                    m_acc = access_attr_re.search(f"access={acc}")
                    if m_acc:
                        roles = [p.strip().strip('"\'') for p in re.split(r"[,;]", m_acc.group(1)) if p.strip()]
                    # fallback: scan full_text for hasRole/isUserInRole
                    for m in has_role_re.finditer(full):
                        roles.append(m.group(1))
                    for m in has_any_re.finditer(full):
                        inside = m.group(1) or ''
                        roles.extend([p.strip().strip('"\'') for p in re.split(r"[,;]", inside) if p.strip()])
                    if roles:
                        _add_mapping((file_item.path, 'tag_access', full, line), 'role', set(roles), full, line, end_line)
                # scan full_text for helper getSecurityLevels comparisons
                for m in helper_levels_re.finditer(full):
                    helper = m.group(1)
                    op = m.group(2)
                    val = m.group(3)
                    _add_mapping((file_item.path, 'tag_helper', full, line, helper, op, val), 'group_level', {'helper': helper, 'op': op, 'value': int(val)}, full, line, end_line)
                # scan full text for hasRole/isUserInRole
                for m in has_role_re.finditer(full):
                    _add_mapping((file_item.path, 'tag_hasRole', m.group(1), line), 'role', m.group(1), m.group(0), line, end_line)
                for m in is_user_in_re.finditer(full):
                    _add_mapping((file_item.path, 'tag_isUserInRole', m.group(1), line), 'role', m.group(1), m.group(0), line, end_line)
            except (KeyError, TypeError, ValueError):
                continue

        # 2) EL expressions
        for el in raw.get('el_expressions', []) or []:
            try:
                expr = el.get('expression', '') or ''
                full = el.get('full_text', '') or ''
                line = el.get('line')
                end_line = el.get('end_line')
                # hasRole / isUserInRole
                for m in has_role_re.finditer(expr):
                    _add_mapping((file_item.path, 'el_hasRole', m.group(1), line), 'role', m.group(1), m.group(0), line, end_line)
                for m in has_any_re.finditer(expr):
                    inside = m.group(1) or ''
                    parts = [p.strip().strip('"\'') for p in re.split(r"[,;]", inside) if p.strip()]
                    if parts:
                        _add_mapping((file_item.path, 'el_hasAnyRole', tuple(parts), line), 'role', parts, full, line, end_line)
                for m in is_user_in_re.finditer(expr):
                    _add_mapping((file_item.path, 'el_isUserInRole', m.group(1), line), 'role', m.group(1), m.group(0), line, end_line)
                # helper comparisons
                for m in helper_levels_re.finditer(expr):
                    helper = m.group(1)
                    op = m.group(2)
                    val = m.group(3)
                    _add_mapping((file_item.path, 'el_helper', expr, helper, op, val), 'group_level', {'helper': helper, 'op': op, 'value': int(val)}, expr, line, end_line)
            except (KeyError, TypeError, ValueError):
                continue

        # 3) Embedded Java/scriptlets
        for blk in raw.get('embedded_java', []) or []:
            try:
                code = blk.get('code', '') or ''
                full = blk.get('full_text', '') or ''
                line = blk.get('line')
                end_line = blk.get('end_line')
                # hasRole / isUserInRole in scriptlets
                for m in has_role_re.finditer(code):
                    _add_mapping((file_item.path, 'java_hasRole', m.group(1), line), 'role', m.group(1), m.group(0), line, end_line)
                for m in has_any_re.finditer(code):
                    inside = m.group(1) or ''
                    parts = [p.strip().strip('"\'') for p in re.split(r"[,;]", inside) if p.strip()]
                    if parts:
                        _add_mapping((file_item.path, 'java_hasAnyRole', tuple(parts), line), 'role', parts, m.group(0), line, end_line)
                for m in is_user_in_re.finditer(code):
                    _add_mapping((file_item.path, 'java_isUserInRole', m.group(1), line), 'role', m.group(1), m.group(0), line, end_line)
                # helper calls and numeric comparisons
                for m in helper_levels_re.finditer(code):
                    helper = m.group(1)
                    op = m.group(2)
                    val = m.group(3)
                    _add_mapping((file_item.path, 'java_helper', code, helper, op, val), 'group_level', {'helper': helper, 'op': op, 'value': int(val)}, m.group(0), line, end_line)
                for m in helper_call_re.finditer(code):
                    helper = m.group(1)
                    args = m.group(2)
                    _add_mapping((file_item.path, 'java_helper_call', code, helper, args), 'helper_call', {'helper': helper, 'args': args}, m.group(0), line, end_line)
            except (KeyError, TypeError, ValueError):
                continue

        return mappings

    def _emit_jsp_java_call_mappings(self, raw: Dict[str, Any], file_item: FileInventoryItem) -> List[CodeMapping]:
        """Emit mappings for JSP scriptlets calling into Java handler objects that generate XHTML.
        Heuristic patterns:
        - <Var>.xhtmlHandlerObject().method(...)
        - HandlerClass.xhtmlHandlerObject().method(...)
        - Calls to XHTMLEncoder.* within scriptlets
        """
        mappings: List[CodeMapping] = []
        seen = set()
        call_re = re.compile(r"([A-Za-z_][A-ZaZ0-9_\.]*)\.xhtmlHandlerObject\s*\(\s*\)\s*\.\s*([A-Za-z_][A-ZaZ0-9_]*)\s*\(")
        enc_re = re.compile(r"\bXHTMLEncoder\s*\.\s*([A-Za-z_][A-ZaZ0-9_]*)\s*\(")
        # Final corrected patterns (no stray quotes after the parenthesis)
        call_re = re.compile(r"([A-Za-z_][A-ZaZ0-9_\.]*)\.xhtmlHandlerObject\s*\(\s*\)\s*\.\s*([A-Za-z_][A-ZaZ0-9_]*)\s*\(")
        enc_re = re.compile(r"\bXHTMLEncoder\s*\.\s*([A-Za-z_][A-ZaZ0-9_]*)\s*\(")
        call_re = re.compile(r"([A-Za-z_][A-ZaZ0-9_\.]*)\.xhtmlHandlerObject\s*\(\s*\)\s*\.\s*([A-Za-z_][A-ZaZ0-9_]*)\s*\(")
        enc_re = re.compile(r"\bXHTMLEncoder\s*\.\s*([A-ZaZ_][A-ZaZ0-9_]*)\s*\(")
        # Use cleaned patterns
        call_re = re.compile(r"([A-Za-z_][A-ZaZ0-9_\.]*)\.xhtmlHandlerObject\s*\(\s*\)\s*\.\s*([A-Za-z_][A-ZaZ0-9_]*)\s*\(")
        enc_re = re.compile(r"\bXHTMLEncoder\s*\.\s*([A-ZaZ_][A-ZaZ0-9_]*)\s*\(")
        for blk in raw.get('embedded_java', []) or []:
            code = blk.get('code') or ''
            if not isinstance(code, str) or not code:
                continue
            line = blk.get('line')
            for m in call_re.finditer(code):
                owner = m.group(1)
                method = m.group(2)
                to_ref = f"{owner}.xhtmlHandlerObject.{method}"
                if to_ref in seen:
                    continue
                seen.add(to_ref)
                attrs = {'raw_call': m.group(0)}
                if line is not None:
                    attrs['line'] = line
                mappings.append(CodeMapping(
                    from_reference=file_item.path,
                    to_reference=to_ref,
                    mapping_type='jsp_java_call',
                    framework='jsp',
                    semantic_category=SemanticCategory.VIEW_RENDER,
                    attributes=attrs
                ))
            for m in enc_re.finditer(code):
                enc_method = m.group(1)
                to_ref = f"XHTMLEncoder.{enc_method}"
                if to_ref in seen:
                    continue
                seen.add(to_ref)
                attrs = {'raw_call': m.group(0)}
                if line is not None:
                    attrs['line'] = line
                mappings.append(CodeMapping(
                    from_reference=file_item.path,
                    to_reference=to_ref,
                    mapping_type='jsp_java_call',
                    framework='jsp',
                    semantic_category=SemanticCategory.VIEW_RENDER,
                    attributes=attrs
                ))
        return mappings

    def parse_file(self, file_item: FileInventoryItem) -> FileDetailsBase:
        """
        Parse a JSP file and build JspDetails from reader output.
        
        Args:
            file_item: FileInventoryItem to parse
            
        Returns:
            JspDetails with extracted structural data and convenience fields
        """
        try:
            self.logger.debug(
                "Starting to parse JSP file: %s (source_location: %s)",
                file_item.path,
                file_item.source_location,
            )

            # Use reader to extract structural data
            parse_result = self.reader.parse_file(file_item.source_location, file_item.path)

            if not parse_result.success:
                self.logger.error("Parse failed for JSP file: %s", file_item.path)
                return JspDetails()

            raw = parse_result.structural_data or {}

            # Map reader dict -> domain PatternHits
            pattern_hits = PatternHits(
                legacy=raw.get("legacy_pattern_hits", []) or [],
                security=raw.get("security_tag_hits", []) or [],
                menu=raw.get("menu_block_hits", []) or [],
                service=raw.get("service_invocation_hits", []) or [],
                tiles=raw.get("tiles_pattern_hits", []) or [],
                custom_tag_prefixes=raw.get("custom_tag_prefix_hits", []) or [],
            )

            # Convert sections
            directives = [JspDirective.from_dict(d) for d in raw.get("directives", [])]
            forms = [ParsedForm.from_dict(f) for f in raw.get("form_elements", [])]
            jsp_tags = [JspTagHit.from_dict(t) for t in raw.get("jsp_tags", [])]
            embedded_java = [EmbeddedJavaBlock.from_dict(e) for e in raw.get("embedded_java", [])]
            el_expressions = [ElExpressionEntry.from_dict(e) for e in raw.get("el_expressions", [])]
            iframes = [IframeRef.from_dict(i) for i in raw.get("iframes", [])]

            # Convenience fields: tag_libraries (from taglib directives), page_directives (merged)
            tag_libraries: List[str] = []
            page_directives: Dict[str, str] = {}
            for d in directives:
                dtype = (d.type or "").lower()
                if dtype == "taglib":
                    uri = d.attributes.get("uri") or d.attributes.get("tagdir")
                    if uri:
                        tag_libraries.append(uri)
                elif dtype == "page":
                    # Merge attributes, last wins
                    page_directives.update(d.attributes or {})

            jsp_details = JspDetails(
                screen_elements=None,
                tag_libraries=tag_libraries,
                includes=raw.get("includes", []) or [],
                page_directives=page_directives,
                file_path=raw.get("file_path"),
                page_type=raw.get("page_type"),
                directives=directives,
                form_elements=forms,
                jsp_tags=jsp_tags,
                embedded_java=embedded_java,
                el_expressions=el_expressions,
                html_elements=raw.get("html_elements", {}) or {},
                pattern_hits=pattern_hits,
                iframes=iframes,
            )

            # Generate JSP code mappings (includes, iframes, redirects)
            code_mappings: List[CodeMapping] = []
            code_mappings.extend(self._emit_include_mappings(raw, file_item))
            code_mappings.extend(self._emit_iframe_mappings(raw, file_item))
            code_mappings.extend(self._emit_redirect_mappings(raw, file_item))
            # New: emit forward/include via RequestDispatcher
            code_mappings.extend(self._emit_dispatcher_mappings(raw, file_item))
            # New: meta refresh and JS navigation redirects
            code_mappings.extend(self._emit_meta_refresh_mappings(raw, file_item))
            code_mappings.extend(self._emit_js_nav_mappings(raw, file_item))
            # New: action call mappings from form actions and anchors
            code_mappings.extend(self._emit_action_call_mappings(raw, file_item))
            # New: emit conservative JSP security tokens for Step04 to consume
            code_mappings.extend(self._emit_jsp_security_mappings(raw, file_item))
            # New: emit JSP->Java call mappings for handler invocations
            code_mappings.extend(self._emit_jsp_java_call_mappings(raw, file_item))
            jsp_details.code_mappings = code_mappings

            self.logger.debug(
                "Completed JSP parse: taglibs=%d, includes=%d, directives(page)=%d, mappings=%d",
                len(tag_libraries),
                len(jsp_details.includes),
                1 if page_directives else 0,
                len(code_mappings),
            )

            return jsp_details

        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to parse JSP file %s: %s", file_item.path, str(e))
            return JspDetails()