# STEP06: Relationship Mapping Implementation

**Version:** 1.0  
**Date:** July 22, 2025  
**Purpose:** Detailed implementation specification for component relationship mapping and service interaction analysis

---

## 📋 Step Overview

### **Primary Responsibility**
Component relationship mapping, service interaction analysis, dependency tracking, and data flow mapping between identified components to establish comprehensive system interconnections.

### **Processing Context**
- **Pipeline Position:** Fifth step in the CodeSight pipeline
- **Dependencies:** STEP01 (file inventory), STEP02 (AST structure), STEP03 (configuration), STEP04 (semantic analysis)
- **Processing Time:** 20-25% of total pipeline time
- **Confidence Level:** 80-85% (code-based relationship detection)

### **Data Flow Integration**

#### **Data Requirements from Previous Steps:**

**From STEP01 (File System Analysis):**
- **Package structure analysis** - For dependency organization understanding
- **File inventory with Unix relative paths** - For cross-reference analysis
- **Project-specific architectural patterns** - Custom patterns (asl, dsl, gsl, isl) for enhanced relationship context

**From STEP02 (AST Structural Extraction):**
- **Cross-reference mappings** - For detailed relationship analysis
- **Method call graphs** - For service interaction mapping
- **Dependency injection patterns** - For component relationship validation
- **Import statements and dependencies** - For explicit dependency tracking

**From STEP03 (Pattern & Configuration Analysis):**
- **Service configuration mappings** - Spring bean configurations for dependency analysis
- **Database configuration details** - Connection patterns for integration analysis
- **Cross-cutting concern configurations** - Security, transaction patterns for relationship context

**From STEP04 (LLM Semantic Analysis):**
- **Enhanced component descriptions** - Business purpose and functionality for relationship context
- **Domain classifications** - Business domain groupings for logical relationship mapping
- **Functional requirements** - Detailed business rules for dependency validation
- **Component confidence adjustments** - LLM-validated confidence scores

#### **Data Provided to Subsequent Steps:**

**For STEP07 (Output Generation & Validation):**
- **Complete service interaction mappings** - All component relationships for final schema
- **Data flow analysis** - Information flow patterns for architecture documentation
- **Dependency graphs** - Comprehensive component dependencies for validation
- **Integration points** - External system connections for final output

---

## ⚙️ Design Principles

### **Project and Language Agnostic Design**
- **All relationship detection logic must be framework and language agnostic**
- **Dependency analysis patterns are configurable through YAML rules**
- **Relationship types and patterns are defined in configuration, not hard-coded**
- **Cross-reference analysis supports multiple programming languages through templates**
- **Project-specific relationship patterns are handled through configuration overrides**

### **Standardized Path Handling**
- **All component references in relationships must use Unix-style relative paths**
- **File paths in dependency mappings must be relative to project root directory**
- **No absolute paths are permitted in relationship data or outputs**
- **Cross-reference paths must maintain Unix relative path format**
- **Path normalization is applied consistently with all previous steps**

### **Configuration System Compliance**
- **Inherits dual YAML configuration system from previous steps**
- **Respects project-specific relationship patterns from config-<project>.yaml**
- **Supports custom architectural relationship rules per project**
- **All relationship detection rules are driven by YAML configuration**

---

## 🎯 Requirements Alignment

### **Functional Requirements Covered**
- **FR-004: Relationship Mapping** - Complete mapping of component interactions and dependencies
- **FR-002: Comprehensive Component Analysis** - Enhanced component understanding through relationships
- **FR-005: Project and Language Agnostic Design** - All code must be project and language agnostic
- **FR-006: Standardized Path Handling** - All paths must be relative to root project directory using Unix format
- **FR-007: Project-Specific Architectural Overrides** - Support custom relationship patterns per project

### **Target Schema Attributes**
Based on SCHEMA_ATTRIBUTE_MAPPING.md, STEP06 extracts:

| Attribute | Confidence | Method |
|-----------|------------|--------|
| `components[].service_interactions` | 85% | Code analysis + configuration validation + LLM enhancement |
| `metadata.extraction_summary.service_interactions_mapped` | 95% | Direct count of identified relationships |
| `components[].technical_requirements.dependencies` | 90% | Import analysis + configuration mapping + dependency injection |
| `components[].technical_requirements.integration_points` | 80% | External system connection analysis |
| `components[].functional_requirements.data_flow` | 75% | Method call analysis + parameter tracking |

---

## 📥 Input Specifications

### **Primary Inputs**
- **STEP01 Output** - `step01_output.json` with file inventory and package structure
- **STEP02 Output** - `step02_output.json` with AST structure and cross-references
- **STEP03 Output** - `step03_output.json` with configuration mappings
- **STEP04 Output** - `step04_output.json` with enhanced component analysis
- **YAML Configuration** - Relationship detection patterns and rules

### **Configuration Requirements**

