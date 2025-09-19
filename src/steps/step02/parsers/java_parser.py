"""
Java parser implementation for Step 02 AST extraction.

Uses JavaReader to extract structural information and builds JavaDetails objects
with CodeMapping integration for cross-file relationship analysis.

## Output Structure: JavaDetails Object

The JavaParser produces a comprehensive JavaDetails object containing:

### Core Structural Information:
- **classes**: Complete Java class definitions with methods, fields, and annotations
- **detected_layer**: Architectural layer classification (ASL, DSL, GSL, ISL)
- **architectural_pattern**: Business/Service/Data/Infrastructure layer detection
- **framework_hints**: Detected frameworks (Spring, JPA, JAX-RS, AspectJ, etc.)

### Security & API Information:
- **requires_security_roles**: Security annotations and role requirements
- **rest_endpoints**: Complete REST API endpoint definitions with HTTP methods
- **aop_pointcuts**: AspectJ cross-cutting concern configurations

### Legacy Pattern Detection (ct-hr-storm specific):
- **factory_methods**: Manager factory pattern methods (*MgrObject patterns)
- **manager_interfaces**: Manager interface implementations (I*Mgr patterns)
- **manager_usage**: Manager service dependencies and factory method calls
- **orchestration_info**: Multi-manager coordination patterns
- **is_manager_class**: Manager pattern classification

### Cross-File Relationship Mappings (CodeMapping objects):
1. **Method Calls**: Class-to-class method invocations with fully qualified names
2. **Dependency Injection**: @Autowired, @Inject, @Resource field dependencies
3. **Inheritance**: extends/implements relationships with package resolution
4. **Field References**: Type dependencies through field declarations
5. **Framework Relationships**: JPA mappings, Spring components, REST endpoints
6. **Manager Factory Patterns**: Legacy business service factory method calls
7. **AOP Advice**: AspectJ advice-to-target method mappings
8. **REST API Endpoints**: HTTP path-to-method mappings with security roles

## Code Flow Understanding Capabilities:

### Service Dependency Graph Construction:
Creates comprehensive dependency graphs showing how services interact:
- Controllers → Business Managers → Entity Managers → Database
- Cross-layer dependency injection patterns
- Factory method usage for legacy service instantiation

### Request Flow Tracing:
Enables end-to-end request tracing:
1. HTTP endpoint → Controller method
2. Controller → Business service calls
3. Business service → Data access layer
4. Security role requirements at each layer

### Cross-Cutting Concern Analysis:
- AspectJ pointcuts affecting multiple service methods
- Security annotations and role-based access control
- Transaction management and logging patterns

### Legacy Pattern Analysis (ct-hr-storm):
- Manager factory usage patterns (*Mgr.get*MgrObject())
- Multi-manager orchestration classes coordinating business services
- Custom architectural layer interactions (ASL/DSL/GSL/ISL)
- EJB integration patterns and JNDI lookups

### Modernization Planning Support:
The parsed data enables:
- **Dependency Analysis**: What components need refactoring together
- **Framework Migration**: Spring Boot conversion from legacy patterns
- **API Extraction**: REST endpoints ready for microservice extraction
- **Database Refactoring**: JPA relationships for data model modernization
- **Service Decomposition**: Manager dependencies for service boundary definition

## Integration with Pipeline Steps:
- **STEP03-05**: Configuration correlation, semantic analysis, relationship mapping
- **STEP06-07**: Component specification generation and architecture documentation
- **Output Generation**: Complete service definitions with dependencies and API specs

This comprehensive analysis transforms raw Java source code into structured, 
analyzable representations that enable automated requirements extraction and 
modernization planning for legacy enterprise applications.
"""

from typing import Any, Dict, List, Optional

from config import Config
from domain.config_details import CodeMapping, SemanticCategory
from domain.java_details import (
    EntityMappingDetails,
    JavaAnnotation,
    JavaClass,
    JavaDetails,
    JavaField,
    JavaMethod,
    JavaParameter,
)
from domain.source_inventory import (
    ArchitecturalLayerType,
    FileDetailsBase,
    FileInventoryItem,
    LayerType,
)
from domain.sql_details import SQLStatement, SQLStoredProcedureDetails

from .base_parser import BaseParser
from .java_reader import JavaReader


