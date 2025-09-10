"""Web technology detection rules and patterns."""

import re
from typing import Any, Dict, List, Optional, Tuple, Union


class WebDetectionRules:
    """
    Web technology detection rules for identifying HTML, CSS, JavaScript,
    JSP, JSF, and other web-related files and frameworks.
    """
    
    @staticmethod
    def get_html_extensions() -> List[str]:
        """Get HTML-related file extensions."""
        return ['.html', '.htm', '.xhtml', '.shtml', '.jsp', '.jsf', '.xsp']
    
    @staticmethod
    def get_css_extensions() -> List[str]:
        """Get CSS-related file extensions."""
        return ['.css', '.scss', '.sass', '.less', '.styl']
    
    @staticmethod
    def get_javascript_extensions() -> List[str]:
        """Get JavaScript-related file extensions."""
        return ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.es6', '.es']
    
    @staticmethod
    def get_html_detection_patterns() -> List[Tuple[str, int]]:
        """Get regex patterns for HTML detection with weights."""
        return [
            # DOCTYPE declarations
            (r'<!DOCTYPE\s+html', 20),
            (r'<!DOCTYPE\s+HTML', 15),
            (r'<!DOCTYPE\s+html\s+PUBLIC', 15),
            
            # HTML tags
            (r'<html[^>]*>', 18),
            (r'<head[^>]*>', 15),
            (r'<body[^>]*>', 15),
            (r'<title[^>]*>.*?</title>', 12),
            (r'<meta[^>]*>', 10),
            (r'<link[^>]*>', 8),
            (r'<script[^>]*>', 10),
            (r'<style[^>]*>', 8),
            
            # Common HTML elements
            (r'<div[^>]*>', 8),
            (r'<span[^>]*>', 6),
            (r'<p[^>]*>', 6),
            (r'<h[1-6][^>]*>', 8),
            (r'<ul[^>]*>|<ol[^>]*>|<li[^>]*>', 6),
            (r'<table[^>]*>|<tr[^>]*>|<td[^>]*>|<th[^>]*>', 8),
            (r'<form[^>]*>', 8),
            (r'<input[^>]*>', 8),
            (r'<button[^>]*>', 6),
            (r'<a\s+href=', 8),
            (r'<img[^>]*>', 6),
            
            # HTML5 semantic elements
            (r'<header[^>]*>|<footer[^>]*>|<nav[^>]*>|<section[^>]*>|<article[^>]*>', 10),
            (r'<aside[^>]*>|<main[^>]*>|<figure[^>]*>|<figcaption[^>]*>', 8),
            
            # HTML attributes
            (r'\bclass\s*=\s*["\'][^"\']*["\']', 6),
            (r'\bid\s*=\s*["\'][^"\']*["\']', 6),
            (r'\bstyle\s*=\s*["\'][^"\']*["\']', 6),
            (r'\bonclick\s*=|onload\s*=|onchange\s*=', 5),
            
            # Comments
            (r'<!--.*?-->', 3)
        ]
    
    @staticmethod
    def get_css_detection_patterns() -> List[Tuple[str, int]]:
        """Get regex patterns for CSS detection with weights."""
        return [
            # CSS selectors
            (r'\.[a-zA-Z_][a-zA-Z0-9_-]*\s*{', 15),  # Class selectors
            (r'#[a-zA-Z_][a-zA-Z0-9_-]*\s*{', 15),   # ID selectors
            (r'[a-zA-Z][a-zA-Z0-9]*\s*{', 10),       # Element selectors
            (r'\[[a-zA-Z][a-zA-Z0-9_-]*[=~|^$*]*[^}]*\]\s*{', 12),  # Attribute selectors
            (r'::?[a-zA-Z][a-zA-Z0-9_-]*\s*{', 10),  # Pseudo selectors
            
            # CSS properties (common ones)
            (r'\bcolor\s*:', 8),
            (r'\bbackground\s*:', 8),
            (r'\bfont-\w+\s*:', 8),
            (r'\bmargin\s*:|padding\s*:', 8),
            (r'\bwidth\s*:|height\s*:', 8),
            (r'\bdisplay\s*:', 8),
            (r'\bposition\s*:', 6),
            (r'\bborder\s*:', 6),
            (r'\btext-\w+\s*:', 6),
            (r'\bz-index\s*:', 5),
            (r'\bopacity\s*:', 5),
            (r'\btransform\s*:|transition\s*:', 6),
            (r'\bflex\s*:|grid\s*:', 8),
            
            # CSS values and units
            (r'\b\d+px\b|\b\d+em\b|\b\d+rem\b|\b\d+%\b', 6),
            (r'\b#[0-9a-fA-F]{3,6}\b', 8),  # Hex colors
            (r'\brgb\s*\(|\brgba\s*\(', 8),
            (r'\bhsl\s*\(|\bhsla\s*\(', 6),
            
            # CSS at-rules
            (r'@import\s+', 10),
            (r'@media\s+', 12),
            (r'@keyframes\s+', 10),
            (r'@font-face\s*{', 8),
            (r'@charset\s+', 6),
            
            # CSS comments
            (r'/\*.*?\*/', 3)
        ]
    
    @staticmethod
    def get_javascript_detection_patterns() -> List[Tuple[str, int]]:
        """Get regex patterns for JavaScript detection with weights."""
        return [
            # JavaScript keywords
            (r'\bvar\s+\w+', 12),
            (r'\blet\s+\w+', 15),
            (r'\bconst\s+\w+', 15),
            (r'\bfunction\s+\w+\s*\(', 15),
            (r'\bclass\s+\w+', 12),
            (r'\bextends\s+\w+', 10),
            (r'\bimport\s+.*?\bfrom\b', 15),
            (r'\bexport\s+', 12),
            (r'\brequire\s*\(', 12),
            (r'\bmodule\.exports\s*=', 10),
            
            # JavaScript syntax
            (r'=>\s*{', 12),  # Arrow functions
            (r'\b\w+\s*=>\s*', 10),
            (r'\basync\s+function', 12),
            (r'\bawait\s+', 10),
            (r'\bnew\s+\w+\s*\(', 10),
            (r'\bthis\.\w+', 8),
            (r'\bprototype\.\w+', 8),
            
            # JavaScript built-ins
            (r'\bconsole\.(log|error|warn|info)', 12),
            (r'\bdocument\.(getElementById|querySelector)', 12),
            (r'\bwindow\.\w+', 8),
            (r'\bJSON\.(parse|stringify)', 10),
            (r'\bsetTimeout\s*\(|setInterval\s*\(', 8),
            (r'\bPromise\s*\(|\.then\s*\(|\.catch\s*\(', 10),
            
            # DOM manipulation
            (r'\baddEventListener\s*\(', 10),
            (r'\bremoveEventListener\s*\(', 8),
            (r'\.innerHTML\s*=|\.textContent\s*=', 8),
            (r'\.appendChild\s*\(|\.removeChild\s*\(', 6),
            (r'\.createElement\s*\(', 8),
            
            # JavaScript operators and syntax
            (r'===|!==', 8),
            (r'\?\?\?|\?\?', 6),  # Nullish coalescing
            (r'\?\.\w+', 8),      # Optional chaining
            (r'`[^`]*\${[^}]*}[^`]*`', 10),  # Template literals
            
            # Comments
            (r'//.*', 3),
            (r'/\*.*?\*/', 3)
        ]
    
    @staticmethod
    def get_jsp_detection_patterns() -> List[Tuple[str, int]]:
        """Get regex patterns for JSP detection with weights."""
        return [
            # JSP directives
            (r'<%@\s*page\s+', 20),
            (r'<%@\s*include\s+', 15),
            (r'<%@\s*taglib\s+', 18),
            (r'<%@\s*attribute\s+', 12),
            (r'<%@\s*variable\s+', 10),
            (r'<%@\s*tag\s+', 12),
            
            # JSP scriptlets and expressions
            (r'<%[^@].*?%>', 18),  # Scriptlets
            (r'<%=.*?%>', 15),     # Expressions
            (r'<%!.*?%>', 12),     # Declarations
            
            # JSP actions
            (r'<jsp:include\s+', 15),
            (r'<jsp:forward\s+', 12),
            (r'<jsp:useBean\s+', 15),
            (r'<jsp:setProperty\s+', 12),
            (r'<jsp:getProperty\s+', 12),
            (r'<jsp:param\s+', 8),
            (r'<jsp:plugin\s+', 6),
            
            # JSP EL (Expression Language)
            (r'\${[^}]+}', 15),
            (r'#{[^}]+}', 12),
            
            # JSTL tags
            (r'<c:if\s+', 12),
            (r'<c:choose\s*>|<c:when\s+|<c:otherwise\s*>', 10),
            (r'<c:forEach\s+', 12),
            (r'<c:forTokens\s+', 8),
            (r'<c:set\s+', 10),
            (r'<c:out\s+', 10),
            (r'<c:url\s+', 8),
            (r'<c:redirect\s+', 6),
            (r'<c:import\s+', 8),
            
            # Format tags
            (r'<fmt:formatDate\s+', 8),
            (r'<fmt:formatNumber\s+', 8),
            (r'<fmt:message\s+', 8),
            (r'<fmt:setLocale\s+', 6),
            
            # SQL tags
            (r'<sql:query\s+', 8),
            (r'<sql:update\s+', 6),
            (r'<sql:setDataSource\s+', 6),
            
            # XML tags
            (r'<x:parse\s+', 6),
            (r'<x:out\s+', 6),
            (r'<x:forEach\s+', 6),
            
            # Function tags
            (r'<fn:\w+\s*\(', 8)
        ]
    
    @staticmethod
    def get_jsf_detection_patterns() -> List[Tuple[str, int]]:
        """Get regex patterns for JSF detection with weights."""
        return [
            # JSF namespaces
            (r'xmlns:h\s*=\s*["\']http://java\.sun\.com/jsf/html["\']', 20),
            (r'xmlns:f\s*=\s*["\']http://java\.sun\.com/jsf/core["\']', 18),
            (r'xmlns:ui\s*=\s*["\']http://java\.sun\.com/jsf/facelets["\']', 15),
            (r'xmlns:p\s*=\s*["\']http://primefaces\.org/ui["\']', 15),
            (r'xmlns:rich\s*=\s*["\']http://richfaces\.org/rich["\']', 12),
            (r'xmlns:a4j\s*=\s*["\']http://richfaces\.org/a4j["\']', 10),
            
            # JSF core tags
            (r'<f:view\s*>', 18),
            (r'<f:viewParam\s+', 12),
            (r'<f:metadata\s*>', 10),
            (r'<f:event\s+', 8),
            (r'<f:ajax\s+', 12),
            (r'<f:validateLength\s+', 8),
            (r'<f:validateRequired\s+', 8),
            (r'<f:converter\s+', 8),
            (r'<f:selectItem\s+', 8),
            (r'<f:selectItems\s+', 8),
            
            # JSF HTML tags
            (r'<h:form\s+', 18),
            (r'<h:inputText\s+', 15),
            (r'<h:inputSecret\s+', 12),
            (r'<h:inputTextarea\s+', 10),
            (r'<h:inputHidden\s+', 8),
            (r'<h:selectOneMenu\s+', 12),
            (r'<h:selectOneRadio\s+', 10),
            (r'<h:selectBooleanCheckbox\s+', 10),
            (r'<h:commandButton\s+', 15),
            (r'<h:commandLink\s+', 12),
            (r'<h:outputText\s+', 12),
            (r'<h:outputLabel\s+', 10),
            (r'<h:dataTable\s+', 15),
            (r'<h:column\s+', 10),
            (r'<h:messages\s+', 10),
            (r'<h:message\s+', 8),
            (r'<h:panelGrid\s+', 12),
            (r'<h:panelGroup\s+', 10),
            
            # Facelets tags
            (r'<ui:composition\s+', 15),
            (r'<ui:define\s+', 12),
            (r'<ui:insert\s+', 12),
            (r'<ui:include\s+', 12),
            (r'<ui:decorate\s+', 10),
            (r'<ui:fragment\s+', 8),
            (r'<ui:repeat\s+', 10),
            
            # PrimeFaces tags (popular JSF library)
            (r'<p:inputText\s+', 12),
            (r'<p:commandButton\s+', 12),
            (r'<p:dataTable\s+', 15),
            (r'<p:dialog\s+', 10),
            (r'<p:calendar\s+', 8),
            (r'<p:selectOneMenu\s+', 8),
            (r'<p:panel\s+', 8),
            (r'<p:tabView\s+', 8),
            (r'<p:accordion\s+', 6),
            
            # JSF EL expressions
            (r'#{[^}]+\.action[^}]*}', 12),
            (r'#{[^}]+\.value[^}]*}', 10),
            (r'#{[^}]+Bean[^}]*}', 10)
        ]
    
    @staticmethod
    def get_framework_indicators() -> Dict[str, List[Tuple[str, int]]]:
        """Get web framework detection patterns."""
        return {
            'react': [
                (r'import\s+React\s+from\s+["\']react["\']', 20),
                (r'from\s+["\']react["\']', 15),
                (r'React\.Component', 15),
                (r'React\.createElement', 12),
                (r'useState\s*\(|useEffect\s*\(|useContext\s*\(', 15),
                (r'ReactDOM\.render', 12),
                (r'<\w+[^>]*jsx[^>]*>', 8),
                (r'className\s*=', 10)
            ],
            'angular': [
                (r'@Component\s*\(', 20),
                (r'@Injectable\s*\(', 15),
                (r'@NgModule\s*\(', 18),
                (r'@Directive\s*\(', 12),
                (r'@Pipe\s*\(', 10),
                (r'import\s+.*?\s+from\s+["\']@angular/', 15),
                (r'\*ngFor\s*=|ngIf\s*=|\*ngIf\s*=', 12),
                (r'\(click\)\s*=|\(change\)\s*=', 10),
                (r'\[\w+\]\s*=|\(\w+\)\s*=', 8)
            ],
            'vue': [
                (r'<template[^>]*>', 20),
                (r'<script[^>]*>.*?export\s+default', 18),
                (r'Vue\.component\s*\(', 15),
                (r'new Vue\s*\(', 15),
                (r'v-if\s*=|v-for\s*=|v-model\s*=', 15),
                (r'@click\s*=|@change\s*=', 10),
                (r':class\s*=|:style\s*=', 8),
                (r'import\s+Vue\s+from\s+["\']vue["\']', 15)
            ],
            'jquery': [
                (r'\$\s*\(', 15),
                (r'jQuery\s*\(', 15),
                (r'\.ready\s*\(', 12),
                (r'\.click\s*\(|\.change\s*\(|\.submit\s*\(', 10),
                (r'\.hide\s*\(|\.show\s*\(|\.toggle\s*\(', 8),
                (r'\.ajax\s*\(|\.get\s*\(|\.post\s*\(', 10),
                (r'\.addClass\s*\(|\.removeClass\s*\(', 8)
            ],
            'bootstrap': [
                (r'\bbootstrap\b', 8),
                (r'\bbtn\s+btn-', 10),
                (r'\bcontainer\b|\brow\b|\bcol-', 12),
                (r'\bnavbar\b|\bnav-', 8),
                (r'\bmodal\b|\bmodal-', 8),
                (r'\bform-control\b|\bform-group\b', 8),
                (r'\btable\s+table-', 6),
                (r'\balert\s+alert-', 6)
            ],
            'spring_mvc': [
                (r'@Controller\s*$|@RestController\s*$', 20),
                (r'@RequestMapping\s*\(', 18),
                (r'@GetMapping\s*\(|@PostMapping\s*\(', 15),
                (r'@PathVariable\s+|@RequestParam\s+', 12),
                (r'@ModelAttribute\s+|@SessionAttribute\s+', 10),
                (r'ModelAndView\s+', 12),
                (r'@ResponseBody\s*$', 10),
                (r'HttpServletRequest\s+|HttpServletResponse\s+', 8)
            ],
            'struts': [
                (r'<action\s+', 15),
                (r'struts-config\.xml|struts\.xml', 18),
                (r'ActionForm\s+|ActionForward\s+', 15),
                (r'ActionMapping\s+|ActionErrors\s+', 12),
                (r'<form-bean\s+', 12),
                (r'<forward\s+', 10),
                (r'<result\s+', 10),
                (r'extends\s+Action\b', 15)
            ]
        }
    
    @staticmethod
    def detect_web_framework(content: str, file_extension: Optional[str] = None) -> Dict[str, Any]:
        """Detect web framework based on content patterns."""
        framework_scores = {}
        
        frameworks = WebDetectionRules.get_framework_indicators()
        
        for framework, patterns in frameworks.items():
            score = 0
            for pattern, weight in patterns:
                matches = len(re.findall(pattern, content, re.IGNORECASE | re.MULTILINE))
                score += matches * weight
            framework_scores[framework] = score
        
        # Find best match
        best_framework = max(framework_scores.keys(), key=lambda k: framework_scores[k])
        best_score = framework_scores[best_framework]
        
        return {
            'detected_framework': best_framework if best_score > 0 else None,
            'confidence': min(best_score / 50, 1.0),  # Normalize to 0-1
            'scores': framework_scores
        }
    
    @staticmethod
    def extract_css_selectors(content: str) -> Dict[str, List[str]]:
        """Extract CSS selectors from content."""
        selectors: Dict[str, List[str]] = {
            'class': [],
            'id': [],
            'element': [],
            'attribute': [],
            'pseudo': []
        }
        
        # Class selectors
        class_matches = re.findall(r'\.([a-zA-Z_][a-zA-Z0-9_-]*)', content)
        selectors['class'] = list(set(class_matches))
        
        # ID selectors
        id_matches = re.findall(r'#([a-zA-Z_][a-zA-Z0-9_-]*)', content)
        selectors['id'] = list(set(id_matches))
        
        # Element selectors (basic)
        element_matches = re.findall(r'^([a-zA-Z][a-zA-Z0-9]*)\s*{', content, re.MULTILINE)
        selectors['element'] = list(set(element_matches))
        
        # Attribute selectors
        attr_matches = re.findall(r'\[([a-zA-Z][a-zA-Z0-9_-]*)', content)
        selectors['attribute'] = list(set(attr_matches))
        
        # Pseudo selectors
        pseudo_matches = re.findall(r'::?([a-zA-Z][a-zA-Z0-9_-]*)', content)
        selectors['pseudo'] = list(set(pseudo_matches))
        
        return selectors
    
    @staticmethod
    def extract_javascript_functions(content: str) -> List[str]:
        """Extract JavaScript function names from content."""
        functions = set()
        
        # Function declarations
        func_decl = re.findall(r'\bfunction\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(', content)
        functions.update(func_decl)
        
        # Function expressions
        func_expr = re.findall(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*function\s*\(', content)
        functions.update(func_expr)
        
        # Arrow functions
        arrow_func = re.findall(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*\([^)]*\)\s*=>', content)
        functions.update(arrow_func)
        
        # Method definitions in classes/objects
        method_def = re.findall(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*{', content)
        functions.update(method_def)
        
        return list(functions)
    
    @staticmethod
    def detect_web_technologies(content: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Comprehensive web technology detection."""
        result: Dict[str, Union[int, str, List[str], float, None]] = {
            'html_score': 0,
            'css_score': 0,
            'javascript_score': 0,
            'jsp_score': 0,
            'jsf_score': 0,
            'primary_technology': None,
            'technologies': [],
            'framework': None,
            'confidence': 0.0
        }
        
        # Score each technology
        html_score = result['html_score']
        css_score = result['css_score']
        javascript_score = result['javascript_score']
        jsp_score = result['jsp_score']
        jsf_score = result['jsf_score']
        
        # Type assertions for mypy
        assert isinstance(html_score, int)
        assert isinstance(css_score, int)
        assert isinstance(javascript_score, int)
        assert isinstance(jsp_score, int)
        assert isinstance(jsf_score, int)
        
        for pattern, weight in WebDetectionRules.get_html_detection_patterns():
            matches = len(re.findall(pattern, content, re.IGNORECASE | re.DOTALL))
            html_score += matches * weight
        result['html_score'] = html_score
        
        for pattern, weight in WebDetectionRules.get_css_detection_patterns():
            matches = len(re.findall(pattern, content, re.IGNORECASE | re.DOTALL))
            css_score += matches * weight
        result['css_score'] = css_score
        
        for pattern, weight in WebDetectionRules.get_javascript_detection_patterns():
            matches = len(re.findall(pattern, content, re.IGNORECASE | re.DOTALL))
            javascript_score += matches * weight
        result['javascript_score'] = javascript_score
        
        for pattern, weight in WebDetectionRules.get_jsp_detection_patterns():
            matches = len(re.findall(pattern, content, re.IGNORECASE | re.DOTALL))
            jsp_score += matches * weight
        result['jsp_score'] = jsp_score
        
        for pattern, weight in WebDetectionRules.get_jsf_detection_patterns():
            matches = len(re.findall(pattern, content, re.IGNORECASE | re.DOTALL))
            jsf_score += matches * weight
        result['jsf_score'] = jsf_score
        
        # Determine primary technology
        scores: Dict[str, int] = {
            'html': html_score,
            'css': css_score,
            'javascript': javascript_score,
            'jsp': jsp_score,
            'jsf': jsf_score
        }
        
        primary_tech = max(scores.keys(), key=lambda k: scores[k])
        result['primary_technology'] = primary_tech
        result['confidence'] = min(scores[primary_tech] / 100, 1.0)
        
        # Collect detected technologies (score > 0)
        detected_technologies = [tech for tech, score in scores.items() if score > 0]
        result['technologies'] = detected_technologies
        
        # Detect framework
        framework_result = WebDetectionRules.detect_web_framework(content, filename)
        result['framework'] = framework_result['detected_framework']
        
        return result