#### **Enhanced config.yaml (Common Relationship Configuration)**
```yaml
# Relationship Detection Rules
relationship_detection:
  method_call_patterns:
    - "direct_method_call"
    - "interface_implementation"
    - "abstract_method_override"
    - "callback_registration"
  
  dependency_patterns:
    spring_injection:
      - "@Autowired"
      - "@Inject"
      - "@Resource"
      - "constructor_injection"
    configuration_based:
      - "xml_bean_reference"
      - "properties_reference"
      - "jndi_lookup"
  
  interaction_types:
    - "synchronous_call"
    - "asynchronous_call"
    - "event_publishing"
    - "message_sending"
    - "database_access"
    - "external_api_call"
    - "file_system_access"

# Data Flow Analysis
data_flow_analysis:
  parameter_tracking: true
  return_value_tracking: true
  exception_flow_tracking: true
  transaction_boundary_tracking: true
  
  data_transformation_patterns:
    - "mapper_transformation"
    - "converter_transformation"
    - "serialization_transformation"
    - "validation_transformation"

# Integration Point Detection
integration_detection:
  external_system_indicators:
    - "http_client"
    - "database_connection"
    - "jms_connection"
    - "web_service_client"
    - "rest_client"
    - "soap_client"
    - "file_system_access"
    - "email_service"
  
  persistence_patterns:
    - "jpa_repository"
    - "hibernate_dao"
    - "jdbc_template"
    - "mybatis_mapper"

# Relationship Confidence Scoring
confidence_scoring:
  direct_code_reference: 0.95
  configuration_based: 0.85
  inferred_from_pattern: 0.70
  llm_suggested: 0.60
  
  cross_validation_boost: 0.1
  multiple_evidence_boost: 0.15
```

#### **Enhanced config-<project>.yaml (Project-Specific Relationship Configuration)**
```yaml
# Project-Specific Relationship Patterns
project_relationship_patterns:
  custom_service_patterns:
    - "storm_service_call"
    - "asl_to_dsl_call"
    - "dsl_to_gsl_call"
    - "gsl_to_isl_call"
  
  custom_integration_patterns:
    - "storm_database_access"
    - "hr_system_integration"
    - "nbcu_enterprise_service"

# Custom Architectural Relationship Rules (asl, dsl, gsl, isl)
architectural_relationship_rules:
  asl_relationships:
    allowed_outbound:
      - "dsl"  # Application can call Domain services
      - "gsl"  # Application can call Generic utilities
      - "screen" # Application can interact with UI components
    restricted_outbound:
      - "isl"  # Application should not directly call Infrastructure
    typical_patterns:
      - "workflow_orchestration"
      - "user_session_management"
      - "ui_controller_coordination"
  
  dsl_relationships:
    allowed_outbound:
      - "gsl"  # Domain can call Generic utilities
      - "isl"  # Domain can call Infrastructure for persistence
    restricted_outbound:
      - "asl"  # Domain should not call Application layer
      - "screen" # Domain should not interact with UI
    typical_patterns:
      - "business_rule_enforcement"
      - "entity_validation"
      - "domain_service_coordination"
  
  gsl_relationships:
    allowed_outbound:
      - "isl"  # Generic can call Infrastructure
    restricted_outbound:
      - "asl"  # Generic should not call Application
      - "dsl"  # Generic should not call Domain
    typical_patterns:
      - "utility_service_provision"
      - "cross_cutting_concerns"
      - "shared_functionality"
  
  isl_relationships:
    allowed_outbound:
      - "external_systems"  # Infrastructure can call external systems
    restricted_outbound:
      - "asl"  # Infrastructure should not call Application
      - "dsl"  # Infrastructure should not call Domain
      - "gsl"  # Infrastructure should not call Generic
    typical_patterns:
      - "data_persistence"
      - "external_integration"
      - "system_infrastructure"

# Business Domain Relationship Rules
business_domain_relationships:
  hr_employee_management:
    related_domains:
      - "time_tracking_system"
      - "payroll_processing"
    integration_points:
      - "employee_data_sync"
      - "timesheet_validation"
  
  time_tracking_system:
    related_domains:
      - "hr_employee_management"
      - "payroll_processing"
    integration_points:
      - "time_entry_validation"
      - "payroll_calculation"

# External System Integration Patterns
external_integration_patterns:
  database_systems:
    - pattern: "jdbc:oracle"
      system_type: "oracle_database"
      integration_complexity: "medium"
    - pattern: "jdbc:sqlserver"
      system_type: "sql_server_database"
      integration_complexity: "medium"
  
  web_services:
    - pattern: "soap.*wsdl"
      system_type: "soap_web_service"
      integration_complexity: "high"
    - pattern: "rest.*api"
      system_type: "rest_api"
      integration_complexity: "low"
```

---

## 📤 Output Specifications

### **Output File: step06_output.json**
Comprehensive relationship and dependency mapping:

```json
{
    "step_metadata": {
        "step_name": "relationship_mapping",
        "execution_timestamp": "ISO 8601 timestamp",
        "processing_time_ms": "integer",
        "components_analyzed": "integer",
        "relationships_identified": "integer",
        "integration_points_found": "integer",
        "errors_encountered": "integer",
        "configuration_sources": ["config.yaml", "config-<project>.yaml"]
    },
    "relationship_analysis": {
        "total_relationships": "integer",
        "relationship_types": {
            "direct_method_calls": "integer",
            "dependency_injection": "integer",
            "configuration_based": "integer",
            "database_connections": "integer",
            "external_integrations": "integer"
        },
        "relationship_confidence_distribution": {
            "high_confidence": "integer",            // > 0.8
            "medium_confidence": "integer",          // 0.6 - 0.8
            "low_confidence": "integer"              // < 0.6
        },
        "architectural_compliance": {
            "compliant_relationships": "integer",
            "violation_count": "integer",
            "compliance_score": "float 0-1"
        }
    },
    "component_relationships": [{
        "source_component": "string",
        "target_component": "string",
        "relationship_type": "string",               // method_call, dependency_injection, configuration, etc.
        "interaction_pattern": "string",            // synchronous, asynchronous, event_driven, etc.
        "confidence": "float 0-1",
        "evidence": [{
            "evidence_type": "string",               // code_reference, configuration, pattern_match
            "source_file": "string",                // Unix relative path
            "line_number": "integer",
            "code_snippet": "string",
            "description": "string"
        }],
        "architectural_context": {
            "source_layer": "string",                // asl, dsl, gsl, isl, screen, external
            "target_layer": "string",                // asl, dsl, gsl, isl, screen, external
            "compliance_status": "string",           // compliant, violation, warning
            "architectural_pattern": "string"
        },
        "business_context": {
            "source_domain": "string",
            "target_domain": "string",
            "business_purpose": "string",
            "data_flow_description": "string"
        },
        "technical_details": {
            "method_signatures": ["array"],
            "parameter_types": ["array"],
            "return_types": ["array"],
            "exception_types": ["array"],
            "transaction_boundaries": ["array"]
        },
        "quality_indicators": {
            "coupling_strength": "string",           // loose, medium, tight
            "dependency_direction": "string",        // inbound, outbound, bidirectional
            "stability_impact": "string",            // low, medium, high
            "testing_complexity": "string"           // simple, moderate, complex
        }
    }],
    "service_interactions": [{
        "interaction_id": "string",
        "interaction_name": "string",
        "interaction_type": "string",                // service_call, data_exchange, event_flow
        "source_services": ["array"],               // Component names
        "target_services": ["array"],               // Component names
        "data_flow": {
            "input_data_types": ["array"],
            "output_data_types": ["array"],
            "data_transformations": ["array"],
            "data_validation_rules": ["array"]
        },
        "flow_characteristics": {
            "synchronous": "boolean",
            "transactional": "boolean",
            "idempotent": "boolean",
            "error_handling": "string",
            "performance_characteristics": "object"
        },
        "business_process": {
            "process_name": "string",
            "business_value": "string",              // low, medium, high, critical
            "process_steps": ["array"],
            "decision_points": ["array"]
        },
        "modernization_impact": {
            "microservice_boundary": "boolean",      // Could this be a service boundary?
            "api_candidate": "boolean",              // Could this be exposed as API?
            "integration_complexity": "string",      // simple, moderate, complex
            "cloud_readiness": "string"              // ready, needs_modification, blocking
        }
    }],
    "integration_points": [{
        "integration_id": "string",
        "integration_name": "string",
        "integration_type": "string",                // database, web_service, file_system, message_queue
        "source_components": ["array"],
        "target_system": {
            "system_name": "string",
            "system_type": "string",                 // oracle_db, sql_server, web_service, etc.
            "connection_details": "object",
            "authentication_method": "string"
        },
        "integration_pattern": "string",             // synchronous, asynchronous, batch, real_time
        "data_exchange": {
            "data_formats": ["array"],               // xml, json, csv, binary
            "data_volumes": "object",
            "data_frequency": "string",              // real_time, hourly, daily, batch
            "error_handling": "string"
        },
        "configuration_sources": ["array"],          // Unix relative paths
        "business_criticality": "string",            // low, medium, high, critical
        "modernization_considerations": {
            "cloud_compatibility": "string",         // compatible, needs_changes, incompatible
            "security_requirements": ["array"],
            "scalability_concerns": ["array"],
            "migration_complexity": "string"
        }
    }],
    "dependency_analysis": {
        "dependency_graph": {
            "nodes": ["array"],                      // Component names
            "edges": ["array"],                      // Dependency relationships
            "cycles_detected": ["array"],           // Circular dependency cycles
            "strongly_connected_components": ["array"]
        },
        "architectural_layers": [{
            "layer_name": "string",
            "components": ["array"],
            "inbound_dependencies": "integer",
            "outbound_dependencies": "integer",
            "layer_coupling": "float 0-1",
            "architectural_violations": ["array"]
        }],
        "custom_architectural_analysis": {          // Project-specific patterns (asl, dsl, gsl, isl)
            "asl_dependencies": {
                "internal_dependencies": ["array"],
                "external_dependencies": ["array"],
                "violation_count": "integer",
                "compliance_score": "float 0-1"
            },
            "dsl_dependencies": {
                "internal_dependencies": ["array"],
                "external_dependencies": ["array"],
                "violation_count": "integer",
                "compliance_score": "float 0-1"
            },
            "gsl_dependencies": {
                "internal_dependencies": ["array"],
                "external_dependencies": ["array"],
                "violation_count": "integer",
                "compliance_score": "float 0-1"
            },
            "isl_dependencies": {
                "internal_dependencies": ["array"],
                "external_dependencies": ["array"],
                "violation_count": "integer",
                "compliance_score": "float 0-1"
            }
        },
        "coupling_analysis": {
            "loose_coupling_score": "float 0-1",
            "high_coupling_components": ["array"],
            "coupling_hotspots": ["array"],
            "refactoring_candidates": ["array"]
        }
    },
    "data_flow_analysis": {
        "data_flow_patterns": [{
            "flow_name": "string",
            "source_component": "string",
            "target_component": "string",
            "data_types": ["array"],
            "flow_characteristics": "object",
            "transformation_points": ["array"],
            "validation_points": ["array"],
            "business_rules_applied": ["array"]
        }],
        "data_consistency_analysis": {
            "data_validation_coverage": "float 0-1",
            "data_transformation_complexity": "string",
            "data_integrity_patterns": ["array"],
            "potential_data_issues": ["array"]
        },
        "transaction_analysis": {
            "transaction_boundaries": ["array"],
            "distributed_transactions": ["array"],
            "transaction_patterns": ["array"],
            "isolation_levels": ["array"]
        }
    },
    "modernization_insights": {
        "microservice_boundaries": [{
            "service_name": "string",
            "components": ["array"],
            "business_capability": "string",
            "data_ownership": ["array"],
            "integration_requirements": ["array"],
            "decomposition_complexity": "string"
        }],
        "api_candidates": [{
            "api_name": "string",
            "source_interactions": ["array"],
            "business_value": "string",
            "technical_feasibility": "string",
            "security_requirements": ["array"]
        }],
        "integration_modernization": [{
            "current_integration": "string",
            "modernization_approach": "string",
            "cloud_native_alternative": "string",
            "migration_effort": "string",
            "business_impact": "string"
        }]
    },
    "quality_metrics": {
        "relationship_detection_accuracy": "float 0-1",
        "dependency_analysis_completeness": "float 0-1",
        "integration_point_coverage": "float 0-1",
        "architectural_compliance_score": "float 0-1",
        "data_flow_analysis_confidence": "float 0-1",
        "cross_validation_success_rate": "float 0-1"
    },
    "validation_results": {
        "relationship_consistency": "float 0-1",
        "dependency_graph_validity": "float 0-1",
        "integration_configuration_accuracy": "float 0-1",
        "business_context_alignment": "float 0-1",
        "technical_detail_completeness": "float 0-1",
        "issues": ["array"]
    }
}
```

