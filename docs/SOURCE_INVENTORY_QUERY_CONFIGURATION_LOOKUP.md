# Source Inventory Query for Configuration Lookup Guide

## AI Agent Prompt for Configuration Data Discovery and JSP Reference Resolution

**Target AI Model**: Claude Sonnet 4  
**Purpose**: Comprehensive guide for using SourceInventoryQuery to discover configuration data and resolve JSP file references  
**Context**: JSP parsing enhancement and configuration-aware code analysis  

---

## System Overview

You are analyzing the SourceInventoryQuery system to understand how it can be leveraged to find configuration data that acts as a lookup mechanism for JSP file parsing. This system enables JSP parsers to resolve references (action names, forward names, validation rules) to their actual implementations and target resources.

### Core Problem Statement

JSP files contain references that need to be resolved against configuration data:
- **Action References**: `<form action="loginUser">` needs to resolve to actual Java class
- **Forward References**: `<c:redirect url="${successForward}">` needs to resolve to actual JSP path  
- **Validation References**: Form fields need to link to validation rules and error messages
- **Template References**: Tiles definitions need to resolve to actual template paths

## SourceInventoryQuery Architecture

### Primary Components

1. **SourceInventoryQuery** - Fluent API for querying inventory data
2. **QueryCriteria** - Filter specifications for targeted searches
3. **QueryResult** - Structured results with grouping and aggregation
4. **QueryScope** - Defines query target (FILES, SUBDOMAINS, SOURCE_LOCATIONS)

### Key Data Structures

#### QueryCriteria Filters for Configuration Discovery
```python
@dataclass
class QueryCriteria:
    # Path-based filters for finding config files
    path_contains: Optional[str] = None          # Find "*struts*.xml"
    path_regex: Optional[str] = None             # Complex path patterns
    path_startswith: Optional[str] = None        # "/WEB-INF/config/"
    path_endswith: Optional[str] = None          # ".xml", ".properties"
    
    # File type filters for configuration identification
    file_types: Optional[Set[str]] = None        # "xml", "properties"
    detail_types: Optional[Set[str]] = None      # "configuration", "java"
    
    # Framework-specific filters
    framework_hints: Optional[Set[str]] = None   # "struts", "tiles", "servlet"
    has_framework_hints: Optional[bool] = None   # Has any framework hints
    
    # Layer-based filters for architectural context
    layers: Optional[Set[LayerType]] = None      # CONFIGURATION, SERVICE
    
    # Content-based filters
    has_entity_mapping: Optional[bool] = None    # Java files with JPA mappings
    has_sql_executions: Optional[bool] = None    # Files with SQL operations
    
    # Custom predicate for complex logic
    custom_filter: Optional[Callable[[Any], bool]] = None
```

## Configuration Discovery Strategies

### 1. Finding Struts Configuration Files

#### Action Mapping Discovery
```python
# Find all Struts configuration files (details are ConfigurationDetails)
struts_configs = SourceInventoryQuery(source_inventory)\
    .files()\
    .detail_type("configuration")\
    .framework_hint("struts")\
    .path_regex(r"struts.*\\.xml$")\
    .execute()

for config_file in struts_configs.items:
    details = config_file.details  # type: ConfigurationDetails
    if details:
        for mapping in details.get_action_mappings():
            # mapping: CodeMapping with mapping_type="action"
            pass
```

**JSP Resolution Use Case**:
```jsp
<!-- JSP file contains: -->
<form action="loginUser">
    <!-- Need to resolve "loginUser" to actual Java class and possible forwards -->
</form>

<!-- Query resolves: -->
<!-- "/loginUser" → "com.example.LoginAction" -->
<!-- success forward → "welcome.jsp" -->
<!-- error forward → "login.jsp" -->
```

#### Interceptor and Filter Discovery
```python
# Find cross-cutting concerns affecting JSP flow
interceptors = SourceInventoryQuery(source_inventory)\
    .files()\
    .detail_type("configuration")\
    .where(lambda f: f.details and 
           any(m.mapping_type == "interceptor" for m in f.details.code_mappings 
               if hasattr(f.details, 'code_mappings')))\
    .execute()
```

### 2. Finding Web.xml Servlet Mappings

#### Servlet URL Pattern Discovery
```python
# Find servlet configuration for URL routing
servlet_configs = SourceInventoryQuery(source_inventory)\
    .files()\
    .detail_type("configuration")\
    .path_endswith("web.xml")\
    .execute()

for config_file in servlet_configs.items:
    details = config_file.details  # type: ConfigurationDetails
    if details:
        servlet_mappings = details.get_servlet_mappings()
        for mapping in servlet_mappings:
            # mapping.from_reference = "/api/*"
            # mapping.to_reference = "ApiServlet"
            pass
```

