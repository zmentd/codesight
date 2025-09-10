# Target Schema Definition

**Version:** 1.0  
**Date:** July 22, 2025  
**Purpose:** Complete JSON schema specification for CodeSight output

---

## 📋 Schema Overview

The TARGET_SCHEMA defines the unified JSON structure that CodeSight generates to represent legacy application requirements. This schema consolidates screens, services, utilities, and integrations into a single "components" array with embedded relationships and comprehensive metadata.

### **Design Principles:**
- **Unified Component Model:** Single array for all component types (screens, services, utilities, integrations)
- **Embedded Relationships:** Service interactions included within screen components
- **Confidence Scoring:** Every extracted element includes confidence metadata
- **Extensible Structure:** Schema supports future enhancements and additional attributes

---

## 🏗️ Root Schema Structure

```json
{
    "metadata": { /* Project and analysis metadata */ },
    "components": [ /* Array of all application components */ ],
    "validation_results": { /* Output quality and validation metrics */ }
}
```

---

## 📊 Metadata Section

```json
{
    "metadata": {
        "project_name": "string",                    // Extracted from build files or directory name
        "analysis_date": "ISO 8601 timestamp",      // When analysis was performed
        "pipeline_version": "string",               // CodeSight version used
        "languages_detected": ["array of strings"], // Programming languages found
        "frameworks_detected": ["array of strings"], // Frameworks identified (Spring, Hibernate, etc.)
        "total_files_analyzed": "integer",          // Number of files processed
        "confidence_score": "float 0-1",            // Overall extraction confidence
        "extraction_summary": {
            "components_extracted": "integer",       // Total components identified
            "screens_identified": "integer",         // Screen/UI components
            "services_identified": "integer",        // Service layer components
            "utilities_identified": "integer",       // Utility/helper components
            "integrations_identified": "integer",    // Integration/external connection components
            "business_rules_extracted": "integer",   // Total business rules found
            "service_interactions_mapped": "integer" // Component interactions mapped
        },
        "architecture_patterns": {
            "primary_pattern": "string",             // Main architecture pattern (layered, MVC, etc.)
            "mvc_compliance": "boolean",             // Whether MVC pattern is followed
            "dependency_injection": "string",        // DI framework (Spring, etc.)
            "transaction_management": "string",      // Transaction approach (declarative, programmatic)
            "security_model": "string"               // Security implementation approach
        }
    }
}
```

---

## 🧩 Components Array

Each component in the array follows this structure:

```json
{
    "name": "string",                              // Component identifier
    "component_type": "screen|service|utility|integration", // Component classification
    "domain": "string",                            // Business domain (User_Management, etc.)
    "subdomain": "string",                         // Specific subdomain (optional)
    "description": "string",                       // LLM-generated description
    "confidence": "float 0-1",                     // Overall component confidence
    "files": [ /* File information array */ ],
    "functional_requirements": { /* Business requirements */ },
    "technical_requirements": { /* Technical specifications */ },
    "service_interactions": [ /* Service relationship array */ ]
}
```

### **Files Array Structure:**
```json
{
    "files": [
        {
            "path": "string",                      // Absolute file path
            "type": "string",                      // File type (controller, service, view, etc.)
            "role": "string",                      // Component role (request_handler, business_logic, etc.)
            "framework_hints": ["array"],          // Framework indicators found in file
            "size_bytes": "integer",               // File size
            "last_modified": "ISO 8601 timestamp" // Last modification date
        }
    ]
}
```

---

## 🧩 Component Types Overview

The schema supports four distinct component types, each designed to capture specific aspects of legacy applications:

- **screen** - User interface components (JSPs, HTML pages, forms, dashboards)
- **service** - Business logic components (services, controllers, business rules)  
- **utility** - Helper components (validators, formatters, converters, constants)
- **integration** - External connection components (REST clients, database connectors, message queues)

---

## 📋 Functional Requirements

