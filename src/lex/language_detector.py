"""Content-based language identification."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import Config
from config.exceptions import ConfigurationError
from utils.logging.logger_factory import LoggerFactory


class LanguageDetector:
    """
    Content-based programming language detection.
    
    Uses pattern matching and statistical analysis to identify
    programming languages when file extensions are ambiguous.
    """
    
    def __init__(self, config: Optional[Config] = None) -> None:
        """Initialize language detector with configuration."""
        try:
            self.config = config if config is not None else Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"Failed to initialize language detector: {e}") from e
        self.logger = LoggerFactory.get_logger(__name__)
        self._initialize_patterns()
    
    def _initialize_patterns(self) -> None:
        """Initialize language detection patterns."""
        # Java language patterns
        self.java_patterns = [
            (r'\bpublic\s+class\s+\w+', 15),
            (r'\bprivate\s+\w+\s+\w+\s*\(', 10),
            (r'\bprotected\s+\w+\s+\w+\s*\(', 10),
            (r'\bpublic\s+static\s+void\s+main', 20),
            (r'@Override|@Deprecated|@SuppressWarnings', 15),
            (r'@Path|@GET|@POST|@PUT|@DELETE', 15),  # JAX-RS annotations
            (r'@Entity|@Table|@Column|@Id', 15),     # JPA annotations
            (r'@Component|@Service|@Repository|@Controller', 15),  # Spring annotations
            (r'\bimport\s+java\.', 12),
            (r'\bimport\s+javax\.', 12),
            (r'\bimport\s+org\.', 8),
            (r'\bpackage\s+[\w.]+;', 12),
            (r'\bSystem\.out\.println', 8),
            (r'\bnew\s+\w+\s*\(', 5),
            (r'\bthrows\s+\w+Exception', 8),
            (r'\bpublic\s+\w+\s+\w+\s*\(', 8),
            (r'\bextends\s+\w+', 8),
            (r'\bimplements\s+\w+', 8),
            (r'\bResourceConfig\b', 10),  # Jersey specific
            (r'\bMediaType\.\w+', 8),     # JAX-RS MediaType
            (r'\bResponse\.', 8)          # JAX-RS Response
        ]
        
        # JSP patterns
        self.jsp_patterns = [
            (r'<%@\s*page\s+', 15),
            (r'<%@\s*taglib\s+', 12),
            (r'<%=\s*.*?\s*%>', 10),
            (r'<%\s*.*?\s*%>', 8),
            (r'<jsp:\w+', 12),
            (r'<c:\w+|<fmt:\w+|<fn:\w+', 10),
            (r'\$\{.*?\}', 8),
            (r'request\.getParameter', 5),
            (r'session\.getAttribute', 5),
            (r'pageContext\.\w+', 5)
        ]
        
        # JavaScript patterns
        self.javascript_patterns = [
            (r'\bfunction\s+\w+\s*\(', 8),
            (r'\bvar\s+\w+\s*=', 5),
            (r'\blet\s+\w+\s*=', 6),
            (r'\bconst\s+\w+\s*=', 6),
            (r'\bdocument\.\w+', 8),
            (r'\bwindow\.\w+', 6),
            (r'\bconsole\.log', 5),
            (r'=>\s*\{', 4),
            (r'\brequire\s*\(', 6),
            (r'\bimport\s+.*?\bfrom\b', 6)
        ]
        
        # SQL patterns
        self.sql_patterns = [
            (r'\bSELECT\s+.*?\bFROM\b', 10),
            (r'\bINSERT\s+INTO\b', 10),
            (r'\bUPDATE\s+.*?\bSET\b', 10),
            (r'\bDELETE\s+FROM\b', 10),
            (r'\bCREATE\s+TABLE\b', 12),
            (r'\bALTER\s+TABLE\b', 8),
            (r'\bDROP\s+TABLE\b', 8),
            (r'\bWHERE\s+', 5),
            (r'\bJOIN\s+.*?\bON\b', 6),
            (r'\bGROUP\s+BY\b|\bORDER\s+BY\b', 5)
        ]
        
        # XML patterns
        self.xml_patterns = [
            (r'<\?xml\s+version', 15),
            (r'<!DOCTYPE\s+\w+', 10),
            (r'<\w+:\w+', 8),
            (r'xmlns:\w+\s*=', 10),
            (r'<!\[CDATA\[', 8),
            (r'</\w+>', 3)
        ]
        
        # HTML patterns
        self.html_patterns = [
            (r'<!DOCTYPE\s+html', 15),
            (r'<html\s*>', 12),
            (r'<head\s*>|<body\s*>', 10),
            (r'<div\s+|<span\s+|<p\s+', 5),
            (r'<script\s+.*?>', 8),
            (r'<style\s+.*?>', 8),
            (r'<link\s+.*?>', 6),
            (r'<meta\s+.*?>', 6)
        ]
        
        # CSS patterns
        self.css_patterns = [
            (r'\.\w+\s*\{', 8),
            (r'#\w+\s*\{', 8),
            (r'\w+\s*:\s*\w+\s*;', 5),
            (r'@media\s+', 8),
            (r'@import\s+', 6),
            (r'@font-face\s*\{', 8),
            (r':hover|:focus|:active', 5)
        ]
        
        # Python patterns
        self.python_patterns = [
            (r'\bdef\s+\w+\s*\(', 10),
            (r'\bclass\s+\w+\s*\(', 10),
            (r'\bimport\s+\w+', 8),
            (r'\bfrom\s+\w+\s+import', 8),
            (r'\bif\s+__name__\s*==\s*["\']__main__["\']', 15),
            (r'\bprint\s*\(', 5),
            (r'\bself\.\w+', 6),
            (r'\breturn\s+\w+', 3)
        ]
        
        # VBScript patterns
        self.vbscript_patterns = [
            (r'\bSub\s+\w+\s*\(', 12),
            (r'\bFunction\s+\w+\s*\(', 12),
            (r'\bDim\s+\w+\s+As\s+\w+', 10),
            (r'\bDim\s+\w+', 8),
            (r'\bSet\s+\w+\s*=', 8),
            (r'\bEnd\s+Sub\b|\bEnd\s+Function\b', 10),
            (r'\bIf\s+.*?\bThen\b', 6),
            (r'\bFor\s+\w+\s*=.*?\bTo\b', 8),
            (r'\bMsgBox\s*\(', 8),
            (r'\bDocument\.\w+', 6),
            (r'\bWindow\.\w+', 6),
            (r'LANGUAGE\s*=\s*["\']?VBScript["\']?', 15)
        ]
        
        # Combine all patterns
        self.language_patterns = {
            'java': self.java_patterns,
            'jsp': self.jsp_patterns,
            'javascript': self.javascript_patterns,
            'sql': self.sql_patterns,
            'xml': self.xml_patterns,
            'html': self.html_patterns,
            'css': self.css_patterns,
            'python': self.python_patterns,
            'vbscript': self.vbscript_patterns
        }
        
        # Keywords for each language
        self.language_keywords = {
            'java': ['public', 'private', 'protected', 'class', 'interface', 'extends', 'implements', 
                    'import', 'package', 'static', 'final', 'abstract', 'synchronized', 'throws'],
            'jsp': ['page', 'taglib', 'include', 'forward', 'param', 'request', 'response', 'session'],
            'javascript': ['function', 'var', 'let', 'const', 'return', 'if', 'else', 'for', 'while', 
                          'document', 'window', 'console'],
            'sql': ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'FROM', 'WHERE', 
                   'JOIN', 'GROUP', 'ORDER', 'BY'],
            'xml': ['version', 'encoding', 'DOCTYPE', 'xmlns', 'CDATA'],
            'html': ['html', 'head', 'body', 'div', 'span', 'script', 'style', 'meta', 'link'],
            'css': ['color', 'background', 'margin', 'padding', 'border', 'font', 'display'],
            'python': ['def', 'class', 'import', 'from', 'if', 'else', 'elif', 'for', 'while', 'return', 'print'],
            'vbscript': ['Sub', 'Function', 'Dim', 'Set', 'If', 'Then', 'Else', 'ElseIf', 'End', 'For', 'To', 
                        'While', 'Do', 'Loop', 'Select', 'Case', 'MsgBox', 'InputBox', 'Document', 'Window']
        }
    
    def detect_language(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect programming language based on file content.
        
        Args:
            file_path: Path to the file
            content: File content (if not provided, will read from file)
            
        Returns:
            Dictionary with detection results
        """
        try:
            if content is None:
                content = self._read_file_content(file_path)
            
            if not content:
                return {
                    'file_path': file_path,
                    'detected_language': None,
                    'confidence': 0.0,
                    'scores': {},
                    'error': 'No content to analyze'
                }
            
            # Calculate scores for each language
            scores = {}
            for language, patterns in self.language_patterns.items():
                scores[language] = self._calculate_language_score(content, patterns, language)
            
            # Find the language with highest score
            best_language: Optional[str] = None
            confidence = 0.0
            if scores:
                best_language = max(scores.keys(), key=lambda k: scores[k])
                best_score = scores[best_language]
                
                # Calculate confidence (normalize score)
                if best_language is not None:
                    max_possible_score = sum(weight for _, weight in self.language_patterns[best_language])
                    # Use a more realistic confidence calculation for small code samples
                    # Add bonus for having any matches at all
                    base_confidence = min(best_score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
                    
                    # Boost confidence if we have strong patterns
                    if best_score > 20:  # Strong pattern matches
                        confidence = min(base_confidence + 0.3, 1.0)
                    elif best_score > 10:  # Moderate pattern matches
                        confidence = min(base_confidence + 0.2, 1.0)
                    else:
                        confidence = base_confidence
                    
                    # Minimum confidence threshold
                    if confidence < 0.1:
                        best_language = None
                        confidence = 0.0
            
            return {
                'file_path': file_path,
                'detected_language': best_language,
                'confidence': confidence,
                'scores': scores,
                'content_length': len(content)
            }
            
        except (OSError, IOError, UnicodeDecodeError, ValueError) as e:
            self.logger.error("Failed to detect language for %s: %s", file_path, e)
            return {
                'file_path': file_path,
                'detected_language': None,
                'confidence': 0.0,
                'scores': {},
                'error': str(e)
            }
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content with encoding detection."""
        try:
            # Try UTF-8 first
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                # Try latin-1 as fallback
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except (OSError, IOError) as e:
                self.logger.warning("Failed to read %s: %s", file_path, e)
                return None
        except (OSError, IOError) as e:
            self.logger.warning("Failed to read %s: %s", file_path, e)
            return None
    
    def _calculate_language_score(self, content: str, patterns: List[Tuple[str, int]], language: str) -> float:
        """Calculate score for a specific language."""
        score = 0.0
        
        # Pattern matching score
        for pattern, weight in patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE | re.MULTILINE))
            score += matches * weight
        
        # Keyword frequency score
        keywords = self.language_keywords.get(language, [])
        for keyword in keywords:
            # Count keyword occurrences (case insensitive for most languages)
            if language in ['sql']:
                # SQL keywords are typically uppercase
                keyword_pattern = r'\b' + re.escape(keyword.upper()) + r'\b'
            else:
                keyword_pattern = r'\b' + re.escape(keyword) + r'\b'
            
            matches = len(re.findall(keyword_pattern, content, re.IGNORECASE))
            score += matches * 2  # Weight for keywords
        
        return score
    
    def detect_language_by_extension(self, file_path: str) -> Optional[str]:
        """Get language based on file extension."""
        extension_map = {
            '.java': 'java',
            '.jsp': 'jsp',
            '.jspx': 'jsp',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.sql': 'sql',
            '.xml': 'xml',
            '.html': 'html',
            '.htm': 'html',
            '.xhtml': 'html',
            '.css': 'css',
            '.scss': 'css',
            '.sass': 'css',
            '.py': 'python',
            '.rb': 'ruby',
            '.php': 'php',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.kt': 'kotlin'
        }
        
        ext = Path(file_path).suffix.lower()
        return extension_map.get(ext)
    
    def is_mixed_language_file(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect if file contains multiple programming languages.
        
        Useful for JSP files with embedded Java, HTML with inline JavaScript, etc.
        """
        try:
            if content is None:
                content = self._read_file_content(file_path)
            
            if not content:
                return {'is_mixed': False, 'languages': []}
            
            # Calculate scores for all languages
            language_scores = {}
            for language, patterns in self.language_patterns.items():
                score = self._calculate_language_score(content, patterns, language)
                if score > 0:
                    language_scores[language] = score
            
            # Consider it mixed if more than one language has significant score
            significant_languages = []
            for language, score in language_scores.items():
                max_possible = sum(weight for _, weight in self.language_patterns[language])
                confidence = score / max_possible if max_possible > 0 else 0
                if confidence > 0.15:  # 15% confidence threshold
                    significant_languages.append({
                        'language': language,
                        'score': score,
                        'confidence': confidence
                    })
            
            is_mixed = len(significant_languages) > 1
            
            return {
                'file_path': file_path,
                'is_mixed': is_mixed,
                'languages': significant_languages,
                'total_languages_detected': len(significant_languages)
            }
            
        except (OSError, IOError, UnicodeDecodeError, ValueError) as e:
            self.logger.error("Failed to detect mixed languages for %s: %s", file_path, e)
            return {
                'file_path': file_path,
                'is_mixed': False,
                'languages': [],
                'error': str(e)
            }
    
    def detect_framework_indicators(self, content: str) -> List[str]:
        """Detect framework indicators in content."""
        indicators = []
        
        # Spring indicators
        spring_patterns = [
            r'@Controller|@RestController',
            r'@Service',
            r'@Repository',
            r'@Component',
            r'@Autowired',
            r'@RequestMapping',
            r'@GetMapping|@PostMapping',
            r'org\.springframework\.'
        ]
        
        for pattern in spring_patterns:
            if re.search(pattern, content):
                indicators.append('spring')
                break
        
        # Hibernate indicators
        hibernate_patterns = [
            r'@Entity',
            r'@Table',
            r'@Column',
            r'@Id',
            r'@GeneratedValue',
            r'org\.hibernate\.',
            r'javax\.persistence\.'
        ]
        
        for pattern in hibernate_patterns:
            if re.search(pattern, content):
                indicators.append('hibernate')
                break
        
        # Struts indicators
        struts_patterns = [
            r'org\.apache\.struts',
            r'ActionSupport',
            r'Action\s*\{',
            r'<action\s+',
            r'struts\.xml'
        ]
        
        for pattern in struts_patterns:
            if re.search(pattern, content):
                indicators.append('struts')
                break
        
        # JSP/JSTL indicators
        jsp_patterns = [
            r'<%@\s*page',
            r'<%@\s*taglib',
            r'<jsp:',
            r'<c:|<fmt:|<fn:'
        ]
        
        for pattern in jsp_patterns:
            if re.search(pattern, content):
                indicators.append('jsp')
                break
        
        return indicators
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages for detection."""
        return list(self.language_patterns.keys())