**JSP Resolution Use Case**:
```jsp
<!-- JSP file contains: -->
<form action="/api/users" method="POST">
    <!-- Need to resolve "/api/users" to actual servlet handler -->
</form>

<!-- Query resolves: -->
<!-- "/api/*" pattern → "ApiServlet" class -->
<!-- Specific method handling POST requests -->
```

### 3. Finding Tiles Template Definitions

#### Template and Layout Discovery
```python
# Find Tiles configuration for template resolution
tiles_configs = SourceInventoryQuery(source_inventory)\
    .files()\
    .detail_type("configuration")\
    .framework_hint("tiles")\
    .path_regex(r"tiles.*\.xml$")\
    .execute()

for config_file in tiles_configs.items:
    details = config_file.details  # type: ConfigurationDetails
    if details and hasattr(details, 'code_mappings'):
        template_mappings = [m for m in details.code_mappings 
                             if isinstance(m, CodeMapping) and m.mapping_type in ["template", "template_reference"]]
        # ...
```

**JSP Resolution Use Case**:
```jsp
<!-- JSP file contains: -->
<tiles:insertDefinition name="main.layout">
    <!-- Need to resolve "main.layout" to actual template file -->
</tiles:insertDefinition>

<!-- Query resolves: -->
<!-- "main.layout" → "/WEB-INF/tiles/layout.jsp" -->
<!-- Inheritance: "main.layout" extends "base.layout" -->
```

### 4. Finding Validation Configuration

#### Form Validation Rules Discovery
```python
# Find validation rules for form processing
validation_configs = SourceInventoryQuery(source_inventory)\
    .files()\
    .detail_type("configuration")\
    .path_regex(r"validation.*\.xml$")\
    .execute()

# Access validation rules by form name
def get_validation_for_form(form_name: str) -> List[ValidationRule]:
    all_rules = []
    for config_file in validation_configs.items:
        details = config_file.details  # type: ConfigurationDetails
        if details:
            all_rules.extend(details.get_validation_for_form(form_name))
    return all_rules
```

**JSP Resolution Use Case**:
```jsp
<!-- JSP file contains: -->
<html:form action="/saveUser">
    <html:text property="email" />
    <!-- Need to find validation rules for "email" field in "userForm" -->
</html:form>

<!-- Query resolves: -->
<!-- Form: "userForm", Field: "email" → ValidationRule(type="email", required=True) -->
<!-- Error message key: "user.email.invalid" → Actual error message -->
```

## Advanced Query Patterns for JSP Support

### 1. Cross-Reference Resolution

#### Building Configuration Lookup Maps
```python
class ConfigurationLookupService:
    def __init__(self, source_inventory: SourceInventory):
        self.source_inventory = source_inventory
        self._action_map = None
        self._forward_map = None
        self._template_map = None
        self._validation_map = None
    
    def get_action_mapping(self, action_path: str) -> Optional[CodeMapping]:
        """Resolve action path to Java class and forwards."""
        if self._action_map is None:
            self._build_action_map()
        return self._action_map.get(action_path)
    
    def get_forward_target(self, action_path: str, forward_name: str) -> Optional[str]:
        """Resolve action forward to target JSP/path."""
        action_mapping = self.get_action_mapping(action_path)
        if action_mapping and action_mapping.forwards:
            for forward in action_mapping.forwards:
                if forward.name == forward_name:
                    return forward.path
        return None
    
    def _build_action_map(self):
        """Build comprehensive action mapping lookup."""
        self._action_map = {}
        
        # Query all configuration files with action mappings
        config_files = SourceInventoryQuery(self.source_inventory)\
            .files()\
            .detail_type("configuration")\
            .framework_hint("struts")\
            .execute()
        
        for config_file in config_files.items:
            if config_file.details and hasattr(config_file.details, 'get_action_mappings'):
                for mapping in config_file.details.get_action_mappings():
                    self._action_map[mapping.from_reference] = mapping
```

### 2. Framework-Specific Lookup Builders