### **Screen Components (component_type: "screen"):**
```json
{
    "functional_requirements": {
        "fields": [
            {
                "name": "string",                  // Field identifier
                "type": "string",                  // Input type (text, email, password, etc.)
                "required": "boolean",             // Whether field is mandatory
                "max_length": "integer|null",      // Maximum character length
                "validation_rules": ["array"],     // Validation patterns/rules
                "default_value": "string",         // Default field value
                "options": ["array"],              // For select/radio fields
                "css_classes": ["array"],          // CSS styling classes
                "help_text": "string",             // User guidance text
                "error_messages": ["array"],       // Validation error messages
                "conditional_display": "string"    // Display conditions
            }
        ],
        "actions": [
            {
                "name": "string",                  // Action identifier
                "type": "string",                  // Action type (form_submit, ajax_call, etc.)
                "endpoint": "string",              // Target URL or service method
                "method": "string",                // HTTP method (GET, POST, etc.)
                "trigger": "string",               // User trigger (button_click, form_submit)
                "validation": "string",            // Validation type (client_side, server_side)
                "confirmation_required": "boolean", // Whether action needs confirmation
                "success_redirect": "string",      // Redirect on success
                "error_handling": ["array"],       // Error handling approaches
                "permissions_required": ["array"] // Required user permissions
            }
        ],
        "validations": [
            {
                "field": "string",                 // Field being validated
                "rules": ["array"],                // Validation rules (required, min_length, etc.)
                "client_side": "boolean",          // Whether validation runs on client
                "server_side": "boolean",          // Whether validation runs on server
                "error_messages": {                // Custom error messages for each rule
                    "rule_name": "string",         // Error message for specific rule
                    "additionalProperties": "string"
                },
                "confidence": "float 0-1"          // Validation extraction confidence
            }
        ],
        "conditional_display": [
            {
                "condition": "string",             // JavaScript/logical condition
                "shows": ["array"],                // Elements to show when condition is true
                "hides": ["array"],                // Elements to hide when condition is true
                "enables": ["array"],              // Elements to enable when condition is true
                "disables": ["array"],             // Elements to disable when condition is true
                "confidence": "float 0-1"          // Condition extraction confidence
            }
        ],
        "business_rules": [
            {
                "rule": "string",                  // Rule identifier
                "description": "string",           // Human-readable rule description
                "enforcement": "string",           // Where rule is enforced (database_constraint, business_logic, etc.)
                "error_message": "string",         // Error message for rule violation
                "confidence": "float 0-1"          // Extraction confidence for this rule
            }
        ],
        "data_flow": "string",                     // High-level data flow description
        "data_transformations": [
            {
                "step": "string",                  // Transformation step name
                "description": "string",           // What the transformation does
                "input_type": "string",            // Input data type
                "output_type": "string",           // Output data type
                "confidence": "float 0-1"          // Transformation extraction confidence
            }
        ]
    }
}
```

### **Service Components (component_type: "service"):**
```json
{
    "functional_requirements": {
        "operations": [
            {
                "name": "string",                  // Method name
                "type": "string",                  // Operation type (business_operation, utility, etc.)
                "description": "string",           // LLM-generated description
                "parameters": [
                    {
                        "name": "string",          // Parameter name
                        "type": "string",          // Parameter type
                        "required": "boolean",     // Whether parameter is required
                        "validation_rules": ["array"], // Parameter validation
                        "default_value": "string" // Default parameter value
                    }
                ],
                "returns": {
                    "type": "string",              // Return type
                    "description": "string"        // Return value description
                },
                "error_handling": ["array"],       // Exception types thrown
                "business_logic": "string",        // LLM-extracted business logic description
                "side_effects": ["array"],         // Side effects (database writes, external calls)
                "confidence": "float 0-1"          // Operation extraction confidence
            }
        ],
        "business_rules": [
            /* Same structure as screen business_rules */
        ],
        "data_transformations": [
            /* Same structure as screen data_transformations */
        ]
    }
}
```

