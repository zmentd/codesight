"""
JSP parser implementation for web interface components.

Handles JSP files and extracts form elements, JSP tags, and embedded Java
using existing domain models and LEX utilities.
"""

import re
import time
from typing import Any, Dict, List, Optional

from config import Config
from lex.rules.java_rules import JavaDetectionRules
from lex.rules.web_rules import WebDetectionRules

from .base_reader import BaseReader, ParseResult


class JSPReader(BaseReader):
    """
    JSP-specific parsing for web interface components.
    
    Extracts form fields, actions, JSP tags, and embedded Java
    using existing LEX web rules.
    """
    
    def __init__(self, config: Config) -> None:
        """
        Initialize JSP parser.
        
        Args:
            config: Configuration instance
        """
        super().__init__(config)
        
        # Use existing LEX rules
        self.java_rules = JavaDetectionRules()
        self.web_rules = WebDetectionRules()
        
        # JSP-specific patterns
        # Allow multiline content inside JSP constructs and avoid directives/expressions for scriptlets
        self.jsp_directive_pattern = re.compile(r'<%@\s*(\w+)(.*?)%>', re.DOTALL)
        self.jsp_expression_pattern = re.compile(r'<%=\s*(.*?)\s*%>', re.DOTALL)
        self.jsp_scriptlet_pattern = re.compile(r'<%(?![@=!])(.*?)%>', re.DOTALL)
        self.el_expression_pattern = re.compile(r'\$\{([^}]+)\}')
        # Broadened: capture any namespaced tag like sec:authorize, security:intercept-url, as well as jsp:, c:, fmt:, fn:
        self.jsp_tag_pattern = re.compile(r'<([A-Za-z_][\w\-]*:[\w\-]+)([^>]*)/?>', re.IGNORECASE)
        # IFRAME open tag (case-insensitive)
        self.iframe_open_tag_pattern = re.compile(r'<iframe\b([^>]*)>', re.IGNORECASE)
        # New: meta refresh redirect detection
        self.meta_refresh_pattern = re.compile(
            r'<meta[^>]*http-equiv\s*=\s*["\']?refresh["\']?[^>]*content\s*=\s*["\']?\s*\d+\s*;\s*url\s*=\s*([^"\'>\s]+)'
            , re.IGNORECASE)
        # New: JavaScript-based navigation patterns
        self.js_location_assign_pattern = re.compile(r'(?:window\.|top\.|parent\.|)location(?:\.href)?\s*=\s*[\"\']([^\"\']+)[\"\']', re.IGNORECASE)
        self.js_location_call_pattern = re.compile(r'(?:window\.|top\.|parent\.|)location\.(?:replace|assign)\(\s*[\"\']([^\"\']+)[\"\']\s*\)', re.IGNORECASE)
        # New: RequestDispatcher forward/include
        self.dispatcher_call_pattern = re.compile(r'getRequestDispatcher\(\s*[\"\']([^\"\']+)[\"\']\s*\)\s*\.\s*(forward|include)\s*\(', re.IGNORECASE | re.DOTALL)

    def can_parse(self, file_info: Dict[str, Any]) -> bool:
        """
        Check if this parser can handle JSP files.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            True if file is a JSP file
        """
        file_path: str = file_info.get("path", "")
        file_type: str = file_info.get("type", "")
        
        return bool(file_path.endswith((".jsp", ".jspx")) or file_type == "jsp")
    
    def parse_file(self, source_path: str, file_path: str) -> ParseResult:
        """
        Parse JSP file and extract structural information.
        
        Args:
            source_path: Base source path
            file_path: Path to the JSP file
            
        Returns:
            Parse result with JSP structural data
        """
        start_time = time.time()
        
        try:
            # Read file content
            content = self.read_file(source_path, file_path)
            
            # Pre-process content
            processed_content = self._pre_process_content(content, file_path)
            
            # Extract JSP components
            structural_data = self._extract_jsp_structure(file_path, processed_content)
            
            # Detect framework patterns
            framework_hints = self._detect_jsp_framework_patterns(processed_content)
            
            # Calculate confidence
            confidence = self._calculate_confidence(structural_data)
            
            result = ParseResult(
                success=True,
                file_path=file_path,
                language="jsp",
                structural_data=structural_data,
                confidence=confidence,
                framework_hints=framework_hints,
                processing_time=time.time() - start_time
            )
            
            return self._post_process_result(result)
            
        except Exception as e:  # pylint: disable=broad-except
            return self._handle_parse_error(file_path, e)
    
    def _extract_jsp_structure(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Extract JSP structural information, including config-driven pattern hits.
        """
        config = self.config if hasattr(self, 'config') else Config.get_instance()
        # Pattern lists from config
        legacy_patterns = config.jsp_analysis.legacy_patterns
        security_patterns = config.jsp_analysis.security_tag_patterns
        menu_patterns = config.jsp_analysis.menu_detection
        service_patterns = config.jsp_analysis.service_invocation_hints
        tiles_patterns = config.jsp_analysis.tiles_patterns
        custom_tag_prefixes = config.jsp_analysis.custom_tag_prefixes

        def _normalize(p: str) -> str:
            # Double backslashes and escape double quotes for consistent comparison
            return p.replace('\\', r'\\').replace('"', r'\"')

        # Pattern hit helpers
        def find_pattern_hits(patterns: List[str], text: str) -> List[str]:
            hits = []
            for pat in patterns:
                try:
                    if re.search(pat, text, re.IGNORECASE):
                        hits.append(_normalize(pat))
                except re.error:
                    continue
            return hits

        # Structural extraction
        structural_data: Dict[str, Any] = {
            "file_path": file_path,
            "page_type": "jsp",
            "directives": self._extract_jsp_directives(content),
            "form_elements": self._extract_form_elements(content),
            "jsp_tags": self._extract_jsp_tags(content),
            "embedded_java": self._extract_embedded_java(content),
            "el_expressions": self._extract_el_expressions(content),
            "includes": self._extract_includes(content),
            "html_elements": self._extract_html_elements(content),
            # New: iframe references
            "iframes": self._extract_iframes(content),
            # Pattern hits
            "legacy_pattern_hits": find_pattern_hits(legacy_patterns, content),
            "security_tag_hits": find_pattern_hits(security_patterns, content),
            "menu_block_hits": find_pattern_hits(menu_patterns, content),
            "service_invocation_hits": find_pattern_hits(service_patterns, content),
            "tiles_pattern_hits": find_pattern_hits(tiles_patterns, content),
            "custom_tag_prefix_hits": [
                prefix for prefix in (custom_tag_prefixes or []) if f'<{prefix}' in content
            ],
        }

        # New: meta refresh redirects
        structural_data["meta_refresh"] = self._extract_meta_refresh(content)
        # New: JS navigations
        structural_data["js_navigations"] = self._extract_js_navigations(content)
        # New: RequestDispatcher forward/include calls
        structural_data["dispatcher_calls"] = self._extract_dispatcher_calls(content)

        # Heuristic: if page explicitly includes VBScript blocks, do not report
        # generic VBScript/document.all legacy hits to avoid over-counting.
        try:
            if re.search(r"<script[^>]*language\s*=\s*['\"]?vbscript", content, re.IGNORECASE):
                structural_data["legacy_pattern_hits"] = [
                    p for p in structural_data.get("legacy_pattern_hits", [])
                    if p not in {"VBScript", "document.all"}
                ]
        except re.error:
            pass

        return structural_data
    
    def _extract_jsp_directives(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract JSP directives (page, taglib, include).
        
        Args:
            content: JSP content
            
        Returns:
            List of directive information
        """
        directives: List[Dict[str, Any]] = []
        
        for match in self.jsp_directive_pattern.finditer(content):
            directive_type = match.group(1)
            attributes_str = match.group(2).strip()
            
            # Parse attributes
            attributes: Dict[str, str] = {}
            attr_pattern = re.compile(r'(\w+)\s*=\s*["\']([^"\']*)["\']')
            for attr_match in attr_pattern.finditer(attributes_str):
                attr_name = attr_match.group(1)
                attr_value = attr_match.group(2)
                attributes[attr_name] = attr_value
            
            directives.append({
                "type": directive_type,
                "attributes": attributes,
                "full_text": match.group(0)
            })
        
        return directives
    
    def _extract_form_elements(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract HTML form elements.
        
        Args:
            content: JSP/HTML content
            
        Returns:
            List of form element information
        """
        form_elements: List[Dict[str, Any]] = []
        
        # Extract form tags
        form_pattern = re.compile(r'<form([^>]*)>(.*?)</form>', re.DOTALL | re.IGNORECASE)
        for form_match in form_pattern.finditer(content):
            form_attrs = self._parse_html_attributes(form_match.group(1))
            form_content = form_match.group(2)

            # Compute line/span for the whole form
            start_line = content.count('\n', 0, form_match.start()) + 1
            end_line = content.count('\n', 0, form_match.end()) + 1
            
            # Extract input elements within this form
            input_pattern = re.compile(r'<input([^>]*)/?>|<select([^>]*)>.*?</select>|<textarea([^>]*)>.*?</textarea>', 
                                     re.DOTALL | re.IGNORECASE)
            
            form_inputs: List[Dict[str, Any]] = []
            for input_match in input_pattern.finditer(form_content):
                input_attrs = self._parse_html_attributes(input_match.group(1) or input_match.group(2) or input_match.group(3))
                form_inputs.append({
                    "tag": input_match.group(0).split()[0][1:].lower(),
                    "attributes": input_attrs
                })
            
            form_elements.append({
                "type": "form",
                "attributes": form_attrs,
                "inputs": form_inputs,
                "line": start_line,
                "end_line": end_line,
                "full_text": form_match.group(0),
            })
        
        return form_elements
    
    def _extract_jsp_tags(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract JSP custom tags (namespaced tags like jsp:, c:, fmt:, fn:, sec:, security:, etc.).

        Args:
            content: JSP content

        Returns:
            List of JSP tag information
        """
        jsp_tags: List[Dict[str, Any]] = []

        for match in self.jsp_tag_pattern.finditer(content):
            tag_name = match.group(1)
            attributes_str = match.group(2).strip()
            attributes = self._parse_html_attributes(attributes_str)

            # Skip common framework library prefixes (Struts 's', JSP standard tags, JSTL, etc.)
            try:
                prefix = (tag_name.split(':', 1)[0] or '').lower()
            except Exception:
                prefix = ''
            if prefix in {"s", "jsp", "c", "fmt", "fn", "bean", "logic", "html"}:
                continue

            # Compute line/span info
            start_line = content.count('\n', 0, match.start()) + 1
            end_line = content.count('\n', 0, match.end()) + 1

            jsp_tags.append({
                "tag_name": tag_name,
                "attributes": attributes,
                "full_text": match.group(0),
                "line": start_line,
                "end_line": end_line,
            })

        return jsp_tags
    
    def _extract_embedded_java(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract embedded Java code (scriptlets).
        
        Args:
            content: JSP content
            
        Returns:
            List of embedded Java code blocks
        """
        embedded_java: List[Dict[str, Any]] = []
        
        # Extract scriptlets (excluding directives, expressions, declarations)
        for match in self.jsp_scriptlet_pattern.finditer(content):
            java_code = (match.group(1) or '').strip()
            if java_code:
                start_line = content.count('\n', 0, match.start()) + 1
                end_line = content.count('\n', 0, match.end()) + 1
                embedded_java.append({
                    "type": "scriptlet",
                    "code": java_code,
                    "full_text": match.group(0),
                    "line": start_line,
                    "end_line": end_line,
                })
        
        # Extract expressions
        for match in self.jsp_expression_pattern.finditer(content):
            expression = (match.group(1) or '').strip()
            start_line = content.count('\n', 0, match.start()) + 1
            end_line = content.count('\n', 0, match.end()) + 1
            embedded_java.append({
                "type": "expression", 
                "code": expression,
                "full_text": match.group(0),
                "line": start_line,
                "end_line": end_line,
            })
        
        return embedded_java
    
    def _extract_el_expressions(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract EL (Expression Language) expressions.
        
        Args:
            content: JSP content
            
        Returns:
            List of EL expressions
        """
        el_expressions: List[Dict[str, Any]] = []
        
        for match in self.el_expression_pattern.finditer(content):
            expression = match.group(1).strip()
            start_line = content.count('\n', 0, match.start()) + 1
            end_line = content.count('\n', 0, match.end()) + 1
            el_expressions.append({
                "expression": expression,
                "full_text": match.group(0),
                "line": start_line,
                "end_line": end_line,
            })
        
        return el_expressions
    
    def _extract_includes(self, content: str) -> List[str]:
        """
        Extract JSP includes and forwards.
        
        Args:
            content: JSP content
            
        Returns:
            List of included file paths
        """
        includes: List[str] = []
        
        # JSP include directives
        include_pattern = re.compile(r'<%@\s*include\s+file\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
        for match in include_pattern.finditer(content):
            includes.append(match.group(1))
        
        # JSP include actions
        action_pattern = re.compile(r'<jsp:include\s+page\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
        for match in action_pattern.finditer(content):
            includes.append(match.group(1))
        
        return includes
    
    def _extract_html_elements(self, content: str) -> Dict[str, int]:
        """
        Extract basic HTML element counts.
        
        Args:
            content: JSP/HTML content
            
        Returns:
            Dictionary with HTML element counts
        """
        html_elements: Dict[str, int] = {}
        
        # Count common HTML elements
        common_tags = ['div', 'span', 'table', 'tr', 'td', 'th', 'ul', 'li', 'p', 'h1', 'h2', 'h3', 'iframe']
        
        for tag in common_tags:
            pattern = re.compile(f'<{tag}[^>]*>', re.IGNORECASE)
            count = len(pattern.findall(content))
            if count > 0:
                html_elements[tag] = count
        
        return html_elements
    
    def _parse_html_attributes(self, attr_string: str) -> Dict[str, str]:
        """
        Parse HTML attributes from attribute string.
        Supports quoted (single/double) and unquoted values, plus boolean attrs.
        
        Args:
            attr_string: HTML attribute string
            
        Returns:
            Dictionary of attribute name-value pairs
        """
        attributes: Dict[str, str] = {}
        
        if not attr_string:
            return attributes
        
        # Pattern captures name and value in one of three groups (double-quoted, single-quoted, or unquoted)
        attr_pattern = re.compile(r'(\w+)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s\"\'=<>&`]+)))?', re.IGNORECASE)
        for match in attr_pattern.finditer(attr_string):
            name = match.group(1)
            val = match.group(2) or match.group(3) or match.group(4)
            # Boolean attributes (no value) get empty string
            attributes[name] = val if val is not None else ""
        
        return attributes
    
    def _detect_jsp_framework_patterns(self, content: str) -> List[str]:
        """
        Detect JSP framework patterns using LEX rules.
        
        Args:
            content: JSP content
            
        Returns:
            List of detected framework hints
        """
        framework_hints: List[str] = []
        
        try:
            # Use LEX Java rules for JSP patterns
            jsp_patterns = self.java_rules.get_jsp_patterns()
            
            for pattern, _ in jsp_patterns:
                if pattern in content:
                    if 'jsp:' in pattern:
                        framework_hints.append("jsp_standard")
                    elif 'c:' in pattern:
                        framework_hints.append("jstl_core")
                    elif 'fmt:' in pattern:
                        framework_hints.append("jstl_format")
                    elif 'fn:' in pattern:
                        framework_hints.append("jstl_functions")
            
            # Check for Struts JSP tags
            if '<html:' in content or '<bean:' in content or '<logic:' in content:
                framework_hints.append("struts_jsp")
            
            # Check for Spring form tags
            if '<form:' in content or '<spring:' in content:
                framework_hints.append("spring_jsp")
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.warning("Failed to detect JSP framework patterns: %s", str(e))
        
        return list(set(framework_hints))  # Remove duplicates

    def _extract_iframes(self, content: str) -> List[Dict[str, Any]]:
        """Extract iframe references with attributes and src."""
        iframes: List[Dict[str, Any]] = []
        for match in self.iframe_open_tag_pattern.finditer(content):
            attr_str = match.group(1) or ''
            attrs = self._parse_html_attributes(attr_str)
            # Attempt to read src in a case-insensitive way without mutating keys
            src = attrs.get('src') or attrs.get('SRC')
            iframes.append({
                'src': src,
                'attributes': attrs,
                'full_text': match.group(0)
            })
        return iframes

    # New helpers
    def _extract_meta_refresh(self, content: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        try:
            for m in self.meta_refresh_pattern.finditer(content):
                url = (m.group(1) or '').strip()
                results.append({
                    'url': url,
                    'full_text': m.group(0)
                })
        except re.error:
            pass
        return results

    def _extract_js_navigations(self, content: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        try:
            for m in self.js_location_assign_pattern.finditer(content):
                results.append({'kind': 'assign', 'target': (m.group(1) or '').strip(), 'full_text': m.group(0)})
            for m in self.js_location_call_pattern.finditer(content):
                results.append({'kind': 'call', 'target': (m.group(1) or '').strip(), 'full_text': m.group(0)})
        except re.error:
            pass
        return results

    def _extract_dispatcher_calls(self, content: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        try:
            for m in self.dispatcher_call_pattern.finditer(content):
                target = (m.group(1) or '').strip()
                action = (m.group(2) or '').strip().lower()  # forward|include
                results.append({'kind': action, 'target': target, 'full_text': m.group(0)})
        except re.error:
            pass
        return results