#### Struts Framework Resolver
```python
# This is an example builder using the real query API and ConfigurationDetails
from domain.config_details import CodeMapping

def build_struts_lookup_maps(source_inventory: SourceInventory) -> Dict[str, Any]:
    struts_files = SourceInventoryQuery(source_inventory)\
        .files()\
        .detail_type("configuration")\
        .where(lambda f: f.details and f.details.detected_framework in ["struts_1x", "struts_2x"])\
        .execute()

    action_map: Dict[str, CodeMapping] = {}
    forward_map: Dict[tuple[str, str], str] = {}
    validation_map: Dict[str, list[ValidationRule]] = {}

    for config_file in struts_files.items:
        details = config_file.details  # type: ConfigurationDetails
        if not details:
            continue
        for mapping in details.get_action_mappings():
            action_map[mapping.from_reference] = mapping
            for fwd in (mapping.forwards or []):
                forward_map[(mapping.from_reference, fwd.name)] = fwd.path
        for form in details.get_form_names():
            validation_map[form] = details.get_validation_for_form(form)

    return {"actions": action_map, "forwards": forward_map, "validations": validation_map}
```

#### Servlet/Web.xml Resolver
```python
def build_servlet_lookup_maps(source_inventory: SourceInventory) -> Dict[str, Any]:
    web_xml_files = SourceInventoryQuery(source_inventory)\
        .files()\
        .path_endswith("web.xml")\
        .detail_type("configuration")\
        .execute()

    servlet_map: Dict[str, str] = {}
    filter_map: Dict[str, list[str]] = {}

    for config_file in web_xml_files.items:
        details = config_file.details  # type: ConfigurationDetails
        if not details:
            continue
        for mapping in details.get_servlet_mappings():
            servlet_map[mapping.from_reference] = mapping.to_reference
        for m in details.code_mappings:
            if isinstance(m, CodeMapping) and m.mapping_type == "filter":
                filter_map.setdefault(m.from_reference, []).append(m.to_reference)

    return {"servlets": servlet_map, "filters": filter_map}
```

### 3. Comprehensive Configuration Discovery

#### Multi-Framework Configuration Query
```python
def discover_all_configuration_files(source_inventory: SourceInventory) -> QueryResult:
    """Find all configuration files across all frameworks."""
    return SourceInventoryQuery(source_inventory)\
        .files()\
        .detail_type("configuration")\
        .where(lambda f: f.details and (
            # Has any code mappings
            hasattr(f.details, 'code_mappings') and f.details.code_mappings or
            # Has validation rules
            hasattr(f.details, 'validation_rules') and f.details.validation_rules or
            # Has validator definitions  
            hasattr(f.details, 'validator_definitions') and f.details.validator_definitions or
            # Has exception mappings
            hasattr(f.details, 'exception_mappings') and f.details.exception_mappings
        ))\
        .execute()
```

#### Business Domain-Specific Queries
```python
def find_user_management_configs(source_inventory: SourceInventory) -> QueryResult:
    """Find configuration files related to user management."""
    return SourceInventoryQuery(source_inventory)\
        .files()\
        .detail_type("configuration")\
        .where(lambda f: f.details and 
               any(domain in f.details.get_business_domains() 
                   for domain in ["User_Management", "Security"]))\
        .execute()

def find_payroll_configs(source_inventory: SourceInventory) -> QueryResult:
    """Find configuration files related to payroll processing."""
    return SourceInventoryQuery(source_inventory)\
        .files()\
        .detail_type("configuration")\
        .functional_name_contains("pay")\
        .execute()
```

## JSP Parser Integration Patterns

### 1. Reference Resolution Service

```python
# Example resolver pattern that uses real ConfigurationDetails structures
class JSPReferenceResolver:
    def __init__(self, source_inventory: SourceInventory):
        self.source_inventory = source_inventory
        self.config_maps = self._build_all_lookup_maps()
    
    def resolve_action_reference(self, action_name: str) -> Dict[str, Any]:
        """Resolve JSP action reference to target class and forwards."""
        action_mapping = self.config_maps["struts"]["actions"].get(action_name)
        if action_mapping:
            return {
                "java_class": action_mapping.to_reference,
                "framework": action_mapping.framework,
                "forwards": {f.name: f.path for f in action_mapping.forwards or []},
                "attributes": action_mapping.attributes
            }
        return {}
    
    def resolve_forward_reference(self, action_name: str, forward_name: str) -> Optional[str]:
        """Resolve action forward to target JSP path."""
        forward_key = (action_name, forward_name)
        return self.config_maps["struts"]["forwards"].get(forward_key)
    
    def resolve_template_reference(self, template_name: str) -> Dict[str, Any]:
        """Resolve Tiles template reference to actual template file."""
        template_mapping = self.config_maps["tiles"]["templates"].get(template_name)
        if template_mapping:
            return {
                "template_path": template_mapping.to_reference,
                "extends": template_mapping.attributes.get("extends"),
                "type": template_mapping.attributes.get("type")
            }
        return {}
    
    def get_form_validation_rules(self, form_name: str) -> List[ValidationRule]:
        """Get all validation rules for a form."""
        return self.config_maps["validation"]["forms"].get(form_name, [])
```