### **Utility Components (component_type: "utility"):**
```json
{
    "functional_requirements": {
        "utilities": [
            {
                "name": "string",                  // Utility function name
                "type": "string",                  // Utility type (validator, formatter, helper, converter, etc.)
                "description": "string",           // Function description
                "parameters": [
                    {
                        "name": "string",          // Parameter name
                        "type": "string",          // Parameter type
                        "required": "boolean",     // Whether parameter is required
                        "description": "string"    // Parameter description
                    }
                ],
                "returns": {
                    "type": "string",              // Return type
                    "description": "string"        // Return value description
                },
                "usage_patterns": ["array"],       // How utility is typically used
                "is_static": "boolean",            // Whether utility is static
                "thread_safe": "boolean",          // Whether utility is thread-safe
                "confidence": "float 0-1"          // Utility extraction confidence
            }
        ],
        "constants": [
            {
                "name": "string",                  // Constant name
                "value": "string",                 // Constant value
                "type": "string",                  // Data type
                "description": "string",           // Purpose description
                "usage_context": "string",         // Where constant is used
                "scope": "string"                  // Scope (global, class, package)
            }
        ],
        "enums": [
            {
                "name": "string",                  // Enum name
                "values": ["array"],               // Enum values
                "description": "string",           // Enum purpose
                "usage_context": "string"          // Where enum is used
            }
        ]
    }
}
```

### **Integration Components (component_type: "integration"):**
```json
{
    "functional_requirements": {
        "integrations": [
            {
                "name": "string",                  // Integration name
                "type": "string",                  // Integration type (rest_client, soap_client, database_connector, message_queue, etc.)
                "description": "string",           // Integration description
                "external_system": "string",       // Target external system name
                "protocol": "string",              // Communication protocol (HTTP, HTTPS, JMS, JDBC, etc.)
                "operations": [
                    {
                        "name": "string",          // Operation name
                        "method": "string",        // HTTP method or operation type
                        "endpoint": "string",      // URL endpoint or operation path
                        "request_format": "string", // Request data format (JSON, XML, etc.)
                        "response_format": "string", // Response data format
                        "timeout_ms": "integer",   // Operation timeout
                        "retry_policy": "string",  // Retry strategy
                        "circuit_breaker": "boolean" // Whether circuit breaker is used
                    }
                ],
                "authentication": {
                    "type": "string",              // Auth type (basic, oauth, api_key, etc.)
                    "mechanism": "string",         // How auth is implemented
                    "credentials_source": "string" // Where credentials are stored
                },
                "error_handling": ["array"],       // Error handling strategies
                "fallback_strategy": "string",     // What happens when integration fails
                "confidence": "float 0-1"          // Integration extraction confidence
            }
        ],
        "message_patterns": [
            {
                "pattern": "string",               // Message pattern (request-response, fire-and-forget, etc.)
                "queue_name": "string",            // Message queue name
                "message_format": "string",        // Message format (JSON, XML, etc.)
                "routing_key": "string",           // Message routing information
                "durability": "string"             // Message durability settings
            }
        ]
    }
}
```

---

## ⚙️ Technical Requirements