---

## 🔧 Implementation Details

### **Phase 1: Component Relationship Discovery**
1. **Direct Code Reference Analysis**
   ```python
   def analyze_direct_code_references(step02_output, config):
       relationships = []
       components = step02_output['components']
       
       for component in components:
           for file_info in component['files']:
               file_path = file_info['path']  # Unix relative path from STEP02
               
               # Analyze method calls and references
               method_calls = extract_method_calls_from_ast(file_path)
               import_statements = extract_imports_from_ast(file_path)
               
               for call in method_calls:
                   target_component = find_target_component(call, components)
                   if target_component and target_component != component['name']:
                       relationship = {
                           'source_component': component['name'],
                           'target_component': target_component,
                           'relationship_type': 'method_call',
                           'confidence': 0.95,  # High confidence for direct code references
                           'evidence': [{
                               'evidence_type': 'code_reference',
                               'source_file': file_path,  # Unix relative path
                               'line_number': call.get('line_number'),
                               'code_snippet': call.get('code_snippet'),
                               'description': f"Direct method call: {call.get('method_name')}"
                           }]
                       }
                       relationships.append(relationship)
       
       return relationships
   ```

2. **Dependency Injection Analysis**
   ```python
   def analyze_dependency_injection(step02_output, step03_output, config):
       di_relationships = []
       spring_config = step03_output.get('framework_analysis', {}).get('spring_framework', {})
       
       # Analyze annotation-based DI
       for component in step02_output['components']:
           for file_info in component['files']:
               annotations = file_info.get('annotations_detected', [])
               
               for annotation in annotations:
                   if annotation in config['relationship_detection']['dependency_patterns']['spring_injection']:
                       injected_component = resolve_injection_target(annotation, component, step02_output)
                       
                       if injected_component:
                           di_relationships.append({
                               'source_component': component['name'],
                               'target_component': injected_component,
                               'relationship_type': 'dependency_injection',
                               'interaction_pattern': 'spring_injection',
                               'confidence': 0.9,
                               'evidence': [{
                                   'evidence_type': 'annotation',
                                   'source_file': file_info['path'],  # Unix relative path
                                   'description': f"Dependency injection: {annotation}"
                               }]
                           })
       
       # Analyze XML-based DI from STEP03 configuration
       xml_relationships = analyze_xml_bean_dependencies(spring_config, step02_output)
       di_relationships.extend(xml_relationships)
       
       return di_relationships
   ```

3. **Configuration-Based Relationship Detection**
   ```python
   def analyze_configuration_relationships(step03_output, step02_output, config):
       config_relationships = []
       
       # Analyze Spring bean configurations
       spring_config = step03_output.get('framework_analysis', {}).get('spring_framework', {})
       
       if spring_config.get('dependency_injection', {}).get('bean_definitions'):
           for bean_def in spring_config['dependency_injection']['bean_definitions']:
               source_component = find_component_by_class_name(bean_def['class_name'], step02_output)
               
               for dependency in bean_def.get('dependencies', []):
                   target_component = find_component_by_bean_name(dependency['ref'], step02_output)
                   
                   if source_component and target_component:
                       config_relationships.append({
                           'source_component': source_component,
                           'target_component': target_component,
                           'relationship_type': 'configuration_based',
                           'confidence': 0.85,
                           'evidence': [{
                               'evidence_type': 'configuration',
                               'source_file': bean_def.get('config_file', ''),  # Unix relative path
                               'description': f"XML bean dependency: {dependency['ref']}"
                           }]
                       })
       
       return config_relationships
   ```

