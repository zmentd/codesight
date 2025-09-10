"""
Java reader implementation using JPype and JavaParser JAR.

Handles Java source files and extracts comprehensive structural information
using existing domain models and LEX utilities.
"""

import re
import time
from typing import Any, Dict, List, Optional, Union

from config import Config
from domain import LayerType, PatternType
from domain.source_inventory import ArchitecturalLayerType
from lex import EncodingDetector, SyntaxValidator

from .base_reader import BaseReader, ParseResult
from .sql_statement_analyzer import SQLStatementAnalyzer


class JavaReader(BaseReader):
    """
    Java-specific AST reading using JPype + JavaParser JAR.
    
    Uses existing domain models and LEX utilities for comprehensive
    Java source code analysis. Responsible for extracting structural
    information and cross-file relationships.
    """
    
    def __init__(self, config: Config, jpype_manager: Any) -> None:
        """
        Initialize Java reader with JPype as required dependency.
        
        Args:
            config: Configuration instance
            jpype_manager: JPype manager instance (required)
        """
        super().__init__(config)
        
        # JPype is now required - fail fast if not provided
        if jpype_manager is None:
            raise RuntimeError("JPype manager is required for JavaReader. "
                             "Please provide a valid JPype manager instance.")
        
        self.jpype_manager = jpype_manager
        
        # Ensure JPype is available and initialized
        if not self.jpype_manager.is_available():
            raise RuntimeError("JPype is required for JavaReader but is not available. "
                             "Please ensure JPype is properly installed and configured.")
        
        # Use existing LEX utilities for configuration-driven pattern detection
        self.encoding_detector = EncodingDetector(config)
        self.syntax_validator = SyntaxValidator(config)
        
        # Use existing LEX utilities, passing config
        self.encoding_detector = EncodingDetector(config)
        self.syntax_validator = SyntaxValidator(config)
                
        # Configuration file patterns
        self.java_file_patterns = {
            'java': r'.*\.java$',
        }
  
    def can_parse(self, file_info: Dict[str, Any]) -> bool:
        """
        Check if this reader can handle Java files.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            True if file is a Java file
        """
        file_path = file_info.get("path", "")
        file_type = file_info.get("type", "")
        
        # Check file type classification
        if file_type in ["java"]:
            return True
        
        # Check specific configuration patterns
        for config_type, pattern in self.java_file_patterns.items():
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
        
        return False
    
    def parse_file(self, source_path: str, file_path: str) -> ParseResult:
        """
        Parse Java source file and extract AST structural information.
        
        Args:
            source_path: Base source path
            file_path: Path to the Java file
            
        Returns:
            Parse result with Java AST data
        """
        start_time = time.time()
        
        try:
            # Read file content
            content = self.read_file(source_path, file_path)
            
            # Pre-process content
            processed_content = self._pre_process_content(content, file_path)
            
            # Extract Java structural data
            structural_data = self._extract_java_structure(file_path, processed_content)
            
            # Detect framework patterns using both content and structural data
            framework_hints = self._detect_java_framework_patterns(processed_content, structural_data)
            
            # Detect layer and architectural patterns using configuration
            detected_layer = self._detect_layer_from_config(file_path, processed_content, structural_data)
            architectural_pattern = self._detect_architectural_pattern_from_config(file_path)
            entity_mappings = self.detect_entity_mapping(file_path, processed_content, structural_data)
            sql_executions = self.detect_sql_execution(file_path, processed_content, structural_data)
            # Add layer and architectural information to structural data
            structural_data["detected_layer"] = detected_layer.value
            structural_data["architectural_pattern"] = architectural_pattern.value
            structural_data["entity_mappings"] = entity_mappings
            structural_data["sql_executions"] = sql_executions
            # Calculate confidence
            confidence = self._calculate_confidence(structural_data)
            
            result = ParseResult(
                success=True,
                file_path=file_path,
                language="java",
                structural_data=structural_data,
                confidence=confidence,
                framework_hints=framework_hints,
                processing_time=time.time() - start_time
            )
            
            return self._post_process_result(result)
            
        except Exception as e:  # pylint: disable=broad-except
            return self._handle_parse_error(file_path, e)
    
    def _extract_java_structure(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Extract Java structural information using JPype only.
        
        Args:
            file_path: Path to the Java file
            content: Java file content
            
        Returns:
            Structural data dictionary
        """
        structural_data: Dict[str, Any] = {
            "file_path": file_path,
            "package": None,
            "imports": [],
            "classes": [],
            "interfaces": [],
            "enums": [],
            "annotations": [],
            # Cross-file relationship tracking (keep for detailed analysis)
            "method_calls": [],  # Methods called from this file
            "field_references": [],  # Other classes referenced as field types
            "inheritance_relationships": [],  # extends/implements relationships
            "annotation_dependencies": [],  # @Autowired, @Inject dependencies
            "framework_relationships": []  # JPA @OneToMany, Struts action mappings
        }
        
        try:
            # Parse with JPype - this is now the only path
            jpype_result = self.jpype_manager.parse_java_file(content)
            if not jpype_result:
                raise RuntimeError(f"Failed to parse Java file {file_path} with JPype. "
                                 "JPype parsing is required for JavaReader.")
        
            # Merge JPype structural data
            structural_data = dict(jpype_result)  # Ensure proper type conversion
            structural_data['file_path'] = file_path  # Ensure file path is set
            
            # Debug: Check the structure we got from JPype
            self.logger.debug("JPype returned data type: %s", type(jpype_result))
            if isinstance(jpype_result, dict):
                self.logger.debug("JPype returned keys: %s", list(jpype_result.keys()))
                classes = jpype_result.get('classes', [])
                self.logger.debug("Classes type: %s", type(classes))
                if classes and len(classes) > 0:
                    self.logger.debug("First class type: %s", type(classes[0]))
                    self.logger.debug("First class: %s", classes[0])
            
        except Exception as e:
            self.logger.error("Error in JPype parsing or data processing: %s", e)
            raise
            
        try:
            # Enrich with complexity metrics (JPype already provides these, but this handles edge cases)
            structural_data = self._enrich_with_complexity_metrics(content, structural_data)
        except Exception as e:
            self.logger.error("Error in _enrich_with_complexity_metrics: %s", e)
            raise
        
        try:
            # Extract cross-file relationships using JPype data + existing config patterns
            structural_data = self._extract_cross_file_relationships(content, structural_data)
        except Exception as e:
            self.logger.error("Error in _extract_cross_file_relationships: %s", e)
            raise
        
        try:
            # Extract REST endpoints and security information
            structural_data = self._extract_rest_endpoints(structural_data)
            structural_data = self._extract_security_roles(structural_data)
            structural_data = self._extract_aop_pointcuts(structural_data)
        except Exception as e:
            self.logger.error("Error in REST/security/AOP extraction: %s", e)
            raise
        
        try:
            # Extract manager pattern information
            structural_data = self._enhance_with_manager_patterns(structural_data)
        except Exception as e:
            self.logger.error("Error in _enhance_with_manager_patterns: %s", e)
            raise
        
        return structural_data
    
    def _extract_cross_file_relationships(self, content: str, structural_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relationships between files using enhanced JPype-first approach.
        
        Args:
            content: Java content
            structural_data: Existing structural data from JPype
            
        Returns:
            Updated structural data with cross-file relationships
        """
        # Build comprehensive resolution context from JPype data
        resolution_context = self._build_resolution_context(structural_data)
        
        # Use JPype-first approach with smart fallbacks
        try:
            structural_data["method_calls"] = self._extract_method_calls_jpype_first(
                content, structural_data, resolution_context)
        except Exception as e:
            self.logger.error("Error in _extract_method_calls_jpype_first: %s", e)
            raise

        try:
            structural_data["field_references"] = self._extract_field_references_jpype_first(
                structural_data, resolution_context)
        except Exception as e:
            self.logger.error("Error in _extract_field_references_jpype_first: %s", e)
            raise

        try:
            structural_data["inheritance_relationships"] = self._extract_inheritance_jpype_first(
                structural_data, resolution_context)
        except Exception as e:
            self.logger.error("Error in _extract_inheritance_jpype_first: %s", e)
            raise

        try:
            structural_data["annotation_dependencies"] = self._extract_annotation_deps_jpype_first(
                structural_data, resolution_context)
        except Exception as e:
            self.logger.error("Error in _extract_annotation_deps_jpype_first: %s", e)
            raise

        try:
            structural_data["framework_relationships"] = self._extract_framework_rels_jpype_first(
                content, structural_data, resolution_context)
        except Exception as e:
            self.logger.error("Error in _extract_framework_rels_jpype_first: %s", e)
            raise

        return structural_data
    
    def _safe_get_classes(self, structural_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Safely get classes from structural data, filtering out any string entries.
        
        Args:
            structural_data: Structural data that may contain mixed types
            
        Returns:
            List of class dictionaries, filtering out any strings
        """
        classes = structural_data.get("classes", [])
        return [cls for cls in classes if isinstance(cls, dict)]
    
    def _safe_get_interfaces(self, structural_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Safely get interfaces from structural data, filtering out any string entries.
        
        Args:
            structural_data: Structural data that may contain mixed types
            
        Returns:
            List of interface dictionaries, filtering out any strings
        """
        interfaces = structural_data.get("interfaces", [])
        return [iface for iface in interfaces if isinstance(iface, dict)]
    
    def _safe_get_annotation_name(self, annotation: Union[str, Dict[str, Any]]) -> str:
        """
        Safely extract annotation name from annotation data.
        
        Args:
            annotation: Annotation data that may be a string or dict
            
        Returns:
            Annotation name with @ prefix
        """
        if isinstance(annotation, str):
            return annotation if annotation.startswith("@") else f"@{annotation}"
        else:
            return str(annotation.get("name", ""))
    
    class ResolutionContext:
        """Enhanced resolution context using JPype structural data."""
        
        def __init__(self, imports: List[Dict[str, Any]], package: str, classes: List[Union[Dict[str, Any], str]]):
            self.import_map = self._build_import_map(imports)
            self.package = package
            # Handle both dictionary and string class representations
            self.local_classes = set()
            for cls in classes:
                if isinstance(cls, dict):
                    class_name = cls.get("name", "")
                    if class_name:
                        self.local_classes.add(class_name)
                elif isinstance(cls, str):
                    self.local_classes.add(cls)
            
            self.java_lang_classes = {
                'String', 'Integer', 'Boolean', 'Long', 'Double', 'Float', 'Character',
                'Byte', 'Short', 'Object', 'Class', 'System', 'Math', 'Exception',
                'RuntimeException', 'Throwable', 'Error', 'List', 'Set', 'Map'
            }
        
        def _build_import_map(self, imports: List[Dict[str, Any]]) -> Dict[str, str]:
            """Build mapping from simple class names to fully qualified names."""
            import_map = {}
            for import_info in imports:
                import_name = import_info.get("name", "")
                is_static = import_info.get("static", False)
                is_asterisk = import_info.get("asterisk", False)
                
                if is_static or is_asterisk or not import_name:
                    continue
                
                if "." in import_name:
                    simple_name = import_name.split(".")[-1]
                    import_map[simple_name] = import_name
            
            return import_map
        
        def resolve_type(self, simple_type_name: str) -> str:
            """Resolve simple type name to fully qualified name."""
            if not simple_type_name:
                return simple_type_name
            
            # Handle generics
            base_type = simple_type_name.split('<')[0] if '<' in simple_type_name else simple_type_name
            
            # Check explicit imports
            if base_type in self.import_map:
                resolved_base = self.import_map[base_type]
                if '<' in simple_type_name:
                    generics_part = simple_type_name[simple_type_name.index('<'):]
                    return resolved_base + generics_part
                return resolved_base
            
            # Check local classes
            if base_type in self.local_classes and self.package:
                resolved_base = f"{self.package}.{base_type}"
                if '<' in simple_type_name:
                    generics_part = simple_type_name[simple_type_name.index('<'):]
                    return resolved_base + generics_part
                return resolved_base
            
            # Check java.lang
            if base_type in self.java_lang_classes:
                resolved_base = f"java.lang.{base_type}"
                if '<' in simple_type_name:
                    generics_part = simple_type_name[simple_type_name.index('<'):]
                    return resolved_base + generics_part
                return resolved_base
            
            # Return as-is if can't resolve
            return simple_type_name
    
    def _build_resolution_context(self, structural_data: Dict[str, Any]) -> 'JavaReader.ResolutionContext':
        """Build resolution context from JPype structural data."""
        imports = structural_data.get("imports", [])
        package = structural_data.get("package", "")
        classes = structural_data.get("classes", [])
        
        return self.ResolutionContext(imports, package, classes)
    
    def _extract_field_references_jpype_first(self, structural_data: Dict[str, Any], 
                                            resolution_context: 'JavaReader.ResolutionContext') -> List[Dict[str, Any]]:
        """
        Extract field references using JPype structural data first.
        
        Args:
            structural_data: Structural data from JPype
            resolution_context: Resolution context for type names
            
        Returns:
            List of field references with resolved fully qualified type names
        """
        field_references = []
        
        # Extract from JPype class data directly - this is the primary approach
        for class_info in self._safe_get_classes(structural_data):
            for field in class_info.get("fields", []):
                field_type = field.get("type", "")
                field_name = field.get("name", "")
                
                if not field_type or not field_name:
                    continue
                
                # Skip primitive types and common Java built-ins
                base_type = field_type.split('<')[0] if '<' in field_type else field_type
                if base_type.lower() in ['int', 'long', 'double', 'float', 'boolean', 'char', 'byte', 'short']:
                    continue
                
                if not base_type.startswith(('String', 'Integer', 'Boolean', 'Long', 'Double', 'Float')):
                    # Resolve using JPype import context
                    resolved_type = resolution_context.resolve_type(field_type)
                    
                    field_references.append({
                        "field_name": field_name,
                        "referenced_type": resolved_type,
                        "is_collection": '<' in field_type,
                        "source": "jpype_ast"  # Track source for debugging
                    })
        
        # Also extract from interfaces
        for interface_info in self._safe_get_interfaces(structural_data):
            for field in interface_info.get("fields", []):
                field_type = field.get("type", "")
                field_name = field.get("name", "")
                
                if not field_type or not field_name:
                    continue
                
                base_type = field_type.split('<')[0] if '<' in field_type else field_type
                if base_type.lower() in ['int', 'long', 'double', 'float', 'boolean', 'char', 'byte', 'short']:
                    continue
                
                if not base_type.startswith(('String', 'Integer', 'Boolean', 'Long', 'Double', 'Float')):
                    resolved_type = resolution_context.resolve_type(field_type)
                    
                    field_references.append({
                        "field_name": field_name,
                        "referenced_type": resolved_type,
                        "is_collection": '<' in field_type,
                        "source": "jpype_ast"
                    })
        
        return field_references
    
    def _extract_inheritance_jpype_first(self, structural_data: Dict[str, Any], 
                                       resolution_context: 'JavaReader.ResolutionContext') -> List[Dict[str, Any]]:
        """
        Extract inheritance relationships using JPype structural data first.
        
        Args:
            structural_data: Structural data from JPype
            resolution_context: Resolution context for type names
            
        Returns:
            List of inheritance relationships with resolved fully qualified names
        """
        relationships = []
        
        # Extract from JPype class data - should be more reliable than regex
        for class_info in self._safe_get_classes(structural_data):
            class_name = class_info.get("name", "")
            if not class_name:
                continue
            
            # Handle extends relationships
            extends_list = class_info.get("extends", [])
            if isinstance(extends_list, str):
                extends_list = [extends_list]
            
            for parent_class in extends_list:
                if parent_class:
                    resolved_parent = resolution_context.resolve_type(parent_class)
                    relationships.append({
                        "child_class": class_name,
                        "parent_class": resolved_parent,
                        "relationship_type": "extends",
                        "source": "jpype_ast"
                    })
            
            # Handle implements relationships
            implements_list = class_info.get("implements", [])
            if isinstance(implements_list, str):
                implements_list = [implements_list]
            
            for interface in implements_list:
                if interface:
                    resolved_interface = resolution_context.resolve_type(interface)
                    relationships.append({
                        "child_class": class_name,
                        "parent_interface": resolved_interface,
                        "relationship_type": "implements",
                        "source": "jpype_ast"
                    })
        
        # Also check interfaces extending other interfaces
        for interface_info in self._safe_get_interfaces(structural_data):
            interface_name = interface_info.get("name", "")
            if not interface_name:
                continue
            
            extends_list = interface_info.get("extends", [])
            if isinstance(extends_list, str):
                extends_list = [extends_list]
            
            for parent_interface in extends_list:
                if parent_interface:
                    resolved_parent = resolution_context.resolve_type(parent_interface)
                    relationships.append({
                        "child_interface": interface_name,
                        "parent_interface": resolved_parent,
                        "relationship_type": "extends",
                        "source": "jpype_ast"
                    })
        
        return relationships
    
    def _extract_annotation_deps_jpype_first(self, structural_data: Dict[str, Any], 
                                           resolution_context: 'JavaReader.ResolutionContext') -> List[Dict[str, Any]]:
        """
        Extract annotation dependencies using JPype structural data first.
        
        Args:
            structural_data: Structural data from JPype
            resolution_context: Resolution context for type names
            
        Returns:
            List of annotation dependencies with resolved fully qualified type names
        """
        dependencies = []
        
        # Extract from JPype class data - annotations on fields
        for class_info in self._safe_get_classes(structural_data):
            for field in class_info.get("fields", []):
                field_name = field.get("name", "")
                field_type = field.get("type", "")
                field_annotations = field.get("annotations", [])
                
                if not field_name or not field_type:
                    continue
                
                # Check for dependency injection annotations
                for annotation in field_annotations:
                    # Handle both string and dict annotations
                    if isinstance(annotation, str):
                        annotation_name = annotation if annotation.startswith("@") else f"@{annotation}"
                    else:
                        annotation_name = annotation.get("name", "")
                    
                    if annotation_name in ["@Autowired", "@Inject", "@Resource"]:
                        resolved_type = resolution_context.resolve_type(field_type)
                        
                        injection_type = "autowired"
                        if annotation_name == "@Resource":
                            injection_type = "resource"
                        elif annotation_name == "@Inject":
                            injection_type = "inject"
                        
                        dependencies.append({
                            "dependency_type": resolved_type,
                            "field_name": field_name,
                            "injection_type": injection_type,
                            "annotation": annotation_name,
                            "source": "jpype_ast"
                        })
        
        return dependencies
    
    def _extract_method_calls_jpype_first(self, content: str, structural_data: Dict[str, Any], 
                                        resolution_context: 'JavaReader.ResolutionContext') -> List[Dict[str, Any]]:
        """
        Extract method calls using JPype data first, with minimal regex fallback.
        
        Args:
            content: Java content
            structural_data: Structural data from JPype
            resolution_context: Resolution context for type names
            
        Returns:
            List of method calls with resolved fully qualified class names
        """
        method_calls = []
        
        # Try to extract method calls from JPype structural data first
        # JPype might provide method call information in method bodies (if available)
        jpype_calls = self._get_jpype_method_calls(structural_data)
        
        if jpype_calls:
            # Resolve using JPype context
            for call in jpype_calls:
                caller = call.get("caller_class", "")
                method = call.get("method_name", "")
                
                if caller and method:
                    resolved_caller = resolution_context.resolve_type(caller)
                    method_calls.append({
                        "caller_class": resolved_caller,
                        "method_name": method,
                        "call_type": call.get("call_type", "unknown"),
                        "source": "jpype_ast"
                    })
        else:
            # Fallback to minimal regex with JPype resolution
            method_calls = self._extract_method_calls_regex_fallback(content, resolution_context)
        
        return method_calls
    
    def _get_jpype_method_calls(self, structural_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Try to extract method calls from JPype structural data.
        
        Args:
            structural_data: Structural data from JPype
            
        Returns:
            List of method calls if available, empty list otherwise
        """
        # Check if JPype provides method call information
        # This depends on how comprehensive the JPype integration is
        method_calls = []
        
        # Look for method calls in class methods
        for class_info in self._safe_get_classes(structural_data):
            for method in class_info.get("methods", []):
                # Check if method has call information
                calls = method.get("method_calls", [])
                if calls:
                    method_calls.extend(calls)
        
        return method_calls
    
    def _extract_method_calls_regex_fallback(self, content: str, 
                                           resolution_context: 'JavaReader.ResolutionContext') -> List[Dict[str, Any]]:
        """
        Fallback method call extraction using minimal regex + JPype resolution.
        
        Args:
            content: Java content
            resolution_context: Resolution context for type names
            
        Returns:
            List of method calls with resolved fully qualified class names
        """
        method_calls = []
        
        # Minimal regex patterns for method calls
        call_patterns = [
            r'([A-Z][a-zA-Z0-9]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',  # Static calls
            r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',  # Instance calls
        ]
        
        for pattern in call_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                caller = match.group(1)
                method = match.group(2)
                
                # Filter out common Java built-ins
                if caller not in ['System', 'String', 'Integer', 'Boolean', 'Collections', 'Arrays']:
                    resolved_caller = resolution_context.resolve_type(caller)
                    
                    method_calls.append({
                        "caller_class": resolved_caller,
                        "method_name": method,
                        "call_type": "static" if caller[0].isupper() else "instance",
                        "source": "regex_fallback"
                    })
        
        return method_calls
    
    def _extract_framework_rels_jpype_first(self, content: str, structural_data: Dict[str, Any], 
                                          resolution_context: 'JavaReader.ResolutionContext') -> List[Dict[str, Any]]:
        """
        Extract framework relationships using JPype data first with targeted regex.
        
        Args:
            content: Java content
            structural_data: Structural data from JPype
            resolution_context: Resolution context for type names
            
        Returns:
            List of framework relationships with resolved fully qualified type names
        """
        relationships = []
        try:
            # Extract JPA relationships from JPype annotations
            relationships.extend(self._extract_jpa_relationships_from_jpype(structural_data, resolution_context))
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error extracting _extract_jpa_relationships_from_jpype: %s", e)
        try:

            # Extract Spring components from JPype annotations
            relationships.extend(self._extract_spring_components_from_jpype(structural_data, resolution_context))
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error extracting _extract_spring_components_from_jpype: %s", e)
        try:
        
            # Use minimal regex for patterns that JPype might not capture
            relationships.extend(self._extract_enterprise_patterns_regex(content, resolution_context))
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error extracting _extract_enterprise_patterns_regex: %s", e)

        return relationships
    
    def _extract_jpa_relationships_from_jpype(self, structural_data: Dict[str, Any], 
                                            resolution_context: 'JavaReader.ResolutionContext') -> List[Dict[str, Any]]:
        """Extract JPA relationships from JPype annotation data."""
        relationships = []
        
        jpa_annotations = {
            "@OneToMany": "one_to_many",
            "@ManyToOne": "many_to_one", 
            "@OneToOne": "one_to_one",
            "@ManyToMany": "many_to_many"
        }
        
        for class_info in self._safe_get_classes(structural_data):
            for field in class_info.get("fields", []):
                field_type = field.get("type", "")
                field_annotations = field.get("annotations", [])
                
                for annotation in field_annotations:
                    annotation_name = self._safe_get_annotation_name(annotation)
                    
                    if annotation_name in jpa_annotations:
                        # Extract entity type from field type
                        entity_type = field_type
                        if '<' in field_type and '>' in field_type:
                            # Handle generic types like List<Entity>
                            start = field_type.index('<') + 1
                            end = field_type.rindex('>')
                            entity_type = field_type[start:end].strip()
                        
                        resolved_entity = resolution_context.resolve_type(entity_type)
                        
                        relationships.append({
                            "relationship_type": jpa_annotations[annotation_name],
                            "related_entity": resolved_entity,
                            "framework": "jpa",
                            "source": "jpype_ast"
                        })
        
        return relationships
    
    def _extract_spring_components_from_jpype(self, structural_data: Dict[str, Any], 
                                            resolution_context: 'JavaReader.ResolutionContext') -> List[Dict[str, Any]]:
        """Extract Spring component information from JPype annotation data."""
        relationships = []
        
        spring_annotations = ["@Component", "@Service", "@Repository", "@Controller", "@RestController"]
        
        for class_info in self._safe_get_classes(structural_data):
            class_annotations = class_info.get("annotations", [])
            
            for annotation in class_annotations:
                annotation_name = self._safe_get_annotation_name(annotation)
                # Only try to get parameters if annotation is a dictionary
                annotation_params = annotation.get("parameters", {}) if isinstance(annotation, dict) else {}
                
                if annotation_name in spring_annotations:
                    # Extract bean name from annotation parameters if available
                    bean_name = None
                    if "value" in annotation_params:
                        bean_name = annotation_params["value"]
                    
                    relationships.append({
                        "relationship_type": "spring_component",
                        "bean_name": bean_name,
                        "component_type": annotation_name.replace("@", ""),
                        "source": "jpype_ast"
                    })
        
        return relationships
    
    def _extract_enterprise_patterns_regex(self, content: str, 
                                          resolution_context: 'JavaReader.ResolutionContext') -> List[Dict[str, Any]]:
        """Extract enterprise patterns using minimal targeted regex."""
        relationships = []
        
        # EJB JNDI lookup patterns
        ejb_lookup_pattern = r'lookup\s*\(\s*["\']([^"\']+)["\']\s*\)'
        ejb_matches = re.finditer(ejb_lookup_pattern, content)
        
        for match in ejb_matches:
            jndi_name = match.group(1)
            relationships.append({
                "relationship_type": "ejb_lookup",
                "jndi_name": jndi_name,
                "lookup_context": "EJBContext",
                "source": "regex_pattern"
            })
        
        # Business service factory patterns
        business_service_factory_pattern = r'([A-Z][a-zA-Z0-9]*Mgr)\.([a-zA-Z0-9]*MgrObject)\s*\('
        service_factory_matches = re.finditer(business_service_factory_pattern, content)
        
        for match in service_factory_matches:
            manager_class = match.group(1)
            factory_method = match.group(2)
            
            resolved_manager = resolution_context.resolve_type(manager_class)
            
            relationships.append({
                "relationship_type": "business_service_factory",
                "manager_class": resolved_manager,
                "factory_method": factory_method,
                "framework": "business_service_layer",
                "source": "regex_pattern"
            })
        
        return relationships
    
    def _build_import_map(self, imports: List[Dict[str, Any]], current_package: str) -> Dict[str, str]:
        """
        Build a mapping from simple class names to fully qualified names using imports.
        
        Args:
            imports: List of import dictionaries from structural data
            current_package: Current file's package
            
        Returns:
            Dictionary mapping simple class names to fully qualified names
        """
        import_map = {}
        
        for import_info in imports:
            import_name = import_info.get("name", "")
            is_static = import_info.get("static", False)
            is_asterisk = import_info.get("asterisk", False)
            
            if is_static or is_asterisk:
                # Skip static imports and wildcard imports for now
                # Could be enhanced later to handle these cases
                continue
            
            # Extract simple class name from fully qualified import
            if "." in import_name:
                simple_name = import_name.split(".")[-1]
                import_map[simple_name] = import_name
        
        return import_map
    
    def _resolve_class_name(self, simple_class_name: str, import_map: Dict[str, str], 
                           current_package: str) -> Optional[str]:
        """
        Resolve a simple class name to fully qualified name using imports.
        
        Args:
            simple_class_name: Simple class name (e.g., "UserManager")
            import_map: Mapping from simple names to fully qualified names
            current_package: Package of the current file
            
        Returns:
            Fully qualified class name or None if not resolvable
        """
        # First check explicit imports
        if simple_class_name in import_map:
            return import_map[simple_class_name]
        
        # Check if it's a class in the same package
        if current_package and simple_class_name and simple_class_name[0].isupper():
            # Assume it's in the same package
            return f"{current_package}.{simple_class_name}"
        
        # Check for common Java standard library classes
        java_lang_classes = {
            'String', 'Integer', 'Boolean', 'Long', 'Double', 'Float', 'Character',
            'Byte', 'Short', 'Object', 'Class', 'System', 'Math', 'Exception',
            'RuntimeException', 'Throwable', 'Error'
        }
        
        if simple_class_name in java_lang_classes:
            return f"java.lang.{simple_class_name}"
        
        # Could not resolve - return None to indicate resolution failure
        return None
    
    def _extract_field_type_references_with_resolution(self, content: str, imports: List[Dict[str, Any]], 
                                                     current_package: str) -> List[Dict[str, Any]]:
        """
        Extract field declarations that reference other classes with resolution.
        
        Args:
            content: Java content
            imports: Import information from JPype
            current_package: Current file's package
            
        Returns:
            List of field references with resolved fully qualified type names
        """
        field_references = []
        
        # Build import resolution map
        import_map = self._build_import_map(imports, current_package)
        
        # Pattern for field declarations with custom types
        field_pattern = r'(?:private|protected|public)?\s*([A-Z][a-zA-Z0-9]*(?:<[^>]+>)?)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[;=]'
        matches = re.finditer(field_pattern, content)
        
        for match in matches:
            field_type = match.group(1)
            field_name = match.group(2)
            
            # Extract base type (remove generics for resolution)
            base_type = field_type.split('<')[0] if '<' in field_type else field_type
            
            # Filter out Java built-in types
            if not base_type.startswith(('String', 'Integer', 'Boolean', 'Long', 'Double', 'Float')):
                # Try to resolve to fully qualified name
                fully_qualified_type = self._resolve_class_name(base_type, import_map, current_package)
                
                # If we resolved the base type, reconstruct with generics
                resolved_type = field_type
                if fully_qualified_type and '<' in field_type:
                    generics_part = field_type[field_type.index('<'):]
                    resolved_type = fully_qualified_type + generics_part
                elif fully_qualified_type:
                    resolved_type = fully_qualified_type
                
                field_references.append({
                    "field_name": field_name,
                    "referenced_type": resolved_type,
                    "is_collection": '<' in field_type
                })
        
        return field_references
    
    def _extract_inheritance_relationships_with_resolution(self, content: str, imports: List[Dict[str, Any]], 
                                                         current_package: str) -> List[Dict[str, Any]]:
        """
        Extract extends and implements relationships with resolution.
        
        Args:
            content: Java content
            imports: Import information from JPype
            current_package: Current file's package
            
        Returns:
            List of inheritance relationships with resolved fully qualified names
        """
        relationships = []
        
        # Build import resolution map
        import_map = self._build_import_map(imports, current_package)
        
        # Extract extends relationships
        extends_pattern = r'class\s+([A-Z][a-zA-Z0-9]*)\s+extends\s+([A-Z][a-zA-Z0-9]*)'
        extends_matches = re.finditer(extends_pattern, content)
        for match in extends_matches:
            child_class = match.group(1)
            parent_class = match.group(2)
            
            # Try to resolve parent class to fully qualified name
            fully_qualified_parent = self._resolve_class_name(parent_class, import_map, current_package)
            
            relationships.append({
                "child_class": child_class,
                "parent_class": fully_qualified_parent or parent_class,
                "relationship_type": "extends"
            })
        
        # Extract implements relationships
        implements_pattern = r'class\s+([A-Z][a-zA-Z0-9]*)\s+(?:extends\s+[A-Z][a-zA-Z0-9]*\s+)?implements\s+([A-Z][a-zA-Z0-9,\s]*)'
        implements_matches = re.finditer(implements_pattern, content)
        for match in implements_matches:
            child_class = match.group(1)
            interfaces = [iface.strip() for iface in match.group(2).split(',')]
            for interface in interfaces:
                if interface:
                    # Try to resolve interface to fully qualified name
                    fully_qualified_interface = self._resolve_class_name(interface, import_map, current_package)
                    
                    relationships.append({
                        "child_class": child_class,
                        "parent_interface": fully_qualified_interface or interface,
                        "relationship_type": "implements"
                    })
        
        return relationships
    
    def _detect_java_framework_patterns(self, content: str, structural_data: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Detect Java framework patterns using configuration-driven approach.
        
        Args:
            content: Java content
            structural_data: Optional structural data from JPype for enhanced detection
            
        Returns:
            List of detected framework hints
        """
        framework_hints: List[str] = []
        
        try:
            # Use configuration-driven framework detection
            if not hasattr(self.config, 'frameworks'):
                return framework_hints
            
            frameworks_config = self.config.frameworks
            
            # Check Struts framework
            if hasattr(frameworks_config, 'struts') and hasattr(frameworks_config.struts, 'indicators'):
                for indicator in frameworks_config.struts.indicators:
                    if indicator in content:
                        framework_hints.append('struts')
                        break
            
            # Check JEE framework
            if hasattr(frameworks_config, 'jee') and hasattr(frameworks_config.jee, 'indicators'):
                for indicator in frameworks_config.jee.indicators:
                    if indicator in content:
                        framework_hints.append('jee')
                        break
            
            # Enhanced detection using JPype structural data + configuration patterns
            if structural_data:
                annotations = self._extract_all_annotations_from_structural_data(structural_data)
                imports = structural_data.get("imports", [])
                
                # Check annotations using configuration patterns
                for annotation in annotations:
                    if annotation in ['@Controller', '@RestController']:
                        framework_hints.append('spring_mvc')
                    elif annotation in ['@Service', '@Repository', '@Component']:
                        framework_hints.append('spring_framework')
                    elif annotation in ['@Entity', '@Table']:
                        framework_hints.append('jpa_hibernate')
                    elif annotation in ['@WebServlet', '@Stateless', '@Stateful']:
                        framework_hints.append('jee')
                    elif annotation in ['@Path', '@GET', '@POST', '@PUT', '@DELETE', '@Produces', '@Consumes']:
                        framework_hints.append('jaxrs')
                    elif annotation in ['@Aspect', '@Pointcut', '@Around', '@Before', '@After']:
                        framework_hints.append('aspectj')
                    elif annotation in ['@RolesAllowed', '@PermitAll', '@DenyAll']:
                        framework_hints.append('security_annotations')
                
                # Check imports using configuration patterns
                for import_info in imports:
                    import_name = import_info.get("name", "")
                    if "springframework" in import_name:
                        framework_hints.append('spring_framework')
                    elif "hibernate" in import_name or "javax.persistence" in import_name:
                        framework_hints.append('jpa_hibernate')
                    elif "javax.servlet" in import_name or "javax.ejb" in import_name:
                        framework_hints.append('jee')
            
            # Additional pattern detection using configuration-driven approach
            if '@Autowired' in content or '@Inject' in content:
                framework_hints.append('dependency_injection')
            if '@OneToMany' in content or '@ManyToOne' in content:
                framework_hints.append('jpa_relationships')
        
        except Exception as e:  # pylint: disable=broad-except
            self.logger.warning("Failed to detect Java framework patterns: %s", str(e))
        
        return list(set(framework_hints))  # Remove duplicates
    
    def _extract_all_annotations_from_structural_data(self, structural_data: Dict[str, Any]) -> List[str]:
        """
        Extract all annotations from JPype structural data.
        
        Args:
            structural_data: Structural data from JPype
            
        Returns:
            List of annotation names
        """
        annotations: List[str] = []
        
        # Extract from classes
        for class_info in self._safe_get_classes(structural_data):
            # Handle both string and dict annotations
            for annotation in class_info.get("annotations", []):
                if isinstance(annotation, str):
                    ann_name = annotation if annotation.startswith("@") else f"@{annotation}"
                else:
                    ann_name = annotation.get("name", "")
                if ann_name:
                    annotations.append(ann_name)
            
            # Extract from methods
            for method in class_info.get("methods", []):
                for annotation in method.get("annotations", []):
                    if isinstance(annotation, str):
                        ann_name = annotation if annotation.startswith("@") else f"@{annotation}"
                    else:
                        ann_name = annotation.get("name", "")
                    if ann_name:
                        annotations.append(ann_name)
            
            # Extract from fields
            for field in class_info.get("fields", []):
                for annotation in field.get("annotations", []):
                    if isinstance(annotation, str):
                        ann_name = annotation if annotation.startswith("@") else f"@{annotation}"
                    else:
                        ann_name = annotation.get("name", "")
                    if ann_name:
                        annotations.append(ann_name)
        
        # Extract from interfaces
        for interface_info in self._safe_get_interfaces(structural_data):
            for annotation in interface_info.get("annotations", []):
                if isinstance(annotation, str):
                    ann_name = annotation if annotation.startswith("@") else f"@{annotation}"
                else:
                    ann_name = annotation.get("name", "")
                if ann_name:
                    annotations.append(ann_name)
            
            # Extract from methods
            for method in interface_info.get("methods", []):
                for annotation in method.get("annotations", []):
                    if isinstance(annotation, str):
                        ann_name = annotation if annotation.startswith("@") else f"@{annotation}"
                    else:
                        ann_name = annotation.get("name", "")
                    if ann_name:
                        annotations.append(ann_name)
        
        return annotations  # Already filtered during appending
    
    def _detect_layer_from_config(self, file_path: str, content: str, structural_data: Dict[str, Any]) -> LayerType:
        """
        Detect architectural layer using configuration-driven patterns.
        
        Args:
            file_path: Path to the Java file
            content: Java file content  
            structural_data: Structural data from JPype
            
        Returns:
            Detected layer type
        """
        try:
            # Get language patterns from configuration
            if not hasattr(self.config, 'languages_patterns'):
                return LayerType.OTHER
            
            languages_patterns = self.config.languages_patterns
            
            if not hasattr(languages_patterns, 'java'):
                return LayerType.OTHER
            
            java_patterns = languages_patterns.java
            
            # Check package patterns first (most reliable)
            package_name = structural_data.get("package", "")
            if package_name:
                layer = self._match_package_patterns(package_name, java_patterns)
                if layer != LayerType.OTHER:
                    return layer
            
            # Check code indicators
            layer = self._match_code_indicators(content, structural_data, java_patterns)
            if layer != LayerType.OTHER:
                return layer
            
            # Check framework-specific layer mapping
            if hasattr(self.config, 'frameworks'):
                frameworks_config = self.config.frameworks
                layer = self._match_framework_layers(structural_data, frameworks_config)
                if layer != LayerType.OTHER:
                    return layer
            
            return LayerType.OTHER
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.warning("Failed to detect layer from config: %s", str(e))
            return LayerType.OTHER
    
    def _match_package_patterns(self, package_name: str, java_patterns: Any) -> LayerType:
        """Match package name against configured patterns."""
        if not hasattr(java_patterns, 'package_patterns'):
            return LayerType.OTHER
        
        package_patterns = java_patterns.package_patterns
        
        # Get layer names dynamically from LayerType enum
        for layer_type in LayerType:
            if layer_type == LayerType.OTHER:
                continue
            layer_name = layer_type.value
            patterns = getattr(package_patterns, layer_name, [])
            for pattern in patterns:
                # Convert glob pattern to regex-like matching
                pattern_regex = pattern.replace('**', '.*').replace('*', '[^.]*')
                if re.search(pattern_regex, package_name, re.IGNORECASE):
                    return layer_type
        
        return LayerType.OTHER
    
    def _match_code_indicators(self, content: str, structural_data: Dict[str, Any], java_patterns: Any) -> LayerType:
        """Match code content against configured indicators."""
        if not hasattr(java_patterns, 'indicators'):
            return LayerType.OTHER
        
        indicators = java_patterns.indicators
        
        # Extract annotations for indicator matching
        annotations = self._extract_all_annotations_from_structural_data(structural_data)
        
        # Get layer names dynamically from LayerType enum
        for layer_type in LayerType:
            if layer_type == LayerType.OTHER:
                continue
            layer_name = layer_type.value
            layer_indicators = getattr(indicators, layer_name, [])
            for indicator in layer_indicators:
                # Check in content or annotations
                if indicator in content or indicator in annotations:
                    return layer_type
                    
                # Check class names for patterns like *Manager*, *Controller*
                if indicator.startswith('*') and indicator.endswith('*'):
                    pattern = indicator[1:-1]  # Remove wildcards
                    for class_info in self._safe_get_classes(structural_data):
                        class_name = class_info.get("name", "")
                        if pattern.lower() in class_name.lower():
                            return layer_type
        
        return LayerType.OTHER
    
    def _match_framework_layers(self, structural_data: Dict[str, Any], frameworks_config: Any) -> LayerType:
        """Match framework annotations to layers using configured mappings."""
        annotations = self._extract_all_annotations_from_structural_data(structural_data)
        
        # Check Struts framework layer mappings
        if hasattr(frameworks_config, 'struts') and hasattr(frameworks_config.struts, 'layer_mapping'):
            for annotation in annotations:
                layer_name = frameworks_config.struts.layer_mapping.get(annotation)
                if layer_name:
                    try:
                        return LayerType(layer_name)
                    except ValueError:
                        continue
        
        # Check JEE framework layer mappings
        if hasattr(frameworks_config, 'jee') and hasattr(frameworks_config.jee, 'layer_mapping'):
            for annotation in annotations:
                layer_name = frameworks_config.jee.layer_mapping.get(annotation)
                if layer_name:
                    try:
                        return LayerType(layer_name)
                    except ValueError:
                        continue
        
        return LayerType.OTHER
    
    def _detect_architectural_pattern_from_config(self, file_path: str) -> ArchitecturalLayerType:
        """
        Detect architectural pattern using configuration-driven directory patterns.
        
        Args:
            file_path: Path to the Java file
            
        Returns:
            Detected architectural layer type
        """
        try:
            # Get architectural patterns from configuration
            if not hasattr(self.config, 'architectural_patterns'):
                return ArchitecturalLayerType.UNKNOWN
            
            architectural_patterns = self.config.architectural_patterns
            
            # Normalize file path for matching
            normalized_path = file_path.replace('\\', '/')
            
            # Get architectural layer types dynamically from ArchitecturalLayerType enum
            # Map config attribute names to enum values
            arch_type_mapping = {
                'application': ArchitecturalLayerType.APPLICATION,
                'business': ArchitecturalLayerType.BUSINESS, 
                'data_access': ArchitecturalLayerType.DATA_ACCESS,
                'security': ArchitecturalLayerType.SECURITY,
                'shared': ArchitecturalLayerType.SHARED
            }
            
            # Check each architectural pattern dynamically
            for arch_type_name, arch_type_enum in arch_type_mapping.items():
                if hasattr(architectural_patterns, arch_type_name):
                    patterns = getattr(architectural_patterns, arch_type_name, [])
                    for pattern in patterns:
                        # Convert glob pattern to regex
                        pattern_regex = pattern.replace('**', '.*').replace('*', '[^/]*')
                        if re.search(pattern_regex, normalized_path, re.IGNORECASE):
                            return arch_type_enum
            
            return ArchitecturalLayerType.UNKNOWN
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.warning("Failed to detect architectural pattern from config: %s", str(e))
            return ArchitecturalLayerType.UNKNOWN
    
    def _enrich_with_complexity_metrics(self, content: str, structural_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich JPype structural data with complexity scores and line counts.
        
        Args:
            content: Java file content
            structural_data: Structural data from JPype
            
        Returns:
            Enriched structural data with complexity metrics
        """
        # Get the current time for performance tracking
        start_time = time.time()
        file_name = structural_data.get("file_path", "unknown")
        self.logger.debug("Enriching structural data with complexity metrics for %s", file_name)
        
        # Track methods processed to detect performance degradation
        methods_processed = 0
        slow_methods = 0
        
        try:
            # Process classes
            for class_info in self._safe_get_classes(structural_data):
                if "methods" in class_info:
                    for method in class_info["methods"]:
                        method_name = method.get("name", "")
                        if method_name:
                            # Check if JPype already provided complexity metrics
                            if "complexity_score" in method and "line_count" in method:
                                # JPype provided AST-based metrics - much faster!
                                methods_processed += 1
                                self.logger.debug("Using JPype complexity metrics for method %s in class %s", 
                                                method_name, class_info.get("name", "unknown"))
                            else:
                                # Simplified method processing without complexity calculation
                                method_start_time = time.time()
                                self.logger.debug("Processing method %s in class %s", method_name, class_info.get("name", "unknown"))
                                method["complexity_score"] = 1  # Default complexity
                                method["line_count"] = 1  # Default line count
                                method_end_time = time.time()
                                method_duration = method_end_time - method_start_time
                                
                                methods_processed += 1
                                if method_duration > 0.5:  # Flag methods taking longer than 0.5 seconds
                                    slow_methods += 1
                                    self.logger.warning("Slow method processing: %s took %.2f seconds", method_name, method_duration)
                                
                                self.logger.debug("Method %s processed in %.2f seconds", method_name, method_duration)
            
            # Process interfaces  
            for interface_info in self._safe_get_interfaces(structural_data):
                if "methods" in interface_info:
                    for method in interface_info["methods"]:
                        method_name = method.get("name", "")
                        if method_name:
                            # Interface methods have no implementation, so complexity is always 1
                            # and line count is 0 (just the declaration)
                            method_start_time = time.time()
                            self.logger.debug("Calculating complexity for method %s in interface %s", method_name, interface_info.get("name", "unknown"))
                            method["complexity_score"] = 1  # Interface methods have minimal complexity
                            method["line_count"] = 0  # Interface methods have no implementation lines
                            method_end_time = time.time()
                            self.logger.debug("Complexity for method %s calculated in %.2f seconds", method_name, method_end_time - method_start_time)
                            
        except (AttributeError, KeyError, ValueError, TypeError) as e:
            self.logger.warning("Failed to enrich structural data with complexity metrics: %s", str(e))

        end_time = time.time()
        elapsed_time = end_time - start_time
        self.logger.debug("Enrichment completed in %.2f seconds for %s", elapsed_time, file_name)
        
        # Log performance summary if we had performance issues
        if methods_processed > 0:
            avg_time_per_method = elapsed_time / methods_processed
            if slow_methods > 0 or avg_time_per_method > 0.1:
                self.logger.info("Performance summary for %s: %d methods, %d slow methods (>0.5s), avg %.3f seconds per method", 
                               file_name, methods_processed, slow_methods, avg_time_per_method)

        return structural_data
    
    def _extract_rest_endpoints(self, structural_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract REST endpoint information from JAX-RS annotations.
        
        Args:
            structural_data: Structural data from JPype
            
        Returns:
            Updated structural data with REST endpoint information
        """
        rest_endpoints = []
        
        # Check classes for @Path annotations (base path)
        for class_info in self._safe_get_classes(structural_data):
            class_path = ""
            class_produces = []
            class_consumes = []
            
            # Extract class-level annotations
            for annotation in class_info.get("annotations", []):
                # Handle both string and dict annotations
                if isinstance(annotation, str):
                    annotation_name = annotation if annotation.startswith("@") else f"@{annotation}"
                else:
                    annotation_name = annotation.get("name", "")
                
                if annotation_name == "@Path":
                    # Extract path value from annotation attributes (only for dict annotations)
                    if isinstance(annotation, dict):
                        attributes = annotation.get("attributes", {})
                        class_path = attributes.get("value", "").strip('"')
                elif annotation_name == "@Produces":
                    if isinstance(annotation, dict):
                        attributes = annotation.get("attributes", {})
                        produces_value = attributes.get("value", "")
                        if "APPLICATION_JSON" in produces_value or "application/json" in produces_value:
                            class_produces.append("application/json")
                        elif "APPLICATION_XML" in produces_value or "application/xml" in produces_value:
                            class_produces.append("application/xml")
                elif annotation_name == "@Consumes":
                    if isinstance(annotation, dict):
                        attributes = annotation.get("attributes", {})
                        consumes_value = attributes.get("value", "")
                        if "APPLICATION_JSON" in consumes_value or "application/json" in consumes_value:
                            class_consumes.append("application/json")
            
            # Check methods for HTTP annotations
            for method in class_info.get("methods", []):
                method_path = ""
                http_method = ""
                method_produces = class_produces.copy()
                method_consumes = class_consumes.copy()
                security_roles = []
                
                for annotation in method.get("annotations", []):
                    # Handle both string and dict annotations
                    if isinstance(annotation, str):
                        annotation_name = annotation if annotation.startswith("@") else f"@{annotation}"
                    else:
                        annotation_name = annotation.get("name", "")
                    
                    if annotation_name == "@Path":
                        if isinstance(annotation, dict):
                            attributes = annotation.get("attributes", {})
                            method_path = attributes.get("value", "").strip('"')
                    elif annotation_name in ["@GET", "@POST", "@PUT", "@DELETE", "@PATCH"]:
                        http_method = annotation_name[1:]  # Remove @
                    elif annotation_name == "@Produces":
                        if isinstance(annotation, dict):
                            attributes = annotation.get("attributes", {})
                            produces_value = attributes.get("value", "")
                            if "APPLICATION_JSON" in produces_value or "application/json" in produces_value:
                                method_produces = ["application/json"]
                            elif "APPLICATION_XML" in produces_value or "application/xml" in produces_value:
                                method_produces = ["application/xml"]
                    elif annotation_name == "@Consumes":
                        if isinstance(annotation, dict):
                            attributes = annotation.get("attributes", {})
                            consumes_value = attributes.get("value", "")
                            if "APPLICATION_JSON" in consumes_value or "application/json" in consumes_value:
                                method_consumes = ["application/json"]
                    elif annotation_name == "@RolesAllowed":
                        if isinstance(annotation, dict):
                            attributes = annotation.get("attributes", {})
                            roles_value = attributes.get("value", "")
                            # Handle both single role and array of roles
                            if roles_value:
                                if roles_value.startswith("[") and roles_value.endswith("]"):
                                    # Array format: ["ADMIN", "USER"]
                                    roles_str = roles_value[1:-1]  # Remove brackets
                                    security_roles = [role.strip().strip('"') for role in roles_str.split(",")]
                                else:
                                    # Single role: "ADMIN"
                                    security_roles = [roles_value.strip('"')]
                
                # Create REST endpoint if we found HTTP method
                if http_method:
                    full_path = class_path + method_path if method_path else class_path
                    if not full_path:
                        full_path = "/" + method.get("name", "")  # Fallback to method name
                    
                    rest_endpoints.append({
                        "path": full_path,
                        "http_method": http_method,
                        "class_name": class_info.get("name", ""),
                        "method_name": method.get("name", ""),
                        "produces": method_produces,
                        "consumes": method_consumes,
                        "security_roles": security_roles,
                        "framework": "jaxrs"
                    })
        
        structural_data["rest_endpoints"] = rest_endpoints
        return structural_data
    
    def _extract_security_roles(self, structural_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract security role information from security annotations.
        
        Args:
            structural_data: Structural data from JPype
            
        Returns:
            Updated structural data with security role information
        """
        security_roles: set[str] = set()
        
        # Extract from classes and methods
        for class_info in self._safe_get_classes(structural_data):
            # Check class-level security annotations
            for annotation in class_info.get("annotations", []):
                # Handle both string and dict annotations
                if isinstance(annotation, str):
                    annotation_name = annotation if annotation.startswith("@") else f"@{annotation}"
                else:
                    annotation_name = annotation.get("name", "")
                    
                if annotation_name == "@RolesAllowed":
                    if isinstance(annotation, dict):
                        attributes = annotation.get("attributes", {})
                        roles_value = attributes.get("value", "")
                        if roles_value:
                            if roles_value.startswith("[") and roles_value.endswith("]"):
                                roles_str = roles_value[1:-1]
                                security_roles.update(role.strip().strip('"') for role in roles_str.split(","))
                            else:
                                security_roles.add(roles_value.strip('"'))
            
            # Check method-level security annotations
            for method in class_info.get("methods", []):
                for annotation in method.get("annotations", []):
                    # Handle both string and dict annotations
                    if isinstance(annotation, str):
                        annotation_name = annotation if annotation.startswith("@") else f"@{annotation}"
                    else:
                        annotation_name = annotation.get("name", "")
                        
                    if annotation_name == "@RolesAllowed":
                        if isinstance(annotation, dict):
                            attributes = annotation.get("attributes", {})
                            roles_value = attributes.get("value", "")
                            if roles_value:
                                if roles_value.startswith("[") and roles_value.endswith("]"):
                                    roles_str = roles_value[1:-1]
                                    security_roles.update(role.strip().strip('"') for role in roles_str.split(","))
                                else:
                                    security_roles.add(roles_value.strip('"'))
        
        structural_data["security_roles"] = list(security_roles)
        return structural_data
    
    def _extract_aop_pointcuts(self, structural_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract AspectJ pointcut information for cross-cutting concerns.
        
        Args:
            structural_data: Structural data from JPype
            
        Returns:
            Updated structural data with AOP pointcut information
        """
        aop_pointcuts = []
        
        # Look for AspectJ annotations
        for class_info in self._safe_get_classes(structural_data):
            # Check if class has @Aspect annotation (handle both string and dict)
            is_aspect = False
            for ann in class_info.get("annotations", []):
                if isinstance(ann, str):
                    ann_name = ann if ann.startswith("@") else f"@{ann}"
                else:
                    ann_name = ann.get("name", "")
                if ann_name == "@Aspect":
                    is_aspect = True
                    break
            
            if is_aspect:
                # Extract pointcuts and advice
                for method in class_info.get("methods", []):
                    for annotation in method.get("annotations", []):
                        # Handle both string and dict annotations
                        if isinstance(annotation, str):
                            annotation_name = annotation if annotation.startswith("@") else f"@{annotation}"
                        else:
                            annotation_name = annotation.get("name", "")
                            
                        if annotation_name in ["@Pointcut", "@Before", "@After", "@Around", "@AfterReturning", "@AfterThrowing"]:
                            pointcut_expression = ""
                            if isinstance(annotation, dict):
                                attributes = annotation.get("attributes", {})
                                pointcut_expression = attributes.get("value", "")
                            
                            # Parse pointcut expression to extract target methods/classes
                            target_info = self._parse_pointcut_expression(pointcut_expression)
                            
                            aop_pointcuts.append({
                                "aspect_class": class_info.get("name", ""),
                                "advice_method": method.get("name", ""),
                                "advice_type": annotation_name[1:],  # Remove @
                                "pointcut_expression": pointcut_expression,
                                "target_class": target_info.get("target_class", ""),
                                "target_method": target_info.get("target_method", ""),
                                "framework": "aspectj"
                            })
        
        structural_data["aop_pointcuts"] = aop_pointcuts
        return structural_data
    
    def _parse_pointcut_expression(self, expression: str) -> Dict[str, str]:
        """
        Parse AspectJ pointcut expression to extract target information.
        
        Args:
            expression: Pointcut expression string
            
        Returns:
            Dictionary with target class and method information
        """
        target_info = {"target_class": "", "target_method": ""}
        
        if not expression:
            return target_info
        
        # Handle execution pointcuts: execution(public * com.example.Class.method())
        execution_match = re.search(r'execution\s*\(\s*[^*]*\*\s+([^.]+\.[^.]+)\.([^()]+)\s*\(', expression)
        if execution_match:
            full_class_path = execution_match.group(1)
            method_name = execution_match.group(2)
            
            # Extract class name from full path
            if "." in full_class_path:
                target_info["target_class"] = full_class_path
            else:
                target_info["target_class"] = full_class_path
            
            target_info["target_method"] = method_name
        
        # Handle other pointcut types as needed (within, args, etc.)
        
        return target_info

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Generic pattern matching that works with configuration"""
        # Handle different pattern types
        if pattern.startswith('*') and pattern.endswith('*'):
            # Wildcard pattern: *MgrObject*
            return pattern[1:-1] in text
        elif pattern.startswith('*'):
            # Suffix pattern: *MgrObject
            return text.endswith(pattern[1:])
        elif pattern.endswith('*'):
            # Prefix pattern: static*
            return text.startswith(pattern[:-1])
        elif '.*' in pattern:
            # Regex pattern: static.*MgrObject()
            try:
                return bool(re.search(pattern, text))
            except re.error:
                return False
        else:
            # Exact match
            return pattern == text

    def _extract_factory_methods(self, class_node: Dict[str, Any], config: Config) -> List[Dict[str, Any]]:
        """Extract static factory methods based on configuration patterns"""
        factory_methods = []
        
        # Safe access to nested configuration
        try:
            service_indicators = config.languages_patterns.java.indicators.Service
            if not isinstance(service_indicators, list):
                service_indicators = []  # type: ignore  # Fallback for type safety
        except AttributeError:
            service_indicators = []
        
        for method in class_node.get('methods', []):
            if 'static' in method.get('modifiers', []):
                method_signature = f"static {method.get('name', '')}()"
                method_name = method.get('name', '')
                return_type = method.get('return_type', '')
                
                # Check against configured patterns
                for indicator in service_indicators:
                    if (self._matches_pattern(method_signature, indicator) or 
                            self._matches_pattern(method_name, indicator)):
                        factory_methods.append({
                            'name': method_name,
                            'return_type': return_type,
                            'line_number': method.get('line_number', 0),
                            'matched_pattern': indicator,
                            'is_factory': True
                        })
                        break
        
        return factory_methods

    def _extract_manager_interfaces(self, class_node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract actual interface implementations from AST"""
        manager_interfaces = []
        
        # Use AST's implements clause, not naming conventions
        for interface in class_node.get('implements', []):
            # Handle both string and dictionary representations from JPype
            if isinstance(interface, str):
                interface_name = interface
                line_number = 0
            elif isinstance(interface, dict):
                interface_name = interface.get('name', '')
                line_number = interface.get('line_number', 0)
            else:
                continue  # Skip unexpected data types
                
            if interface_name:  # Only add if we have a valid interface name
                manager_interfaces.append({
                    'interface': interface_name,
                    'is_interface': True,  # We know it's an interface because it's in implements clause
                    'line_number': line_number
                })
        
        return manager_interfaces

    def _extract_manager_usage(self, method_node: Dict[str, Any], config: Config) -> List[Dict[str, Any]]:
        """Extract manager factory method calls"""
        manager_usages = []
        
        # Safe access to nested configuration
        try:
            service_indicators = config.languages_patterns.java.indicators.Service
            if not isinstance(service_indicators, list):
                service_indicators = []  # type: ignore  # Fallback for type safety
        except AttributeError:
            service_indicators = []
        
        # Look for method calls in the method body
        method_calls = method_node.get('method_calls', [])
        for call in method_calls:
            call_expression = call.get('expression', '')
            
            # Check if this matches service patterns
            for indicator in service_indicators:
                if self._matches_pattern(call_expression, indicator):
                    # Extract manager class and method from call
                    parts = call_expression.split('.')
                    if len(parts) >= 2:
                        manager_usages.append({
                            'manager_class': parts[0],
                            'factory_method': parts[1] if len(parts) > 1 else 'unknown',
                            'line_number': call.get('line_number', 0),
                            'usage_type': 'factory_call',
                            'matched_pattern': indicator
                        })
                    break
        
        return manager_usages

    def _detect_multi_manager_orchestration(self, class_node: Dict[str, Any], config: Config) -> Dict[str, Any]:
        """Detect classes that coordinate multiple managers"""
        manager_fields = []
        manager_calls = []
        
        # Safe access to nested configuration
        try:
            service_indicators = config.languages_patterns.java.indicators.Service
            if not isinstance(service_indicators, list):
                service_indicators = []  # type: ignore  # Fallback for type safety
        except AttributeError:
            service_indicators = []
        
        # Check for multiple manager field declarations
        for field in class_node.get('fields', []):
            field_type = field.get('type', '')
            
            # Check against service patterns for field types
            for indicator in service_indicators:
                if self._matches_pattern(field_type, indicator):
                    manager_fields.append({
                        'field_name': field.get('name', 'unknown'),
                        'manager_type': field_type,
                        'line_number': field.get('line_number', 0),
                        'matched_pattern': indicator
                    })
                    break
        
        # Check for multiple manager method calls in methods
        for method in class_node.get('methods', []):
            method_manager_calls = self._extract_manager_usage(method, config)
            manager_calls.extend(method_manager_calls)
        
        unique_managers: set[str] = set()
        unique_managers.update(field['manager_type'] for field in manager_fields)
        unique_managers.update(call['manager_class'] for call in manager_calls)
        
        is_orchestrator = len(unique_managers) > 1
        
        return {
            'is_orchestrator': is_orchestrator,
            'manager_fields': manager_fields,
            'manager_calls': manager_calls,
            'orchestration_score': len(manager_fields) + len(manager_calls),
            'unique_manager_count': len(unique_managers)
        }

    def _analyze_type_relationships(self, class_node: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze actual type relationships from AST"""
        relationships: Dict[str, Any] = {
            'implements': [],
            'extends': [],
            'is_interface': False,
            'is_abstract': False
        }
        
        # Check if this is an interface declaration
        relationships['is_interface'] = class_node.get('is_interface', False)
        
        # Check modifiers for abstract
        modifiers = class_node.get('modifiers', [])
        relationships['is_abstract'] = 'abstract' in modifiers
        
        # Ensure implements is a list and get actual implements relationships
        implements_list = relationships['implements']
        if not isinstance(implements_list, list):
            implements_list = []
            relationships['implements'] = implements_list
            
        for interface in class_node.get('implements', []):
            # Handle both string and dictionary representations from JPype
            if isinstance(interface, str):
                interface_name = interface
                qualified_name = interface
            elif isinstance(interface, dict):
                interface_name = interface.get('name', '')
                qualified_name = interface.get('qualified_name', interface.get('name', ''))
            else:
                continue  # Skip unexpected data types
                
            if interface_name:  # Only add if we have a valid interface name
                implements_list.append({
                    'interface_name': interface_name,
                    'qualified_name': qualified_name
                })
        
        # Ensure extends is a list and get actual extends relationships
        extends_list = relationships['extends']
        if not isinstance(extends_list, list):
            extends_list = []
            relationships['extends'] = extends_list
            
        extends_info = class_node.get('extends')
        if extends_info:
            # Handle both string and dictionary representations from JPype
            if isinstance(extends_info, str):
                parent_class = extends_info
                qualified_name = extends_info
            elif isinstance(extends_info, dict):
                parent_class = extends_info.get('name', '')
                qualified_name = extends_info.get('qualified_name', extends_info.get('name', ''))
            else:
                parent_class = ''
                qualified_name = ''
                
            if parent_class:  # Only add if we have a valid parent class name
                extends_list.append({
                    'parent_class': parent_class,
                    'qualified_name': qualified_name
                })
        
        return relationships

    def _enhance_with_manager_patterns(self, structural_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance structural data with manager pattern information.
        
        Args:
            structural_data: The structural data to enhance
            
        Returns:
            Enhanced structural data with manager pattern info
        """
        all_factory_methods = []
        all_manager_interfaces = []
        all_manager_usage = []
        orchestration_info = {}
        
        # Process each class for manager patterns
        classes = structural_data.get("classes", [])
        for class_info in classes:
            # Skip if class_info is not a dictionary (defensive programming)
            if not isinstance(class_info, dict):
                continue
                
            # Extract factory methods
            factory_methods = self._extract_factory_methods(class_info, self.config)
            all_factory_methods.extend(factory_methods)
            
            # Extract manager interfaces
            manager_interfaces = self._extract_manager_interfaces(class_info)
            all_manager_interfaces.extend(manager_interfaces)
            
            # Extract manager usage from methods
            for method in class_info.get('methods', []):
                manager_usage = self._extract_manager_usage(method, self.config)
                all_manager_usage.extend(manager_usage)
            
            # Detect orchestration patterns
            class_orchestration = self._detect_multi_manager_orchestration(class_info, self.config)
            if class_orchestration.get('is_orchestrator'):
                orchestration_info = class_orchestration
        
        # Determine if this is a manager class or orchestrator
        # Handle both dictionary and string class representations safely
        mgr_classes = []
        for cls in self._safe_get_classes(structural_data):
            class_name = cls.get('name', '')
            if 'Mgr' in class_name:
                mgr_classes.append(class_name)
        
        is_manager_class = (len(all_factory_methods) > 0 or 
                          len(all_manager_interfaces) > 0 or
                          len(mgr_classes) > 0)
        
        is_orchestrator_class = orchestration_info.get('is_orchestrator', False)
        
        # Add manager pattern data to structural data
        structural_data.update({
            "factory_methods": all_factory_methods,
            "manager_interfaces": all_manager_interfaces,
            "manager_usage": all_manager_usage,
            "orchestration_info": orchestration_info,
            "is_manager_class": is_manager_class,
            "is_orchestrator_class": is_orchestrator_class
        })
        
        return structural_data

    def detect_entity_mapping(self, file_path: str, processed_content: str, structural_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect entity mapping patterns in Java files.
        
        Args:
            file_path: Path to the Java file
            processed_content: Processed content of the file
            structural_data: Structural data from JPype
            
        Returns:
            Dictionary with entity mapping information
        """
        entity_mappings: List[Dict[str, Any]] = []
        
        try:
            # Get entity manager patterns from configuration
            entity_patterns = None
            if hasattr(self.config, 'languages_patterns') and hasattr(self.config.languages_patterns, 'java'):
                java_config = self.config.languages_patterns.java
                if hasattr(java_config, 'entity_manager_patterns'):
                    entity_patterns = java_config.entity_manager_patterns
            
            if not entity_patterns:
                return entity_mappings
            
            # Check if file matches the pattern (e.g., **/*Mgr.java)
            file_name = file_path.replace('\\', '/').split('/')[-1]
            if not self._matches_file_pattern(file_name, entity_patterns.file_name_pattern):
                return entity_mappings
        
            # Build resolution context to get FQNs
            resolution_context = self._build_resolution_context(structural_data)
            
            # Look for Manager classes that extend EntityMgr
            for class_info in self._safe_get_classes(structural_data):
                class_name = class_info.get('name', '')
                
                # Check if class matches the pattern (e.g., class SomeMgr extends EntityMgr)
                extends_info = class_info.get('extends')
                is_entity_manager = False
                
                if extends_info:
                    parent_class = extends_info if isinstance(extends_info, str) else extends_info.get('name', '')
                    if parent_class == 'EntityMgr':
                        is_entity_manager = True
                
                # Also check with regex pattern on content
                class_match = re.search(entity_patterns.class_declaration_pattern, processed_content)
                if class_match and class_match.group(1) == class_name:
                    is_entity_manager = True
                
                class_info["entity_mapping"] = {}
                if is_entity_manager:
                    # Look for getTableName() method
                    table_name = self._extract_table_name(class_info, processed_content, entity_patterns)
                                    
                    # Build fully qualified class name using resolution context
                    fqn_class_name = resolution_context.resolve_type(class_name)

                    entity_mapping = {
                        'class_name': fqn_class_name,
                        'table_name': table_name,
                        'file_path': file_path,
                        'line_number': class_info.get('line_number', 0),
                        'mapping_type': 'entity_manager',
                        'framework': 'custom_entity_mgr'
                    }
                    entity_mappings.append(entity_mapping)
                    class_info["entity_mapping"] = entity_mapping
        
        except Exception as e:  # pylint: disable=broad-except
            self.logger.warning("Failed to detect entity mapping patterns: %s", str(e))
        
        return entity_mappings
    
    def _matches_file_pattern(self, file_name: str, pattern: str) -> bool:
        """Check if file name matches glob-like pattern"""
        # Convert glob pattern to regex
        if pattern.startswith('**/'):
            pattern = pattern[3:]  # Remove **/ prefix
        
        if pattern.endswith('*'):
            return file_name.startswith(pattern[:-1])
        elif pattern.startswith('*'):
            return file_name.endswith(pattern[1:])
        elif '*' in pattern:
            # Convert * to .* for regex
            regex_pattern = pattern.replace('*', '.*')
            return bool(re.match(regex_pattern, file_name))
        else:
            return file_name == pattern
    
    def _extract_table_name(self, class_info: Dict[str, Any], content: str, entity_patterns: Any) -> str:
        """Extract table name from getTableName() method"""
        # Look for getTableName method in the class
        for method in class_info.get('methods', []):
            if method.get('name') == 'getTableName':
                # Try to find the return statement in the content
                table_match = re.search(entity_patterns.table_name_return_pattern, content)
                if table_match:
                    return table_match.group(1)
        
        # Fallback: try to infer table name from class name
        class_name = class_info.get('name', '')
        if isinstance(class_name, str) and class_name.endswith('Mgr'):
            return class_name[:-3]  # Remove 'Mgr' suffix
        
        return ""

    def detect_sql_execution(self, file_path: str, processed_content: str, structural_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect SQL execution patterns in Java files by analyzing each method.
        
        Args:
            file_path: Path to the Java file
            processed_content: Processed content of the file
            structural_data: Structural data from JPype
            
        Returns:
            List with SQL execution information including method context
        """
        sql_executions: List[Dict[str, Any]] = []
        analyzer = SQLStatementAnalyzer()
        try:
            # Get SQL execution patterns from configuration
            sql_patterns = None
            if hasattr(self.config, 'languages_patterns') and hasattr(self.config.languages_patterns, 'java'):
                java_config = self.config.languages_patterns.java
                if hasattr(java_config, 'sql_execution_patterns'):
                    sql_patterns = java_config.sql_execution_patterns
            
            if not sql_patterns:
                return sql_executions
            
            # Iterate through classes and their methods
            for class_info in self._safe_get_classes(structural_data):
                class_name = class_info.get('name', '')
                
                for method in class_info.get('methods', []):
                    method_name = method.get('name', '')
                    method_line_start = method.get('line_number', 0)
                    method_line_end = method.get('end_line_number', method_line_start)
                    method["sql_executions"] = []  # Initialize list to hold SQL executions
                    # Extract method body content
                    if not method.get('has_body', False):
                        continue
                    method_content = method.get('body_text', 0)  # self._extract_method_content(content_lines, method_line_start, method_line_end, method)
                    
                    if not method_content:
                        continue
                    
                    ps_matches = re.finditer(sql_patterns.prepared_statement_pattern, method_content)
                    for match in ps_matches:
                        sql_statement = match.group(1)
                        # Calculate line number relative to method start
                        method_relative_line = method_content[:match.start()].count('\n') + 1
                        absolute_line = method_line_start + method_relative_line - 1
                        
                        # Extract stored procedure name from EXEC statement
                        exec_match = re.search(sql_patterns.exec_pattern, sql_statement)
                        sql_execution = {
                            'sql_statement': sql_statement,
                            'execution_type': 'stored_procedure' if exec_match else 'sql_query',
                            'framework': 'java',
                            'file_path': file_path,
                            'line_number': absolute_line,
                            'class_name': class_name,
                            'method_name': method_name,
                            'method_line_start': method_line_start,
                            'method_line_end': method_line_end,
                        }
                        
                        if exec_match:
                            sql_execution['stored_procedure'] = exec_match.group(1)
                        else:
                            # Add call to parse SQL statement for further analysis
                            sql_analyzed_statement = analyzer.analyze_statement(sql_statement, "")
                            sql_execution['analyzed_statement'] = sql_analyzed_statement
                        sql_executions.append(sql_execution)
                        method["sql_executions"].append(sql_execution)
                    # Look for dynamic stored procedure patterns in method content
                    dynamic_matches = re.finditer(sql_patterns.dynamic_sp_pattern, method_content)
                    for match in dynamic_matches:
                        sp_suffix = match.group(1)
                        method_relative_line = method_content[:match.start()].count('\n') + 1
                        absolute_line = method_line_start + method_relative_line - 1
                        
                        dynamic_sql_execution = {
                            'sql_statement': f'getTableName() + "{sp_suffix}"',
                            'stored_procedure_suffix': sp_suffix,
                            'execution_type': 'dynamic_stored_procedure',
                            'framework': 'java',
                            'file_path': file_path,
                            'line_number': absolute_line,
                            'class_name': class_name,
                            'method_name': method_name,
                            'method_line_start': method_line_start,
                            'method_line_end': method_line_end
                        }
                        sql_executions.append(dynamic_sql_execution)
                        method["sql_executions"].append(dynamic_sql_execution)
        
        except Exception as e:  # pylint: disable=broad-except
            self.logger.warning("Failed to detect SQL execution patterns: %s", str(e))
        
        return sql_executions
    
    def _extract_method_content(self, content_lines: List[str], method_line_start: int, method_line_end: int, method: Dict[str, Any]) -> str:
        """
        Extract the content of a specific method from the file content.
        
        Args:
            content_lines: List of content lines from the file
            method_line_start: Starting line number of the method (1-indexed)
            method_line_end: Ending line number of the method (1-indexed)  
            method: Method information from structural data
            
        Returns:
            String containing the method's content
        """
        try:
            # Handle case where we don't have end line number
            if method_line_end <= method_line_start:
                # Try to estimate method end by looking for method body or fallback to reasonable range
                method_line_end = min(method_line_start + 50, len(content_lines))  # Default to 50 lines max
            
            # Convert to 0-indexed for list access
            start_idx = max(0, method_line_start - 1)
            end_idx = min(len(content_lines), method_line_end)
            
            # Extract method lines
            method_lines = content_lines[start_idx:end_idx]
            return '\n'.join(method_lines)
            
        except (IndexError, ValueError) as e:
            self.logger.warning("Failed to extract method content for %s: %s", method.get('name', 'unknown'), str(e))
            return ""