```json
{
    "technical_requirements": {
        "dependencies": [
            {
                "name": "string",                  // Dependency name
                "type": "string",                  // Dependency type/interface
                "required": "boolean",             // Whether dependency is required
                "injection_mechanism": "string",   // How dependency is injected (autowired, etc.)
                "scope": "string",                 // Dependency scope (singleton, prototype, etc.)
                "qualifier": "string",             // Specific qualifier for injection
                "interface": "string",             // Interface implemented
                "async_capable": "boolean"         // Whether dependency supports async operations
            }
        ],
        "data_storage": [
            {
                "table": "string",                 // Database table name
                "operations": ["array"],           // Operations performed (INSERT, UPDATE, SELECT, DELETE)
                "key_fields": ["array"],           // Primary key and important fields
                "indexes": ["array"],              // Database indexes used
                "constraints": ["array"],          // Database constraints (foreign keys, unique, etc.)
                "transaction_scope": "string",     // Transaction boundary (method, class, global)
                "isolation_level": "string",       // Transaction isolation level
                "confidence": "float 0-1"          // Data storage extraction confidence
            }
        ],
        "security_constraints": [
            {
                "type": "string",                  // Constraint type (url_authorization, method_authorization, etc.)
                "mechanism": "string",             // Security mechanism (role_based, annotation_based, etc.)
                "required": "boolean",             // Whether security is mandatory
                "patterns": ["array"],             // URL patterns or method patterns
                "roles": ["array"],                // Required roles
                "permissions": ["array"],          // Required permissions
                "expression": "string",            // Security expression (SpEL, etc.)
                "enforcement_level": "string"      // Where enforced (method, class, global)
            }
        ],
        "performance_patterns": {
            "caching": {
                "strategy": "string",              // Caching strategy (single_level, multi_level, etc.)
                "providers": ["array"],            // Caching providers (EhCache, Redis, etc.)
                "ttl_default": "integer",          // Default TTL in seconds
                "cache_regions": ["array"],        // Defined cache regions
                "eviction_policy": "string"        // Cache eviction policy
            },
            "connection_pooling": {
                "type": "string",                  // Pool type (HikariCP, C3P0, etc.)
                "max_connections": "integer",      // Maximum connections
                "min_connections": "integer",      // Minimum connections
                "timeout_ms": "integer",           // Connection timeout
                "validation_query": "string",      // Connection validation query
                "validation_enabled": "boolean"    // Whether validation is enabled
            },
            "transaction_management": {
                "type": "string",                  // Transaction type (declarative, programmatic)
                "propagation": "string",           // Propagation behavior
                "isolation": "string",             // Isolation level
                "timeout_seconds": "integer",      // Transaction timeout
                "read_only": "boolean"             // Whether transactions are read-only
            },
            "async_processing": {
                "enabled": "boolean",              // Whether async is used
                "thread_pool_size": "integer",     // Thread pool configuration
                "queue_capacity": "integer",       // Queue capacity
                "executor_type": "string"          // Executor type
            }
        },
        "performance_indicators": {
            "caching_strategy": "string",          // Simple caching strategy indicator
            "async_processing": "boolean",         // Whether async processing is detected
            "connection_pooling": {
                "max_connections": "integer",      // Maximum connections detected
                "timeout_ms": "integer"            // Connection timeout detected
            },
            "pagination_patterns": ["array"]       // Pagination patterns detected (offset_limit, cursor_based, etc.)
        },
        "external_dependencies": [
            {
                "name": "string",                  // External system name
                "type": "string",                  // Dependency type (database, external_api, message_queue, etc.)
                "connection_string": "string",     // Connection details
                "authentication": "string",        // Authentication method
                "timeout_ms": "integer",           // Connection timeout
                "retry_policy": "string",          // Retry strategy
                "circuit_breaker": "boolean",      // Whether circuit breaker is used
                "required": "boolean"              // Whether dependency is critical
            }
        ],
        "data_dependencies": [
            "string"                               // Simple array of table/data source names this component depends on
        ],
        "error_handling": {
            "global_handler": "boolean",          // Whether global error handler exists
            "exception_mapping": "object",        // Exception to HTTP status mapping
            "logging_strategy": "string",         // How errors are logged
            "user_error_messages": "boolean",     // Whether user-friendly messages are provided
            "retry_mechanisms": ["array"]         // Retry strategies for different error types
        },
        "service_interactions": [
            {
                "service_name": "string",          // Target service name
                "service_domain": "string",        // Service business domain
                "interactions": [
                    {
                        "action": "string",        // Triggering action name
                        "service_method": "string", // Target service method
                        "data_flow": "string",     // Data flow description
                        "trigger": "string",       // What triggers this interaction
                        "confidence": "float 0-1"  // Interaction mapping confidence
                    }
                ]
            }
        ]
    }
}
```