### **Phase 2: Architectural Relationship Validation**
1. **Custom Architectural Pattern Validation (asl, dsl, gsl, isl)**
   ```python
   def validate_architectural_relationships(relationships, step04_output, config):
       architectural_rules = config.get('architectural_relationship_rules', {})
       validated_relationships = []
       
       for relationship in relationships:
           source_layer = determine_architectural_layer(
               relationship['source_component'], step04_output
           )
           target_layer = determine_architectural_layer(
               relationship['target_component'], step04_output
           )
           
           # Check architectural compliance
           compliance_status = "compliant"
           if source_layer in architectural_rules:
               layer_rules = architectural_rules[source_layer]
               
               if target_layer in layer_rules.get('restricted_outbound', []):
                   compliance_status = "violation"
               elif target_layer not in layer_rules.get('allowed_outbound', []):
                   compliance_status = "warning"
           
           relationship['architectural_context'] = {
               'source_layer': source_layer,
               'target_layer': target_layer,
               'compliance_status': compliance_status,
               'architectural_pattern': determine_pattern_type(source_layer, target_layer)
           }
           
           validated_relationships.append(relationship)
       
       return validated_relationships
   ```

2. **Business Domain Relationship Validation**
   ```python
   def validate_business_domain_relationships(relationships, step04_output, config):
       domain_rules = config.get('business_domain_relationships', {})
       
       for relationship in relationships:
           source_domain = get_component_domain(relationship['source_component'], step04_output)
           target_domain = get_component_domain(relationship['target_component'], step04_output)
           
           # Check business domain relationship validity
           if source_domain in domain_rules:
               related_domains = domain_rules[source_domain].get('related_domains', [])
               if target_domain in related_domains:
                   relationship['business_context'] = {
                       'source_domain': source_domain,
                       'target_domain': target_domain,
                       'business_purpose': determine_business_purpose(source_domain, target_domain),
                       'data_flow_description': generate_data_flow_description(relationship)
                   }
           
           # Enhance with LLM-derived business context from STEP04
           llm_context = get_llm_business_context(relationship, step04_output)
           if llm_context:
               relationship['business_context'].update(llm_context)
       
       return relationships
   ```

### **Phase 3: Service Interaction Analysis**
1. **Service Interaction Pattern Detection**
   ```python
   def analyze_service_interactions(relationships, step04_output, config):
       interactions = []
       
       # Group relationships by business process
       process_groups = group_relationships_by_process(relationships, step04_output)
       
       for process_name, process_relationships in process_groups.items():
           interaction = {
               'interaction_id': generate_interaction_id(process_name),
               'interaction_name': process_name,
               'interaction_type': determine_interaction_type(process_relationships),
               'source_services': extract_source_services(process_relationships),
               'target_services': extract_target_services(process_relationships)
           }
           
           # Analyze data flow characteristics
           interaction['data_flow'] = analyze_data_flow(process_relationships, step04_output)
           
           # Determine flow characteristics
           interaction['flow_characteristics'] = {
               'synchronous': is_synchronous_flow(process_relationships),
               'transactional': has_transaction_boundaries(process_relationships),
               'idempotent': assess_idempotency(process_relationships),
               'error_handling': analyze_error_handling(process_relationships)
           }
           
           # Extract business process information
           interaction['business_process'] = extract_business_process_info(
               process_name, process_relationships, step04_output
           )
           
           # Assess modernization impact
           interaction['modernization_impact'] = assess_modernization_impact(
               interaction, step04_output
           )
           
           interactions.append(interaction)
       
       return interactions
   ```

2. **Data Flow Analysis**
   ```python
   def analyze_data_flow(relationships, step04_output):
       data_flow_patterns = []
       
       for relationship in relationships:
           # Extract method signature information from technical details
           method_sigs = relationship.get('technical_details', {}).get('method_signatures', [])
           
           for method_sig in method_sigs:
               flow_pattern = {
                   'flow_name': f"{relationship['source_component']}_to_{relationship['target_component']}",
                   'source_component': relationship['source_component'],
                   'target_component': relationship['target_component'],
                   'data_types': extract_data_types_from_signature(method_sig),
                   'transformation_points': identify_transformation_points(method_sig),
                   'validation_points': identify_validation_points(method_sig, step04_output)
               }
               
               # Enhance with business rules from STEP04
               business_rules = get_component_business_rules(
                   relationship['target_component'], step04_output
               )
               flow_pattern['business_rules_applied'] = business_rules
               
               data_flow_patterns.append(flow_pattern)
       
       return data_flow_patterns
   ```

### **Phase 4: Integration Point Analysis**
1. **External System Integration Detection**
   ```python
   def detect_integration_points(step02_output, step03_output, config):
       integration_points = []
       external_indicators = config['integration_detection']['external_system_indicators']
       
       # Analyze database connections
       db_configs = step03_output.get('framework_analysis', {}).get('persistence_framework', {})
       for db_connection in db_configs.get('database_connections', []):
           integration_point = {
               'integration_id': generate_integration_id(db_connection['datasource_name']),
               'integration_name': db_connection['datasource_name'],
               'integration_type': 'database',
               'target_system': {
                   'system_name': db_connection['datasource_name'],
                   'system_type': determine_db_type(db_connection['driver_class']),
                   'connection_details': db_connection,
                   'authentication_method': extract_auth_method(db_connection)
               }
           }
           
           # Find components that use this database
           integration_point['source_components'] = find_components_using_datasource(
               db_connection['datasource_name'], step02_output
           )
           
           integration_points.append(integration_point)
       
       # Analyze web service integrations
       web_service_integrations = detect_web_service_integrations(
           step02_output, external_indicators, config
       )
       integration_points.extend(web_service_integrations)
       
       # Analyze file system integrations
       file_system_integrations = detect_file_system_integrations(
           step02_output, external_indicators, config
       )
       integration_points.extend(file_system_integrations)
       
       return integration_points
   ```