class JavaParser(BaseParser):
    """
    Java parser that uses JavaReader to extract structure and builds JavaDetails.
    
    Responsible for converting structural data to domain objects and generating
    CodeMapping objects for cross-file relationship analysis.
    """
    
    def __init__(self, config: Config, jpype_manager: Any = None) -> None:
        """
        Initialize Java parser.
        
        Args:
            config: Configuration instance
            jpype_manager: JPype manager for JVM operations
        """
        super().__init__(config)
        
        # Create Java reader for structural extraction
        self.reader = JavaReader(config, jpype_manager)
    
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
    
    def parse_file(self, file_item: FileInventoryItem, 
                   included_packages: Optional[List[str]] = None,
                   exclude_same_package: bool = False) -> FileDetailsBase:
        """
        Parse a file and extract structural information.
        
        Args:
            file_item: FileInventoryItem to parse
            included_packages: Optional list of packages to include in code mappings.
                             If provided, only mappings to classes in these packages will be created.
                             This filters out third-party library mappings.
            exclude_same_package: If True, exclude code mappings to other files within 
                                the same package as the current file.
            
        Returns:
            JavaDetails with extracted structural data and filtered code mappings
        """
        try:
            self.logger.debug("Starting to parse configuration file: %s (source_location: %s)", 
                             file_item.path, file_item.source_location)
            # Use reader to extract structural data
            parse_result = self.reader.parse_file(file_item.source_location, file_item.path)
            
            self.logger.debug("Parse result success: %s", parse_result.success)
            if parse_result.structural_data:
                self.logger.debug("Structural data keys: %s", list(parse_result.structural_data.keys()))
                self.logger.debug("Number of classes: %s", len(parse_result.structural_data.get('classes', [])))
            else:
                self.logger.debug("No structural data returned")
            
            if not parse_result.success:
                self.logger.error("Parse failed for file: %s", file_item.path)
                # Return empty JavaDetails on failure
                return JavaDetails()
            
            structural_data = parse_result.structural_data or {}
            
            # Convert structural data to JavaDetails
            java_details = self._build_java_details(structural_data)
            
            # Extract and set layer information from JavaReader analysis
            detected_layer_str = structural_data.get("detected_layer")
            architectural_pattern_str = structural_data.get("architectural_pattern")
            
            # Convert string values back to enums
            detected_layer = None
            if detected_layer_str:
                try:
                    detected_layer = LayerType(detected_layer_str)
                except ValueError:
                    self.logger.warning("Invalid detected_layer value: %s", detected_layer_str)
            
            architectural_pattern = None
            if architectural_pattern_str:
                try:
                    architectural_pattern = ArchitecturalLayerType(architectural_pattern_str)
                except ValueError:
                    self.logger.warning("Invalid architectural_pattern value: %s", architectural_pattern_str)
            
            # Add layer and architectural information to JavaDetails if available
            if detected_layer:
                java_details.detected_layer = detected_layer
            if architectural_pattern:
                java_details.architectural_pattern = architectural_pattern
            
            # Set framework hints from JavaReader analysis
            java_details.framework_hints = parse_result.framework_hints or []
            
            # Set security roles from structural data
            java_details.requires_security_roles = structural_data.get("security_roles", [])
            
            # Set REST endpoints from structural data
            java_details.rest_endpoints = structural_data.get("rest_endpoints", [])
            
            # Set AOP pointcuts from structural data
            java_details.aop_pointcuts = structural_data.get("aop_pointcuts", [])
            
            self.logger.debug("Reader result: structural_data_keys=%s, framework_hints=%s", 
                             list(parse_result.structural_data.keys()) if parse_result.structural_data else "None",
                             parse_result.framework_hints)

            # Generate code mappings from relationships with filtering
            code_mappings = self._generate_code_mappings(
                structural_data, 
                included_packages=included_packages,
                exclude_same_package=exclude_same_package
            )
            # NEW: Emit java_security mappings from structural_data.java_security_checks
            for sec in structural_data.get("java_security_checks", []) or []:
                try:
                    pkg = structural_data.get("package", "") or ""
                    cls = sec.get("class_name", "") or ""
                    mtd = sec.get("method_name", "") or ""
                    from_ref = f"{pkg}.{cls}.{mtd}" if pkg else f"{cls}.{mtd}" if cls else (structural_data.get("file_path") or "unknown")
                    attrs = {
                        "token_type": sec.get("token_type"),
                        "tokens": sec.get("tokens"),
                        "file_path": sec.get("file_path"),
                        "line": sec.get("line"),
                        "method_line_start": sec.get("method_line_start"),
                        "method_line_end": sec.get("method_line_end"),
                        "raw_text": sec.get("raw_text"),
                        "emits_xhtml": str(bool(sec.get("emits_xhtml")))
                    }
                    code_mappings.append(CodeMapping(
                        from_reference=from_ref,
                        to_reference=from_ref,
                        mapping_type="java_security",
                        framework="java",
                        semantic_category=SemanticCategory.CROSS_CUTTING,
                        attributes=attrs
                    ))
                except (KeyError, TypeError, ValueError):
                    continue
            java_details.code_mappings = code_mappings

            # self.logger.debug("Completed parsing file %s: framework=%s, code_mappings=%d, validation_rules=%d",
            #                  file_item.path, java_details.detected_framework,
            #                  len(java_details.code_mappings), len(java_details.validation_rules))

            return java_details
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to parse Java file %s: %s", file_item.path, str(e))
            return JavaDetails()
    
    def _build_java_details(self, structural_data: Dict[str, Any]) -> JavaDetails:
        """
        Build JavaDetails object from structural data.
        
        Args:
            structural_data: Raw structural data from reader
            
        Returns:
            JavaDetails object
        """
        java_classes = []
        
        # Convert class data to JavaClass objects
        for class_data in structural_data.get("classes", []):
            # Convert methods to JavaMethod objects
            java_methods = []
            for method_data in class_data.get("methods", []):
                # Convert parameters to JavaParameter objects
                java_parameters = []
                for param_data in method_data.get("parameters", []):
                    java_param = JavaParameter(
                        name=param_data.get("name", ""),
                        type=param_data.get("type", ""),
                        annotations=self._convert_annotations(param_data.get("annotations", []))
                    )
                    java_parameters.append(java_param)
                sql_statements = []
                sql_stored_procedures = []
                if method_data.get("sql_executions"):
                    for sql_exec in method_data["sql_executions"]:
                        if sql_exec.get("execution_type") == "sql_query":
                            if sql_exec.get("analyzed_statement"):
                                analyzed_stmt = sql_exec["analyzed_statement"]
                                sql_statements.append(analyzed_stmt)
                        elif sql_exec.get("execution_type") == "stored_procedure":
                            sql_stored_procedures.append(SQLStoredProcedureDetails(
                                procedure_name=sql_exec.get("stored_procedure", ""),
                                schema_name=sql_exec.get("schema_name", ""),
                                body=sql_exec.get("sql_statement", "")
                            ))

                java_method = JavaMethod(
                    name=method_data.get("name", ""),
                    visibility=method_data.get("visibility", "package"),
                    modifiers=method_data.get("modifiers", []),
                    return_type=method_data.get("return_type"),
                    parameters=java_parameters,
                    exceptions=method_data.get("exceptions", []),
                    annotations=self._convert_annotations(method_data.get("annotations", [])),
                    complexity_score=method_data.get("complexity_score"),
                    line_count=method_data.get("line_count"),
                    sql_statements=sql_statements,
                    sql_stored_procedures=sql_stored_procedures,
                )
                java_methods.append(java_method)
            
            # Convert fields to JavaField objects
            java_fields = []
            for field_data in class_data.get("fields", []):
                java_field = JavaField(
                    name=field_data.get("name", ""),
                    type=field_data.get("type", ""),
                    visibility=field_data.get("visibility", "package"),
                    modifiers=field_data.get("modifiers", []),
                    annotations=self._convert_annotations(field_data.get("annotations", [])),
                    initial_value=field_data.get("initial_value")
                )
                java_fields.append(java_field)
            
            entiy_mapping_details = None
            if class_data.get("entity_mapping"):
                enity_mapping = class_data["entity_mapping"]
                entiy_mapping_details = EntityMappingDetails(
                    entity_class=enity_mapping.get("class_name", ""),
                    table_name=enity_mapping.get("table_name", ""),
                )
            java_class = JavaClass(
                package_name=structural_data.get("package", ""),
                class_name=class_data.get("name", ""),
                class_type=class_data.get("type", "class"),
                modifiers=class_data.get("modifiers", []),
                methods=java_methods,
                fields=java_fields,
                annotations=self._convert_annotations(class_data.get("annotations", [])),
                imports=structural_data.get("imports", []),
                entity_mapping=entiy_mapping_details if entiy_mapping_details else None
            )
            java_classes.append(java_class)
        
        return JavaDetails(classes=java_classes)
    
    def _convert_annotations(self, annotation_data: List[Any]) -> List[JavaAnnotation]:
        """
        Convert annotation data to JavaAnnotation objects.
        
        Args:
            annotation_data: Raw annotation data
            
        Returns:
            List of JavaAnnotation objects
        """
        annotations = []
        for ann_data in annotation_data:
            if isinstance(ann_data, str):
                # Simple annotation name
                annotations.append(JavaAnnotation(name=ann_data))
            elif isinstance(ann_data, dict):
                # Annotation with attributes
                annotations.append(JavaAnnotation(
                    name=ann_data.get("name", ""),
                    attributes=ann_data.get("attributes", {}),
                    framework=ann_data.get("framework")
                ))
        return annotations
    
    def _should_include_mapping(self, target_ref: str, current_package: str,
                               included_packages: Optional[List[str]] = None,
                               exclude_same_package: bool = False) -> bool:
        """
        Determine if a code mapping should be included based on filtering criteria.
        
        Args:
            target_ref: The target reference (class or method being called)
            current_package: The package of the current file being parsed
            included_packages: Optional list of packages to include
            exclude_same_package: Whether to exclude same-package mappings
            
        Returns:
            True if the mapping should be included
        """
        # Extract package from target reference
        target_package = ""
        if "." in target_ref:
            # Handle cases like "com.example.Class.method" or "com.example.Class"
            parts = target_ref.split(".")
            # Find the last part that looks like a class name (starts with uppercase)
            # We go from the end backwards to find the class name, skipping the method name
            class_index = -1
            for i in range(len(parts) - 2, -1, -1):  # Skip last part (method) and go backwards
                if parts[i] and parts[i][0].isupper():
                    class_index = i
                    break
            
            if class_index > 0:
                target_package = ".".join(parts[:class_index])
            elif class_index == 0:
                # No package, just class name
                target_package = ""
            else:
                # If no uppercase found, try assuming the last part before method is class
                if len(parts) >= 2:
                    target_package = ".".join(parts[:-2])  # Remove class and method
                else:
                    target_package = ""
        
        # Apply package filtering
        if included_packages is not None:
            if not target_package:
                # No package means it's likely a local class or primitive - exclude
                return False
            
            # Check if target package starts with any of the included packages
            package_match = any(
                target_package.startswith(pkg) 
                for pkg in included_packages
            )
            if not package_match:
                return False
        
        # Apply same-package filtering
        if exclude_same_package and current_package and target_package == current_package:
            return False
        
        return True
    
    def _generate_code_mappings(self, structural_data: Dict[str, Any],
                               included_packages: Optional[List[str]] = None,
                               exclude_same_package: bool = False) -> List[CodeMapping]:
        """
        Generate CodeMapping objects from extracted cross-file relationships.
        
        Args:
            structural_data: Structural data with relationship information
            included_packages: Optional list of packages to include in mappings.
                             If provided, only mappings to classes in these packages will be created.
            exclude_same_package: If True, exclude mappings to other files within 
                                the same package as the current file.
            
        Returns:
            List of filtered CodeMapping objects representing high-level code flow
        """
        code_mappings = []
        package_name = structural_data.get("package", "")
        
        # Get primary class name for generating full qualified names
        primary_class = None
        if structural_data.get("classes"):
            primary_class = structural_data["classes"][0].get("name", "")
        
        # Convert method calls to CodeMapping objects
        for method_call in structural_data.get("method_calls", []):
            caller_class = method_call.get("caller_class", "")
            method_name = method_call.get("method_name", "")
            call_type = method_call.get("call_type", "instance")
            
            # Build source reference (current class.method calling)
            source_ref = f"{package_name}.{primary_class}" if package_name and primary_class else primary_class or "unknown"
            
            # Build target reference (called class.method)
            target_ref = f"{caller_class}.{method_name}"
            
            # Apply filtering
            if self._should_include_mapping(target_ref, package_name, included_packages, exclude_same_package):
                code_mappings.append(CodeMapping(
                    from_reference=source_ref,
                    to_reference=target_ref,
                    mapping_type="method_call",
                    framework="java",
                    semantic_category=SemanticCategory.METHOD_CALL,
                    attributes={"call_type": call_type}
                ))
        
        # Convert inheritance relationships to CodeMapping objects
        for inheritance in structural_data.get("inheritance_relationships", []):
            child_class = inheritance.get("child_class", "")
            parent_class = inheritance.get("parent_class", "")
            parent_interface = inheritance.get("parent_interface", "")
            relationship_type = inheritance.get("relationship_type", "")
            
            # Build full qualified names
            child_ref = f"{package_name}.{child_class}" if package_name else child_class
            parent_ref = parent_class or parent_interface
            
            # Apply filtering
            if self._should_include_mapping(parent_ref, package_name, included_packages, exclude_same_package):
                code_mappings.append(CodeMapping(
                    from_reference=child_ref,
                    to_reference=parent_ref,
                    mapping_type="inheritance",
                    framework="java",
                    semantic_category=SemanticCategory.INHERITANCE,
                    attributes={"relationship_type": relationship_type}
                ))
        
        # Convert annotation dependencies to CodeMapping objects
        for dependency in structural_data.get("annotation_dependencies", []):
            dependency_type = dependency.get("dependency_type", "")
            field_name = dependency.get("field_name", "")
            injection_type = dependency.get("injection_type", "")
            
            # Build source reference (current class)
            source_ref = f"{package_name}.{primary_class}" if package_name and primary_class else primary_class or "unknown"
            
            # Apply filtering
            if self._should_include_mapping(dependency_type, package_name, included_packages, exclude_same_package):
                code_mappings.append(CodeMapping(
                    from_reference=source_ref,
                    to_reference=dependency_type,
                    mapping_type="dependency_injection",
                    framework="java",
                    semantic_category=SemanticCategory.COMPOSITION,
                    attributes={
                        "field_name": field_name,
                        "injection_type": injection_type
                    }
                ))
        
        # Convert field references to CodeMapping objects
        for field_ref in structural_data.get("field_references", []):
            field_name = field_ref.get("field_name", "")
            referenced_type = field_ref.get("referenced_type", "")
            is_collection = field_ref.get("is_collection", False)
            
            # Build source reference (current class)
            source_ref = f"{package_name}.{primary_class}" if package_name and primary_class else primary_class or "unknown"
            
            # Apply filtering
            if self._should_include_mapping(referenced_type, package_name, included_packages, exclude_same_package):
                code_mappings.append(CodeMapping(
                    from_reference=source_ref,
                    to_reference=referenced_type,
                    mapping_type="field_reference",
                    framework="java",
                    semantic_category=SemanticCategory.COMPOSITION,
                    attributes={
                        "field_name": field_name,
                        "is_collection": str(is_collection)
                    }
                ))
        
        # Convert framework relationships to CodeMapping objects
        for framework_rel in structural_data.get("framework_relationships", []):
            relationship_type = framework_rel.get("relationship_type", "")
            framework = framework_rel.get("framework", "")
            
            # Build source reference (current class)
            source_ref = f"{package_name}.{primary_class}" if package_name and primary_class else primary_class or "unknown"
            
            if framework == "jpa":
                related_entity = framework_rel.get("related_entity", "")
                # Apply filtering
                if self._should_include_mapping(related_entity, package_name, included_packages, exclude_same_package):
                    code_mappings.append(CodeMapping(
                        from_reference=source_ref,
                        to_reference=related_entity,
                        mapping_type="jpa_relationship",
                        framework="jpa",
                        semantic_category=SemanticCategory.COMPOSITION,
                        attributes={"relationship_type": relationship_type}
                    ))
            elif framework == "business_service_layer":
                manager_class = framework_rel.get("manager_class", "")
                factory_method = framework_rel.get("factory_method", "")
                # Apply filtering
                if self._should_include_mapping(manager_class, package_name, included_packages, exclude_same_package):
                    code_mappings.append(CodeMapping(
                        from_reference=source_ref,
                        to_reference=manager_class,
                        mapping_type="manager_factory",
                        framework="business_service_layer",
                        semantic_category=SemanticCategory.METHOD_CALL,
                        attributes={"factory_method": factory_method}
                    ))

        # Convert entity mappings to CodeMapping objects
        for class_data in structural_data.get("classes", []):
            if class_data.get("entity_mapping"):
                entity_mapping = class_data.get("entity_mapping")
                if entity_mapping:
                    class_name = class_data.get("name", "")
                    table_name = entity_mapping.get("table_name", "")
                    mapping_type = entity_mapping.get("mapping_type", "entity_manager")
                    
                    # Build source reference (entity manager class)
                    source_ref = f"{package_name}.{class_name}" if package_name else class_name
                    
                    code_mappings.append(CodeMapping(
                        from_reference=source_ref,
                        to_reference=table_name,
                        mapping_type="entity_table_mapping",
                        framework="database",
                        semantic_category=SemanticCategory.DATA_ACCESS,
                        attributes={
                            "table_name": table_name,
                            "mapping_type": mapping_type,
                            "entity_class": class_name
                        }
                    ))
        
        # Convert SQL executions to CodeMapping objects
        for class_data in structural_data.get("classes", []):
            class_name = class_data.get("name", "")
            for method_data in class_data.get("methods", []):
                method_name = method_data.get("name", "")
                sql_executions = method_data.get("sql_executions", [])
                
                for sql_exec in sql_executions:
                    execution_type = sql_exec.get("execution_type", "")
                    
                    # Build source reference (class.method)
                    source_ref = f"{package_name}.{class_name}.{method_name}" if package_name else f"{class_name}.{method_name}"
                    
                    if execution_type == "sql_query" and sql_exec.get("analyzed_statement"):
                        # SQL statement execution
                        sql_statement = sql_exec["analyzed_statement"]
                        object_name = sql_statement.object_name
                        statement_type = sql_statement.statement_type
                        
                        if sql_statement and object_name:
                            code_mappings.append(CodeMapping(
                                from_reference=source_ref,
                                to_reference=object_name,
                                mapping_type="sql_table_access",
                                framework="database",
                                semantic_category=SemanticCategory.DATA_ACCESS,
                                attributes={
                                    "statement_type": statement_type,
                                    "object_type": sql_statement.object_type,
                                    "schema_name": sql_statement.schema_name,
                                    "logical_database": sql_statement.logical_database,
                                    "sql_statement": sql_statement.statement_text[:200] + "..." if len(sql_statement.statement_text) > 200 else sql_statement.statement_text
                                }
                            ))
                    
                    elif execution_type == "stored_procedure":
                        # Stored procedure call
                        procedure_name = sql_exec.get("stored_procedure", "")
                        
                        if procedure_name:
                            code_mappings.append(CodeMapping(
                                from_reference=source_ref,
                                to_reference=procedure_name,
                                mapping_type="stored_procedure_call",
                                framework="database",
                                semantic_category=SemanticCategory.DATA_ACCESS,
                                attributes={
                                    "procedure_name": procedure_name,
                                    "schema_name": sql_exec.get("schema_name", ""),
                                    "execution_type": "stored_procedure"
                                }
                            ))

        # Convert REST endpoints to CodeMapping objects
        for rest_endpoint in structural_data.get("rest_endpoints", []):
            path = rest_endpoint.get("path", "")
            http_method = rest_endpoint.get("http_method", "")
            class_name = rest_endpoint.get("class_name", "")
            method_name = rest_endpoint.get("method_name", "")
            produces = rest_endpoint.get("produces", [])
            consumes = rest_endpoint.get("consumes", [])
            security_roles = rest_endpoint.get("security_roles", [])
            
            # Build full qualified class name
            target_ref = f"{package_name}.{class_name}.{method_name}" if package_name else f"{class_name}.{method_name}"
            
            code_mappings.append(CodeMapping(
                from_reference=path,
                to_reference=target_ref,
                mapping_type="rest_endpoint",
                framework="jaxrs",
                semantic_category=SemanticCategory.ENTRY_POINT,
                attributes={
                    "http_method": http_method,
                    "produces": ",".join(produces),
                    "consumes": ",".join(consumes),
                    "security_roles": ",".join(security_roles)
                }
            ))
        
        # Convert AOP pointcuts to CodeMapping objects
        for pointcut in structural_data.get("aop_pointcuts", []):
            aspect_class = pointcut.get("aspect_class", "")
            advice_method = pointcut.get("advice_method", "")
            advice_type = pointcut.get("advice_type", "")
            target_class = pointcut.get("target_class", "")
            target_method = pointcut.get("target_method", "")
            pointcut_expression = pointcut.get("pointcut_expression", "")
            
            # Build source reference (aspect class.advice method)
            source_ref = f"{package_name}.{aspect_class}.{advice_method}" if package_name else f"{aspect_class}.{advice_method}"
            
            # Build target reference
            target_ref = f"{target_class}.{target_method}" if target_method else target_class
            
            # Apply filtering for target
            if self._should_include_mapping(target_ref, package_name, included_packages, exclude_same_package):
                code_mappings.append(CodeMapping(
                    from_reference=source_ref,
                    to_reference=target_ref,
                    mapping_type="aop_advice",
                    framework="aspectj",
                    semantic_category=SemanticCategory.CROSS_CUTTING,
                    attributes={
                        "advice_type": advice_type,
                        "pointcut_expression": pointcut_expression
                    }
                ))
        
        # Convert manager pattern factory methods to CodeMapping objects
        for factory_method in structural_data.get("factory_methods", []):
            factory_name = factory_method.get("name", "")
            return_type = factory_method.get("return_type", "")
            matched_pattern = factory_method.get("matched_pattern", "")
            
            # Build source reference (factory method)
            source_ref = f"{package_name}.{primary_class}.{factory_name}" if package_name and primary_class else f"{primary_class}.{factory_name}" if primary_class else factory_name
            
            code_mappings.append(CodeMapping(
                from_reference=source_ref,
                to_reference=return_type,
                mapping_type="factory_method",
                framework="custom",
                semantic_category=SemanticCategory.METHOD_CALL,
                attributes={
                    "factory_pattern": "true",
                    "return_type": return_type,
                    "matched_pattern": matched_pattern
                }
            ))
        
        # Convert manager interface implementations to CodeMapping objects
        for interface in structural_data.get("manager_interfaces", []):
            interface_name = interface.get("interface", "")
            
            # Build source reference (implementing class)
            source_ref = f"{package_name}.{primary_class}" if package_name and primary_class else primary_class or "unknown"
            
            code_mappings.append(CodeMapping(
                from_reference=source_ref,
                to_reference=interface_name,
                mapping_type="interface_implementation",
                framework="custom",
                semantic_category=SemanticCategory.INHERITANCE,
                attributes={
                    "manager_interface": "true",
                    "interface_name": interface_name
                }
            ))
        
        # Convert manager usage patterns to CodeMapping objects
        for usage in structural_data.get("manager_usage", []):
            manager_class = usage.get("manager_class", "")
            factory_method = usage.get("factory_method", "")
            usage_type = usage.get("usage_type", "")
            matched_pattern = usage.get("matched_pattern", "")
            
            # Build source reference (current class)
            source_ref = f"{package_name}.{primary_class}" if package_name and primary_class else primary_class or "unknown"
            
            # Build target reference (manager factory method)
            target_ref = f"{manager_class}.{factory_method}"
            
            # Apply filtering
            if self._should_include_mapping(target_ref, package_name, included_packages, exclude_same_package):
                code_mappings.append(CodeMapping(
                    from_reference=source_ref,
                    to_reference=target_ref,
                    mapping_type="service_dependency",
                    framework="custom",
                    semantic_category=SemanticCategory.COMPOSITION,
                    attributes={
                        "usage_type": usage_type,
                        "manager_class": manager_class,
                        "factory_method": factory_method,
                        "matched_pattern": matched_pattern
                    }
                ))
        
        # Convert orchestration patterns to CodeMapping objects
        orchestration_info = structural_data.get("orchestration_info", {})
        if orchestration_info.get("is_orchestrator", False):
            # Build source reference (orchestrator class)
            source_ref = f"{package_name}.{primary_class}" if package_name and primary_class else primary_class or "unknown"
            
            code_mappings.append(CodeMapping(
                from_reference=source_ref,
                to_reference="ORCHESTRATION_PATTERN",
                mapping_type="orchestration",
                framework="custom",
                semantic_category=SemanticCategory.CROSS_CUTTING,
                attributes={
                    "orchestration_score": str(orchestration_info.get("orchestration_score", 0)),
                    "unique_manager_count": str(orchestration_info.get("unique_manager_count", 0)),
                    "pattern_type": "multi_manager_coordination"
                }
            ))
        
        return code_mappings