---

## 🔗 Service Interactions

```json
{
    "service_interactions": [
        {
            "service_name": "string",              // Target service name
            "service_domain": "string",            // Service business domain
            "interaction_type": "string",          // Type of interaction (direct_call, event_driven, etc.)
            "description": "string",               // LLM-generated interaction description
            "interactions": [
                {
                    "action": "string",            // Triggering action name
                    "service_method": "string",    // Target service method
                    "data_flow": "string",         // Data flow description
                    "trigger": "string",           // What triggers this interaction
                    "synchronous": "boolean",      // Whether call is synchronous
                    "transaction_boundary": "string", // Transaction scope
                    "error_handling": ["array"],   // How errors are handled
                    "retry_policy": "string",      // Retry strategy
                    "timeout_ms": "integer",       // Interaction timeout
                    "circuit_breaker": "boolean",  // Whether circuit breaker is used
                    "confidence": "float 0-1"      // Interaction mapping confidence
                }
            ]
        }
    ]
}
```

---

## ✅ Validation Results

```json
{
    "validation_results": {
        "schema_compliance": "boolean",            // Whether output matches this schema
        "completeness_score": "float 0-1",        // Percentage of schema populated
        "consistency_score": "float 0-1",         // Internal consistency rating
        "business_logic_validation": "string",     // Business logic validation result
        "issues_identified": "integer",           // Number of issues found
        "recommendations": ["array"],             // Recommendations for improvement
        "confidence_distribution": {
            "high_confidence": "integer",          // Count of high-confidence components (>0.8)
            "medium_confidence": "integer",        // Count of medium-confidence components (0.6-0.8)
            "low_confidence": "integer",           // Count of low-confidence components (<0.6)
            "average_confidence": "float 0-1"      // Average confidence across all components
        },
        "extraction_quality": {
            "ast_analysis_coverage": "float 0-1",  // Percentage of code analyzed by AST
            "configuration_coverage": "float 0-1", // Percentage of configs analyzed
            "llm_analysis_coverage": "float 0-1",  // Percentage analyzed by LLM
            "relationship_coverage": "float 0-1"   // Percentage of relationships mapped
        }
    }
}
```

---

## 📏 Schema Validation Rules

### **Required Fields:**
- `metadata.project_name` - Must be non-empty string
- `metadata.analysis_date` - Must be valid ISO 8601 timestamp
- `components` - Must be non-empty array
- Each component must have: `name`, `component_type`, `files` array

### **Data Type Constraints:**
- All confidence scores must be floats between 0 and 1
- All timestamps must be ISO 8601 format
- All arrays must be valid JSON arrays (can be empty)
- Integer fields must be non-negative

### **Business Logic Constraints:**
- Component names must be unique within the components array
- Service interactions must reference valid service components
- File paths must be valid filesystem paths
- Confidence scores should reflect extraction method reliability

### **Cross-Reference Integrity:**
- Service interactions must reference components that exist in the components array
- Dependencies must reference valid component or external system names
- Framework hints must align with detected frameworks in metadata

---

## 🔄 Schema Evolution

### **Version Compatibility:**
- Schema version is tracked in `metadata.pipeline_version`
- Backward compatibility maintained for minor version changes
- Major version changes may require data migration

### **Extension Points:**
- Additional attributes can be added to any object without breaking compatibility
- New component types can be added to `component_type` enum
- Custom validation rules can be added to `validation_results`

---

**Schema Maintainers:** CodeSight Development Team  
**Review Cycle:** Updated with each major pipeline enhancement  
**Next Review:** August 22, 2025