2. **Integration Pattern Analysis**
   ```python
   def analyze_integration_patterns(integration_points, step04_output, config):
       for integration in integration_points:
           # Determine integration pattern
           integration['integration_pattern'] = determine_integration_pattern(
               integration, step04_output
           )
           
           # Analyze data exchange characteristics
           integration['data_exchange'] = {
               'data_formats': detect_data_formats(integration, step04_output),
               'data_volumes': estimate_data_volumes(integration),
               'data_frequency': determine_data_frequency(integration),
               'error_handling': analyze_integration_error_handling(integration)
           }
           
           # Assess business criticality
           integration['business_criticality'] = assess_business_criticality(
               integration, step04_output
           )
           
           # Evaluate modernization considerations
           integration['modernization_considerations'] = {
               'cloud_compatibility': assess_cloud_compatibility(integration),
               'security_requirements': extract_security_requirements(integration),
               'scalability_concerns': identify_scalability_concerns(integration),
               'migration_complexity': assess_migration_complexity(integration)
           }
       
       return integration_points
   ```

### **Phase 5: Dependency Graph Construction**
1. **Dependency Graph Building**
   ```python
   def build_dependency_graph(relationships, components):
       nodes = [comp['name'] for comp in components]
       edges = []
       
       for relationship in relationships:
           edge = {
               'source': relationship['source_component'],
               'target': relationship['target_component'],
               'relationship_type': relationship['relationship_type'],
               'weight': relationship['confidence']
           }
           edges.append(edge)
       
       # Detect cycles
       cycles = detect_dependency_cycles(nodes, edges)
       
       # Identify strongly connected components
       strongly_connected = find_strongly_connected_components(nodes, edges)
       
       return {
           'nodes': nodes,
           'edges': edges,
           'cycles_detected': cycles,
           'strongly_connected_components': strongly_connected
       }
   ```

2. **Architectural Layer Analysis**
   ```python
   def analyze_architectural_layers(dependency_graph, step04_output, config):
       layers = {}
       architectural_rules = config.get('architectural_relationship_rules', {})
       
       # Group components by architectural layer
       for node in dependency_graph['nodes']:
           layer = determine_architectural_layer(node, step04_output)
           if layer not in layers:
               layers[layer] = {
                   'layer_name': layer,
                   'components': [],
                   'inbound_dependencies': 0,
                   'outbound_dependencies': 0,
                   'architectural_violations': []
               }
           layers[layer]['components'].append(node)
       
       # Calculate layer dependencies and violations
       for edge in dependency_graph['edges']:
           source_layer = determine_architectural_layer(edge['source'], step04_output)
           target_layer = determine_architectural_layer(edge['target'], step04_output)
           
           if source_layer in layers:
               layers[source_layer]['outbound_dependencies'] += 1
           if target_layer in layers:
               layers[target_layer]['inbound_dependencies'] += 1
           
           # Check for architectural violations
           if source_layer in architectural_rules:
               restricted = architectural_rules[source_layer].get('restricted_outbound', [])
               if target_layer in restricted:
                   violation = f"{edge['source']} -> {edge['target']} violates {source_layer} -> {target_layer} restriction"
                   layers[source_layer]['architectural_violations'].append(violation)
       
       # Calculate layer coupling
       for layer_info in layers.values():
           total_deps = layer_info['inbound_dependencies'] + layer_info['outbound_dependencies']
           component_count = len(layer_info['components'])
           layer_info['layer_coupling'] = total_deps / component_count if component_count > 0 else 0
       
       return list(layers.values())
   ```

### **Phase 6: Cross-Validation and Enhancement**
1. **Cross-Step Validation**
   ```python
   def cross_validate_relationships(relationships, step02_output, step03_output, step04_output):
       validation_results = []
       
       for relationship in relationships:
           validation = {
               'relationship_id': generate_relationship_id(relationship),
               'consistency_checks': {},
               'confidence_adjustments': []
           }
           
           # Validate against AST data from STEP02
           ast_validation = validate_against_ast(relationship, step02_output)
           validation['consistency_checks']['ast_consistency'] = ast_validation
           
           # Validate against configuration from STEP04
           config_validation = validate_against_config(relationship, step04_output)
           validation['consistency_checks']['config_consistency'] = config_validation
           
           # Validate against LLM analysis from STEP05
           llm_validation = validate_against_llm_analysis(relationship, step05_output)
           validation['consistency_checks']['llm_consistency'] = llm_validation
           
           # Calculate overall validation score
           validation_score = calculate_overall_validation_score(validation['consistency_checks'])
           
           # Apply confidence adjustments
           if validation_score > 0.8:
               relationship['confidence'] = min(relationship['confidence'] + 0.1, 1.0)
               validation['confidence_adjustments'].append("High cross-validation boost")
           elif validation_score < 0.5:
               relationship['confidence'] = max(relationship['confidence'] - 0.2, 0.1)
               validation['confidence_adjustments'].append("Low cross-validation penalty")
           
           validation_results.append(validation)
       
       return validation_results
   ```