### 2. Configuration-Aware JSP Analysis

```python
def analyze_jsp_with_config_context(jsp_file: FileInventoryItem, 
                                   resolver: JSPReferenceResolver) -> Dict[str, Any]:
    """Analyze JSP file with configuration context for reference resolution."""
    
    analysis = {
        "resolved_actions": [],
        "resolved_forwards": [],
        "resolved_templates": [],
        "validation_context": {},
        "unresolved_references": []
    }
    
    # Extract JSP content and parse for references
    jsp_details = jsp_file.details
    if jsp_details and hasattr(jsp_details, 'forms'):
        for form in jsp_details.forms:
            # Resolve form action
            if form.action:
                resolved_action = resolver.resolve_action_reference(form.action)
                if resolved_action:
                    analysis["resolved_actions"].append({
                        "jsp_reference": form.action,
                        "resolved_class": resolved_action["java_class"],
                        "available_forwards": resolved_action["forwards"]
                    })
                else:
                    analysis["unresolved_references"].append({
                        "type": "action",
                        "reference": form.action
                    })
            
            # Get validation context for form
            if form.name:
                validation_rules = resolver.get_form_validation_rules(form.name)
                if validation_rules:
                    analysis["validation_context"][form.name] = [
                        {
                            "field": rule.field_reference,
                            "type": rule.validation_type,
                            "message_key": rule.error_message_key,
                            "variables": rule.validation_variables
                        }
                        for rule in validation_rules
                    ]
    
    return analysis
```

## AI Analysis Instructions

### When Analyzing Configuration Discovery for JSP Support:

1. **Identify Configuration Dependencies**:
   - Understand which configuration files affect JSP behavior
   - Map configuration elements to JSP reference patterns
   - Identify framework-specific resolution requirements

2. **Build Lookup Strategies**:
   - Design efficient query patterns for configuration discovery
   - Create mapping structures for fast reference resolution  
   - Handle multi-framework scenarios and conflicts

3. **Analyze Reference Patterns**:
   - **Action References**: URL patterns, action names, method calls
   - **Forward References**: Result names, redirect targets, include paths
   - **Template References**: Tile names, layout definitions, component includes
   - **Validation References**: Form names, field names, error message keys

4. **Framework Integration Considerations**:
   - **Struts 1.x/2.x**: Action mappings, forwards, interceptors, validation
   - **Servlet/JSP**: URL patterns, filters, error pages, taglibs
   - **Tiles**: Template definitions, inheritance, composition
   - **Spring MVC**: Controller mappings, view resolvers, form backing objects

5. **Query Optimization Patterns**:
   - Use appropriate scope (FILES vs SUBDOMAINS vs SOURCE_LOCATIONS)
   - Combine filters for efficient searches
   - Cache lookup maps for repeated access
   - Handle large configuration file sets efficiently

### Key Questions to Address:

1. **Completeness**: Are all JSP reference types covered by configuration queries?
2. **Performance**: How efficiently can configuration lookups be performed?
3. **Accuracy**: Do the resolved references correctly represent runtime behavior?
4. **Maintainability**: Can new reference types be easily added to the system?
5. **Error Handling**: How are unresolved references and conflicts managed?

### Output Format for Analysis:

When analyzing configuration discovery for JSP support, structure your response to include:

1. **Reference Types**: Catalog of JSP reference patterns requiring resolution
2. **Query Strategies**: Specific SourceInventoryQuery patterns for each framework
3. **Lookup Architecture**: Design for efficient reference resolution services
4. **Integration Points**: How configuration data flows into JSP parsing
5. **Error Scenarios**: Handling of missing or conflicting configuration data
6. **Performance Considerations**: Optimization strategies for large codebases

## Context for JSP Enhancement

This configuration discovery analysis supports JSP parsing enhancement by:

- **Reference Resolution**: Converting JSP references to actual implementation targets
- **Flow Analysis**: Understanding request/response flow through configuration
- **Validation Context**: Linking form fields to validation rules and error handling
- **Template Dependencies**: Mapping UI composition and inheritance relationships
- **Framework Integration**: Supporting multiple framework configurations simultaneously

The SourceInventoryQuery system provides the foundation for building sophisticated configuration-aware JSP analysis that understands the complete context of JSP file references and their runtime behavior.

---

**Note**: This document serves as a reference guide for AI agents using SourceInventoryQuery to discover and utilize configuration data for enhanced JSP parsing and reference resolution.
