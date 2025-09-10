"""Pre-parsing syntax validation for source files."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config
from config.exceptions import ConfigurationError
from utils.logging.logger_factory import LoggerFactory


class SyntaxValidator:
    """
    Pre-parsing syntax validation to detect obviously malformed files.
    
    Performs lightweight syntax checks before sending files to
    full parsers to avoid parsing errors and improve performance.
    """
    
    def __init__(self, config: Optional[Config] = None) -> None:
        """Initialize syntax validator with configuration."""
        try:
            self.config = config if config is not None else Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"Failed to initialize syntax validator: {e}") from e
        self.logger = LoggerFactory.get_logger(__name__)
        self._initialize_validators()
    
    def _initialize_validators(self) -> None:
        """Initialize syntax validation patterns."""
        # Java syntax patterns
        self.java_validators = [
            ('balanced_braces', self._check_balanced_braces),
            ('balanced_parentheses', self._check_balanced_parentheses),
            ('package_syntax', self._check_java_package_syntax),
            ('import_syntax', self._check_java_import_syntax),
            ('class_declaration', self._check_java_class_syntax),
            ('string_literals', self._check_string_literals)
        ]
        
        # JSP syntax patterns
        self.jsp_validators = [
            ('jsp_tags', self._check_jsp_tag_syntax),
            ('scriptlet_syntax', self._check_jsp_scriptlet_syntax),
            ('expression_syntax', self._check_jsp_expression_syntax),
            ('directive_syntax', self._check_jsp_directive_syntax),
            ('el_syntax', self._check_jsp_el_syntax)
        ]
        
        # XML syntax patterns
        self.xml_validators = [
            ('xml_declaration', self._check_xml_declaration),
            ('balanced_tags', self._check_xml_balanced_tags),
            ('attribute_syntax', self._check_xml_attribute_syntax),
            ('namespace_syntax', self._check_xml_namespace_syntax)
        ]
        
        # JavaScript syntax patterns
        self.javascript_validators = [
            ('balanced_braces', self._check_balanced_braces),
            ('balanced_parentheses', self._check_balanced_parentheses),
            ('function_syntax', self._check_javascript_function_syntax),
            ('string_literals', self._check_string_literals)
        ]
        
        # SQL syntax patterns
        self.sql_validators = [
            ('statement_termination', self._check_sql_statement_syntax),
            ('quoted_identifiers', self._check_sql_quoted_identifiers),
            ('comment_syntax', self._check_sql_comment_syntax)
        ]
        
        # VBScript syntax patterns
        self.vbscript_validators = [
            ('sub_function_syntax', self._check_vbscript_sub_function_syntax),
            ('balanced_parentheses', self._check_balanced_parentheses),
            ('end_statements', self._check_vbscript_end_statements),
            ('string_literals', self._check_string_literals)
        ]
        
        # Language validator mapping
        self.language_validators = {
            'java': self.java_validators,
            'jsp': self.jsp_validators,
            'xml': self.xml_validators,
            'javascript': self.javascript_validators,
            'sql': self.sql_validators,
            'vbscript': self.vbscript_validators
        }
    
    def validate_syntax(self, file_path: str, content: Optional[str] = None, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate syntax of a source file.
        
        Args:
            file_path: Path to the file
            content: File content (if not provided, will read from file)
            language: Programming language (if not provided, will detect)
            
        Returns:
            Dictionary with validation results
        """
        try:
            if content is None:
                content = self._read_file_content(file_path)
            
            if not content:
                return {
                    'file_path': file_path,
                    'is_valid': True,  # Empty files are considered valid
                    'language': language,
                    'issues': [],
                    'warnings': ['File is empty'],
                    'validation_count': 0
                }
            
            # Auto-detect language if not provided
            if language is None:
                language = self._detect_language_from_extension(file_path)
            
            # Get validators for the language
            validators = self.language_validators.get(language, [])
            
            issues: List[str] = []
            warnings: List[str] = []
            validations: Dict[str, Dict[str, Any]] = {}
            
            # Run all validators
            for validator_name, validator_func in validators:
                try:
                    result = validator_func(content)
                    validations[validator_name] = result
                    if result['issues']:
                        issues.extend(result['issues'])
                    if result.get('warnings'):
                        warnings.extend(result['warnings'])
                except (ValueError, TypeError, RuntimeError) as e:
                    warnings.append(f"Validator {validator_name} failed: {e}")
                    validations[validator_name] = {'issues': [], 'warnings': [f"Failed: {e}"]}
            
            # Overall validation result
            is_valid = len(issues) == 0
            
            return {
                'file_path': file_path,
                'is_valid': is_valid,
                'language': language,
                'issues': issues,
                'warnings': warnings,
                'validations': validations,
                'validation_count': len(validators),
                'content_length': len(content)
            }
            
        except (OSError, IOError, UnicodeDecodeError, ValueError) as e:
            self.logger.error("Failed to validate syntax for %s: %s", file_path, e)
            return {
                'file_path': file_path,
                'is_valid': False,
                'language': language,
                'issues': [f"Validation error: {e}"],
                'warnings': [],
                'validation_count': 0
            }
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content safely."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except (OSError, IOError, UnicodeDecodeError) as e:
            self.logger.warning("Failed to read %s: %s", file_path, e)
            return None
    
    def _detect_language_from_extension(self, file_path: str) -> str:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lower()
        extension_map = {
            '.java': 'java',
            '.jsp': 'jsp',
            '.jspx': 'jsp',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.xml': 'xml',
            '.sql': 'sql',
            '.html': 'xml',
            '.xhtml': 'xml'
        }
        return extension_map.get(ext, 'unknown')
    
    # Generic validators
    def _check_balanced_braces(self, content: str) -> Dict[str, Any]:
        """Check if braces are balanced."""
        brace_count = 0
        issues: List[str] = []
        line_num = 1
        
        in_string = False
        in_char = False
        escape_next = False
        
        for i, char in enumerate(content):
            if char == '\n':
                line_num += 1
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not in_char:
                in_string = not in_string
            elif char == "'" and not in_string:
                in_char = not in_char
            elif not in_string and not in_char:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count < 0:
                        issues.append(f"Unmatched closing brace at line {line_num}")
                        brace_count = 0  # Reset to continue checking
        
        if brace_count > 0:
            issues.append(f"Unmatched opening braces: {brace_count}")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_balanced_parentheses(self, content: str) -> Dict[str, Any]:
        """Check if parentheses are balanced."""
        paren_count = 0
        issues: List[str] = []
        line_num = 1
        
        in_string = False
        in_char = False
        escape_next = False
        
        for char in content:
            if char == '\n':
                line_num += 1
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not in_char:
                in_string = not in_string
            elif char == "'" and not in_string:
                in_char = not in_char
            elif not in_string and not in_char:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count < 0:
                        issues.append(f"Unmatched closing parenthesis at line {line_num}")
                        paren_count = 0
        
        if paren_count > 0:
            issues.append(f"Unmatched opening parentheses: {paren_count}")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_string_literals(self, content: str) -> Dict[str, Any]:
        """Check string literal syntax."""
        issues: List[str] = []
        warnings: List[str] = []
        
        # Check for unterminated strings
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Simple check for unterminated strings
            in_string = False
            escape_next = False
            
            for char in line:
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                elif char == '"':
                    in_string = not in_string
            
            if in_string:
                warnings.append(f"Possible unterminated string at line {i}")
        
        return {'issues': issues, 'warnings': warnings}
    
    # Java-specific validators
    def _check_java_package_syntax(self, content: str) -> Dict[str, Any]:
        """Check Java package declaration syntax."""
        issues: List[str] = []
        
        package_pattern = r'^\s*package\s+([a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*;'
        package_matches = re.findall(package_pattern, content, re.MULTILINE)
        
        if len(package_matches) > 1:
            issues.append("Multiple package declarations found")
        
        # Check for invalid package syntax
        invalid_package = re.search(r'^\s*package\s+[^;]*$', content, re.MULTILINE)
        if invalid_package:
            issues.append("Invalid package declaration syntax")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_java_import_syntax(self, content: str) -> Dict[str, Any]:
        """Check Java import statement syntax."""
        issues: List[str] = []
        
        # Check for malformed import statements
        import_pattern = r'^\s*import\s+(static\s+)?([a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_*][a-zA-Z0-9_]*)*)\s*;'
        import_lines = re.findall(r'^\s*import\s+.*$', content, re.MULTILINE)
        
        for import_line in import_lines:
            if not re.match(import_pattern, import_line):
                issues.append(f"Invalid import syntax: {import_line.strip()}")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_java_class_syntax(self, content: str) -> Dict[str, Any]:
        """Check Java class declaration syntax."""
        issues: List[str] = []
        warnings: List[str] = []
        
        # Check for class declaration
        class_pattern = r'\b(public\s+|private\s+|protected\s+)?(final\s+|abstract\s+)?class\s+\w+'
        class_matches = re.findall(class_pattern, content)
        
        # Check for interface declaration
        interface_pattern = r'\b(public\s+|private\s+|protected\s+)?interface\s+\w+'
        interface_matches = re.findall(interface_pattern, content)
        
        # Check for enum declaration
        enum_pattern = r'\b(public\s+|private\s+|protected\s+)?enum\s+\w+'
        enum_matches = re.findall(enum_pattern, content)
        
        total_declarations = len(class_matches) + len(interface_matches) + len(enum_matches)
        
        if total_declarations == 0:
            warnings.append("No class, interface, or enum declarations found")
        elif total_declarations > 1:
            warnings.append("Multiple top-level type declarations found")
        
        return {'issues': issues, 'warnings': warnings}
    
    # JSP-specific validators
    def _check_jsp_tag_syntax(self, content: str) -> Dict[str, Any]:
        """Check JSP tag syntax."""
        issues: List[str] = []
        
        # Check for malformed JSP tags
        jsp_tag_pattern = r'<jsp:\w+[^>]*>'
        malformed_tags = re.findall(r'<jsp:[^>]*[^/>]$', content, re.MULTILINE)
        
        for tag in malformed_tags:
            issues.append(f"Malformed JSP tag: {tag}")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_jsp_scriptlet_syntax(self, content: str) -> Dict[str, Any]:
        """Check JSP scriptlet syntax."""
        issues = []
        
        # Check for unmatched scriptlet tags (exclude directives and expressions)
        # Scriptlets are <% ... %> but NOT <%@ ... %> (directives) or <%=  ... %> (expressions)
        scriptlet_opens = len(re.findall(r'<%(?![=@])', content))
        # Count all %> closes
        all_closes = len(re.findall(r'%>', content))
        
        # Count directive closes (<%@ ... %>)
        directive_closes = len(re.findall(r'<%@.*?%>', content, re.DOTALL))
        
        # Count expression closes (<%=  ... %>)
        expression_closes = len(re.findall(r'<%=.*?%>', content, re.DOTALL))
        
        # Scriptlet closes = total closes - directive closes - expression closes
        scriptlet_closes = all_closes - directive_closes - expression_closes
        
        if scriptlet_opens != scriptlet_closes:
            issues.append(f"Unmatched scriptlet tags: {scriptlet_opens} opens, {scriptlet_closes} closes")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_jsp_expression_syntax(self, content: str) -> Dict[str, Any]:
        """Check JSP expression syntax."""
        issues = []
        
        # Check for malformed expressions
        expression_pattern = r'<%=.*?%>'
        expressions = re.findall(expression_pattern, content, re.DOTALL)
        
        for expr in expressions:
            if not expr.strip().endswith('%>'):
                issues.append(f"Malformed JSP expression: {expr}")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_jsp_directive_syntax(self, content: str) -> Dict[str, Any]:
        """Check JSP directive syntax."""
        issues = []
        
        # Check for malformed directives
        directive_pattern = r'<%@\s*\w+.*?%>'
        directives = re.findall(directive_pattern, content, re.DOTALL)
        
        for directive in directives:
            if not directive.strip().endswith('%>'):
                issues.append(f"Malformed JSP directive: {directive}")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_jsp_el_syntax(self, content: str) -> Dict[str, Any]:
        """Check JSP EL (Expression Language) syntax."""
        issues = []
        
        # Check for unmatched EL expressions
        el_opens = len(re.findall(r'\$\{', content))
        el_closes = len(re.findall(r'\}', content))
        
        # This is a rough check - not all } are EL closes
        if el_opens > 0 and el_closes < el_opens:
            issues.append("Possible unmatched EL expressions")
        
        return {'issues': issues, 'warnings': []}
    
    # XML-specific validators
    def _check_xml_declaration(self, content: str) -> Dict[str, Any]:
        """Check XML declaration syntax."""
        issues = []
        
        xml_decl_pattern = r'<\?xml\s+version\s*=\s*["\'][^"\']+["\']\s*(encoding\s*=\s*["\'][^"\']+["\']\s*)?(standalone\s*=\s*["\'](?:yes|no)["\']\s*)?\?>'
        xml_declarations = re.findall(r'<\?xml.*?\?>', content)
        
        for decl in xml_declarations:
            if not re.match(xml_decl_pattern, decl):
                issues.append(f"Invalid XML declaration: {decl}")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_xml_balanced_tags(self, content: str) -> Dict[str, Any]:
        """Check if XML tags are balanced."""
        issues: List[str] = []
        
        # This is a simplified check - a full XML parser would be more accurate
        tag_stack: List[str] = []
        
        # Find all tags
        tag_pattern = r'<(/?)(\w+)[^>]*?(/?)>'
        tags = re.findall(tag_pattern, content)
        
        for is_closing, tag_name, is_self_closing in tags:
            if is_self_closing:
                continue  # Self-closing tags
            elif is_closing:
                if not tag_stack or tag_stack[-1] != tag_name:
                    issues.append(f"Unmatched closing tag: </{tag_name}>")
                else:
                    tag_stack.pop()
            else:
                tag_stack.append(tag_name)
        
        if tag_stack:
            issues.append(f"Unclosed tags: {', '.join(tag_stack)}")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_xml_attribute_syntax(self, content: str) -> Dict[str, Any]:
        """Check XML attribute syntax."""
        issues: List[str] = []
        
        # Check for malformed attributes
        malformed_attrs = re.findall(r'\w+\s*=\s*[^"\'>\s]', content)
        
        for attr in malformed_attrs:
            issues.append(f"Malformed attribute (missing quotes): {attr}")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_xml_namespace_syntax(self, content: str) -> Dict[str, Any]:
        """Check XML namespace syntax."""
        issues: List[str] = []
        warnings: List[str] = []
        
        # Check for namespace declarations
        ns_pattern = r'xmlns(?::\w+)?\s*=\s*["\'][^"\']*["\']'
        namespaces = re.findall(ns_pattern, content)
        
        if not namespaces and 'xmlns' in content:
            warnings.append("Possible malformed namespace declarations")
        
        return {'issues': issues, 'warnings': warnings}
    
    # JavaScript-specific validators
    def _check_javascript_function_syntax(self, content: str) -> Dict[str, Any]:
        """Check JavaScript function syntax."""
        issues: List[str] = []
        warnings: List[str] = []
        
        # Check for function declarations
        func_pattern = r'\bfunction\s+\w+\s*\([^)]*\)\s*\{'
        functions = re.findall(func_pattern, content)
        
        # Check for arrow functions
        arrow_pattern = r'\([^)]*\)\s*=>\s*\{'
        arrow_functions = re.findall(arrow_pattern, content)
        
        total_functions = len(functions) + len(arrow_functions)
        
        if total_functions == 0:
            warnings.append("No function declarations found")
        
        return {'issues': issues, 'warnings': warnings}
    
    # SQL-specific validators
    def _check_sql_statement_syntax(self, content: str) -> Dict[str, Any]:
        """Check SQL statement syntax."""
        issues: List[str] = []
        warnings: List[str] = []
        
        # Check for statements without semicolons
        statements = re.split(r';', content)
        for stmt in statements[:-1]:  # Exclude last empty part
            stmt = stmt.strip()
            if stmt and not stmt.endswith(';'):
                sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']
                if any(keyword in stmt.upper() for keyword in sql_keywords):
                    warnings.append("SQL statement may be missing semicolon")
        
        return {'issues': issues, 'warnings': warnings}
    
    def _check_sql_quoted_identifiers(self, content: str) -> Dict[str, Any]:
        """Check SQL quoted identifier syntax."""
        issues: List[str] = []
        
        # Check for unmatched quotes in identifiers
        single_quotes = content.count("'")
        double_quotes = content.count('"')
        
        if single_quotes % 2 != 0:
            issues.append("Unmatched single quotes detected")
        
        if double_quotes % 2 != 0:
            issues.append("Unmatched double quotes detected")
        
        return {'issues': issues, 'warnings': []}
    
    def _check_sql_comment_syntax(self, content: str) -> Dict[str, Any]:
        """Check SQL comment syntax."""
        issues: List[str] = []
        warnings: List[str] = []
        
        # Check for malformed block comments
        block_comment_opens = content.count('/*')
        block_comment_closes = content.count('*/')
        
        if block_comment_opens != block_comment_closes:
            issues.append(f"Unmatched block comments: {block_comment_opens} opens, {block_comment_closes} closes")
        
        return {'issues': issues, 'warnings': warnings}
    
    def _check_vbscript_sub_function_syntax(self, content: str) -> Dict[str, Any]:
        """Check VBScript Sub and Function syntax."""
        issues: List[str] = []
        warnings: List[str] = []
        
        # Check for proper Sub/Function declarations
        sub_pattern = r'\bSub\s+\w+\s*\('
        function_pattern = r'\bFunction\s+\w+\s*\('
        
        subs = re.findall(sub_pattern, content, re.IGNORECASE)
        functions = re.findall(function_pattern, content, re.IGNORECASE)
        
        # Check for matching End Sub/End Function
        end_subs = len(re.findall(r'\bEnd\s+Sub\b', content, re.IGNORECASE))
        end_functions = len(re.findall(r'\bEnd\s+Function\b', content, re.IGNORECASE))
        
        if len(subs) != end_subs:
            issues.append(f"Unmatched Sub declarations: {len(subs)} Subs, {end_subs} End Subs")
        
        if len(functions) != end_functions:
            issues.append(f"Unmatched Function declarations: {len(functions)} Functions, {end_functions} End Functions")
        
        return {'issues': issues, 'warnings': warnings}
    
    def _check_vbscript_end_statements(self, content: str) -> Dict[str, Any]:
        """Check VBScript End statement matching."""
        issues: List[str] = []
        warnings: List[str] = []
        
        # Check for matching If/End If statements
        if_pattern = r'\bIf\b.*?\bThen\b'
        end_if_pattern = r'\bEnd\s+If\b'
        
        ifs = len(re.findall(if_pattern, content, re.IGNORECASE))
        end_ifs = len(re.findall(end_if_pattern, content, re.IGNORECASE))
        
        # Note: This is a simplified check - inline If statements don't need End If
        # Only block If statements need End If, but this gives a rough validation
        if ifs > end_ifs and ifs - end_ifs > 2:  # Allow some tolerance for inline Ifs
            warnings.append(f"Possible unmatched If statements: {ifs} Ifs, {end_ifs} End Ifs")
        
        return {'issues': issues, 'warnings': warnings}

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages for validation."""
        return list(self.language_validators.keys())