2. **Quality Enhancement**
   ```python
   def enhance_relationship_quality(relationships, step04_output, config):
       enhanced_relationships = []
       
       for relationship in relationships:
           # Add business context from STEP04
           business_context = extract_business_context(relationship, step04_output)
           if business_context:
               relationship['business_context'] = business_context
           
           # Add technical details
           technical_details = extract_technical_details(relationship, step04_output)
           relationship['technical_details'] = technical_details
           
           # Calculate quality indicators
           relationship['quality_indicators'] = {
               'coupling_strength': assess_coupling_strength(relationship),
               'dependency_direction': determine_dependency_direction(relationship),
               'stability_impact': assess_stability_impact(relationship),
               'testing_complexity': assess_testing_complexity(relationship)
           }
           
           enhanced_relationships.append(relationship)
       
       return enhanced_relationships
   ```

---

## ✅ Validation and Quality Assurance

### **Internal Validation**
1. **Relationship Detection Accuracy**
   ```python
   def validate_relationship_detection():
       accuracy_metrics = {
           'true_positives': 0,
           'false_positives': 0,
           'false_negatives': 0,
           'precision': 0.0,
           'recall': 0.0
       }
       
       # Compare detected relationships with ground truth (if available)
       # Validate against multiple evidence sources
       for relationship in detected_relationships:
           evidence_count = len(relationship.get('evidence', []))
           confidence = relationship.get('confidence', 0)
           
           # High confidence relationships with multiple evidence sources
           if evidence_count >= 2 and confidence > 0.8:
               accuracy_metrics['true_positives'] += 1
           elif evidence_count == 1 and confidence > 0.6:
               # Medium confidence - likely correct but needs validation
               pass
           else:
               # Low confidence - potential false positive
               accuracy_metrics['false_positives'] += 1
       
       return accuracy_metrics
   ```

2. **Dependency Graph Validation**
   ```python
   def validate_dependency_graph():
       graph_quality = {
           'connectivity': 0.0,
           'cycle_ratio': 0.0,
           'layer_compliance': 0.0
       }
       
       # Check graph connectivity
       connected_components = count_connected_components(dependency_graph)
       total_components = len(dependency_graph['nodes'])
       graph_quality['connectivity'] = connected_components / total_components
       
       # Calculate cycle ratio
       total_relationships = len(dependency_graph['edges'])
       cycles = len(dependency_graph['cycles_detected'])
       graph_quality['cycle_ratio'] = cycles / total_relationships if total_relationships > 0 else 0
       
       # Check architectural layer compliance
       compliant_relationships = count_compliant_relationships(dependency_graph)
       graph_quality['layer_compliance'] = compliant_relationships / total_relationships
       
       return graph_quality
   ```

3. **Integration Point Coverage**
   ```python
   def validate_integration_coverage():
       coverage_metrics = {
           'database_coverage': 0.0,
           'external_service_coverage': 0.0,
           'configuration_consistency': 0.0
       }
       
       # Check database integration coverage
       db_configs = step03_output['framework_analysis']['persistence_framework']['database_connections']
       detected_db_integrations = [ip for ip in integration_points if ip['integration_type'] == 'database']
       coverage_metrics['database_coverage'] = len(detected_db_integrations) / len(db_configs) if db_configs else 1.0
       
       # Check external service coverage
       # Compare with web service configurations and external dependencies
       
       # Check configuration consistency
       # Validate that detected integrations match configuration files
       
       return coverage_metrics
   ```

### **Output Validation**
1. **JSON Schema Compliance**
   ```python
   def validate_step06_output_schema():
       required_sections = [
           'step_metadata', 'relationship_analysis', 'component_relationships',
           'service_interactions', 'integration_points', 'dependency_analysis',
           'data_flow_analysis', 'modernization_insights', 'quality_metrics', 'validation_results'
       ]
       
       for section in required_sections:
           if section not in step06_output:
               raise ValueError(f"Missing required section: {section}")
       
       # Validate Unix relative path compliance
       validate_unix_relative_paths_in_relationships(step06_output)
       
       return True
   ```

2. **Relationship Quality Assessment**
   ```python
   def assess_relationship_quality():
       quality_indicators = {
           'high_confidence_relationships': 0,
           'multi_evidence_relationships': 0,
           'business_context_coverage': 0,
           'architectural_compliance': 0
       }
       
       for relationship in step06_output['component_relationships']:
           if relationship.get('confidence', 0) > 0.8:
               quality_indicators['high_confidence_relationships'] += 1
           
           if len(relationship.get('evidence', [])) > 1:
               quality_indicators['multi_evidence_relationships'] += 1
           
           if relationship.get('business_context'):
               quality_indicators['business_context_coverage'] += 1
           
           if relationship.get('architectural_context', {}).get('compliance_status') == 'compliant':
               quality_indicators['architectural_compliance'] += 1
       
       total_relationships = len(step06_output['component_relationships'])
       return {
           indicator: count / total_relationships 
           for indicator, count in quality_indicators.items()
       } if total_relationships > 0 else {}
   ```

### **Success Criteria**
- **Relationship Detection Accuracy**: 85%+ accuracy in identifying component relationships
- **Dependency Graph Completeness**: 90%+ of identifiable dependencies captured
- **Integration Point Coverage**: 95%+ of external integrations identified
- **Architectural Compliance**: 80%+ of relationships comply with architectural rules
- **Cross-Step Validation Success**: 85%+ consistency with previous step findings
- **Path Format Compliance**: 100% of file references must be Unix relative format
- **Custom Pattern Recognition**: 90%+ accuracy in architectural layer compliance (asl, dsl, gsl, isl)

---

## 🚨 Error Handling

### **Relationship Detection Failures**
```python
def handle_relationship_detection_failure(component, target, error):
    error_info = {
        "source_component": component,
        "target_component": target,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.now().isoformat(),
        "recovery_action": "mark_as_potential_relationship"
    }
    log_error(error_info)
    
    # Create low-confidence relationship entry
    return {
        'source_component': component,
        'target_component': target,
        'relationship_type': 'potential_relationship',
        'confidence': 0.3,
        'evidence': [{
            'evidence_type': 'failed_detection',
            'description': f"Relationship detection failed: {error_info['error_message']}"
        }]
    }
```

### **Dependency Graph Construction Failures**
```python
def handle_dependency_graph_failure(relationships, error):
    # Fallback to simplified graph construction
    simplified_graph = create_simplified_dependency_graph(relationships)
    
    error_info = {
        "error_type": "dependency_graph_construction_failure",
        "error_message": str(error),
        "fallback_action": "simplified_graph_created",
        "affected_relationships": len(relationships)
    }
    log_error(error_info)
    
    return simplified_graph
```

### **Integration Point Detection Failures**
```python
def handle_integration_detection_failure(config_data, error):
    # Continue with partial integration analysis
    partial_integrations = extract_partial_integration_data(config_data)
    
    error_info = {
        "error_type": "integration_detection_failure",
        "error_message": str(error),
        "recovery_action": "partial_integration_analysis",
        "confidence_adjustment": -0.2
    }
    log_error(error_info)
    
    return partial_integrations
```

---

## 📊 Performance Considerations

### **Optimization Strategies**
1. **Parallel Relationship Analysis**
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   def parallel_relationship_analysis(components, max_workers=4):
       with ThreadPoolExecutor(max_workers=max_workers) as executor:
           futures = {executor.submit(analyze_component_relationships, comp): comp 
                     for comp in components}
           results = []
           for future in futures:
               try:
                   results.extend(future.result())
               except Exception as e:
                   handle_relationship_analysis_error(futures[future], e)
       return results
   ```

2. **Efficient Dependency Graph Algorithms**
   ```python
   def optimized_cycle_detection(graph):
       # Use efficient algorithms for large graphs
       # Implement depth-first search with memoization
       # Early termination for acyclic subgraphs
       pass
   ```

3. **Cached Cross-Reference Lookups**
   ```python
   def cache_component_lookups():
       # Cache component name to object mappings
       # Cache package to component mappings
       # Cache method signature lookups
       pass
   ```

### **Resource Limits**
- **Graph Size**: Support up to 10,000 components and 50,000 relationships
- **Processing Time**: Target <20 minutes for typical projects
- **Memory Usage**: Target <2GB for relationship analysis
- **Cycle Detection**: Efficient algorithms for graphs with <1000 cycles

---

## 🔍 Testing Strategy

### **Unit Tests**
1. **Relationship Detection Tests**
   ```python
   def test_direct_relationship_detection():
       # Test method call detection
       # Verify dependency injection analysis
       # Test configuration-based relationships
   
   def test_architectural_validation():
       # Test custom architectural layer compliance (asl, dsl, gsl, isl)
       # Verify business domain relationship validation
       # Test architectural violation detection
   ```

2. **Dependency Analysis Tests**
   ```python
   def test_dependency_graph_construction():
       # Test graph building from relationships
       # Verify cycle detection accuracy
       # Test strongly connected component identification
   
   def test_integration_point_detection():
       # Test database integration detection
       # Verify web service integration analysis
       # Test external system identification
   ```

### **Integration Tests**
1. **Cross-Step Integration Tests**
   ```python
   def test_multi_step_relationship_validation():
       # Test consistency across STEP02, STEP03, STEP04, STEP06
       # Verify relationship confidence adjustments
       # Test business context integration
   ```

2. **End-to-End Relationship Mapping**
   ```python
   def test_complete_relationship_analysis():
       # Test full STEP06 pipeline with real components
       # Verify all output requirements are met
       # Test modernization insight generation
   ```

---

## 📝 Configuration Examples

#### **Development Environment**
**config.yaml enhancements**:
```yaml
relationship_detection:
  aggressive_detection: true
  confidence_threshold: 0.5
  include_potential_relationships: true

dependency_analysis:
  detect_circular_dependencies: true
  analyze_coupling_strength: true
  generate_refactoring_suggestions: true
```

#### **Production Environment**
**config-storm.yaml enhancements**:
```yaml
project_relationship_patterns:
  storm_specific_patterns:
    - "asl_service_orchestration"
    - "dsl_business_rule_enforcement"
    - "gsl_utility_provision"
    - "isl_data_persistence"

architectural_relationship_rules:
  # Storm-specific architectural compliance rules
  strict_layer_enforcement: true
  allow_emergency_violations: false
  custom_integration_patterns:
    - "storm_hr_database_access"
    - "nbcu_enterprise_service_integration"
    - "legacy_system_bridge_patterns"

business_domain_relationships:
  storm_hr_specific:
    employee_management:
      critical_integrations:
        - "time_tracking_validation"
        - "payroll_calculation_trigger"
        - "benefits_enrollment_sync"
    time_tracking:
      dependent_processes:
        - "overtime_calculation"
        - "absence_management"
        - "project_time_allocation"
```
