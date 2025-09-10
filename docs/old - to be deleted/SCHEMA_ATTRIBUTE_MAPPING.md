# Schema Attribute Extraction Mapping

**Version:** 1.0  
**Date:** July 22, 2025  
**Purpose:** Define exactly how each TARGET_SCHEMA attribute will be extracted

---

## 📋 Overview| `functional_requirements.integrations[].name` | AST + CONFIG | STEP02 + STEP04 | Class name + configuration name | 85% | Service class + config bean name |
| `functional_requirements.integrations[].type` | AST + CONFIG | STEP02 + STEP04 | Interface analysis + framework detection | 80% | RestTemplate, JMS, JDBC patterns |
| `functional_requirements.integrations[].description` | LLM | STEP05 | LLM-generated integration description | 60% | Generated from code analysis |
| `functional_requirements.integrations[].external_system` | CONFIG + LLM | STEP04 + STEP05 | Configuration properties + analysis | 70% | URLs, connection strings |
| `functional_requirements.integrations[].protocol` | CONFIG + AST | STEP04 + STEP02 | Configuration + import analysis | 75% | HTTP, JMS, JDBC detection |is document maps every attribute in TARGET_SCHEMA.md to the specific extraction method, step, and confidence level. This serves as the authoritative blueprint for implementation and ensures complete coverage of the target schema.

**Extraction Methods:**
- **FILE** - File system analysis (STEP01)
- **AST** - Abstract Syntax Tree parsing (STEP02)
- **EMBEDDINGS** - Vector embeddings and semantic similarity analysis (STEP03)
- **CONFIG** - Configuration file analysis (STEP04)
- **LLM** - Large Language Model semantic analysis (STEP05)
- **RELATIONSHIP** - Relationship mapping analysis (STEP06)
- **AGGREGATION** - Data consolidation and calculation (STEP07)

---

## 🏗️ Root Schema Mapping

### **Metadata Section**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `metadata.project_name` | FILE | STEP01 | Extract from build files (pom.xml, build.xml) or directory name | 95% | Primary from build files, fallback to directory name |
| `metadata.analysis_date` | AGGREGATION | STEP07 | System timestamp when analysis runs | 100% | Generated during output creation |
| `metadata.pipeline_version` | AGGREGATION | STEP07 | CodeSight version constant | 100% | Hardcoded version string |
| `metadata.languages_detected` | FILE | STEP01 | File extension analysis and content detection | 90% | Extension-based detection with content validation |
| `metadata.frameworks_detected` | FILE + CONFIG | STEP01 + STEP04 | Dependencies in build files + configuration patterns | 85% | Maven/Gradle deps + Spring/Hibernate configs |
| `metadata.total_files_analyzed` | FILE | STEP01 | File inventory count | 100% | Direct file system count |
| `metadata.confidence_score` | AGGREGATION | STEP07 | Weighted average of all component confidences | 95% | Calculated from component-level scores |
| `metadata.extraction_summary.components_extracted` | AGGREGATION | STEP07 | Count of identified components | 100% | Component array length |
| `metadata.extraction_summary.screens_identified` | AGGREGATION | STEP07 | Count of screen-type components | 100% | Filter components by type |
| `metadata.extraction_summary.services_identified` | AGGREGATION | STEP07 | Count of service-type components | 100% | Filter components by type |
| `metadata.extraction_summary.utilities_identified` | AGGREGATION | STEP07 | Count of utility-type components | 100% | Filter components by type |
| `metadata.extraction_summary.integrations_identified` | AGGREGATION | STEP07 | Count of integration-type components | 100% | Filter components by type |
| `metadata.extraction_summary.business_rules_extracted` | AGGREGATION | STEP07 | Count of all business rules across components | 100% | Sum business rules from all components |
| `metadata.extraction_summary.service_interactions_mapped` | AGGREGATION | STEP07 | Count of service interaction relationships | 100% | Sum interactions from all components |
| `metadata.architecture_patterns.primary_pattern` | CONFIG + LLM | STEP04 + STEP05 | Spring MVC detection + LLM pattern recognition | 70% | Configuration analysis enhanced by LLM |
| `metadata.architecture_patterns.mvc_compliance` | CONFIG + AST | STEP04 + STEP02 | Controller/Service/Repository pattern detection | 80% | Package structure + class analysis |
| `metadata.architecture_patterns.dependency_injection` | CONFIG + AST | STEP04 + STEP02 | Spring annotations + configuration files | 85% | @Autowired detection + Spring configs |
| `metadata.architecture_patterns.transaction_management` | CONFIG + AST | STEP04 + STEP02 | @Transactional annotations + config files | 85% | Annotation scanning + configuration |
| `metadata.architecture_patterns.security_model` | CONFIG + AST | STEP04 + STEP02 | Security annotations + Spring Security config | 80% | Security configuration analysis |

---

## 🧩 Component Base Attributes

### **Component Creation Strategy**

**IMPORTANT:** Components are NOT created in STEP02. STEP02 works with subdomain-based groupings from STEP01 and extracts pure code structure. Meaningful component creation requires semantic similarity analysis and business understanding, which only becomes available in STEP05.

**STEP02 Focus:**
- Subdomain-based file groupings (from STEP01)
- AST parsing of classes, methods, annotations
- Technical artifact identification
- Code structure extraction

**Component Creation in STEP05:**
- Semantic clustering via embeddings (STEP03)
- LLM business logic analysis
- Meaningful component boundaries based on business concepts
- Understanding that "billing" and "billmgmt" are related
- Knowledge that "BillingsByUser" belongs with reporting, not billing

### **Common Component Fields** (Created in STEP05)

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `components[].name` | LLM + EMBEDDINGS + AST | STEP05 + STEP03 + STEP02 | Semantic component creation from subdomain analysis + code structure | 85% | Business-meaningful component names from semantic analysis |
| `components[].component_type` | LLM + EMBEDDINGS + AST | STEP05 + STEP03 + STEP02 | Semantic similarity clustering + LLM business classification | 85% | Type classification based on business purpose, not just file patterns |
| `components[].domain` | LLM + EMBEDDINGS | STEP05 + STEP03 | LLM semantic analysis + vector similarity clustering | 80% | Business domain detection via semantic understanding |
| `components[].subdomain` | LLM + EMBEDDINGS | STEP05 + STEP03 | LLM semantic analysis + embedding-based similarity | 70% | Business subdomain grouping from semantic analysis |
| `components[].description` | LLM + EMBEDDINGS | STEP05 + STEP03 | LLM-generated description enhanced by similar component patterns | 75% | Business-focused descriptions from semantic understanding |
| `components[].confidence` | AGGREGATION | STEP07 | Weighted average of attribute confidences | 95% | Calculated per component after semantic creation |

### **Files Array** (Populated from STEP02 Subdomain Analysis)

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `components[].files[].path` | FILE | STEP01 | File system traversal | 100% | Direct file system data |
| `components[].files[].type` | FILE + AST | STEP01 + STEP02 | Extension analysis + class type detection | 90% | File extension + class stereotypes |
| `components[].files[].role` | AST + EMBEDDINGS + LLM | STEP02 + STEP03 + STEP05 | Class annotations + semantic similarity + LLM role analysis during component creation | 80% | Enhanced role detection when components are created in STEP05 |
| `components[].files[].framework_hints` | AST + CONFIG | STEP02 + STEP04 | Import statements + annotations | 85% | Spring imports, Hibernate annotations |
| `components[].files[].size_bytes` | FILE | STEP01 | File system metadata | 100% | Direct file system data |
| `components[].files[].last_modified` | FILE | STEP01 | File system metadata | 100% | Direct file system data |

---

## 📋 Functional Requirements Mapping

### **Screen Components (component_type: "screen")**

#### **Fields Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `functional_requirements.fields[].name` | AST | STEP02 | JSP/HTML form field parsing | 90% | Input name attributes and JSP variables |
| `functional_requirements.fields[].type` | AST | STEP02 | HTML input type or JSP tag analysis | 85% | Input type attributes, select tags |
| `functional_requirements.fields[].required` | AST + CONFIG | STEP02 + STEP04 | HTML required + validation annotations | 80% | HTML attributes + Bean Validation |
| `functional_requirements.fields[].max_length` | AST + CONFIG | STEP02 + STEP04 | HTML maxlength + @Size annotations | 75% | HTML attributes + validation constraints |
| `functional_requirements.fields[].validation_rules` | AST + CONFIG | STEP02 + STEP04 | Bean Validation annotations + JS validation | 80% | @NotNull, @Size, client-side validation |
| `functional_requirements.fields[].default_value` | AST | STEP02 | HTML value attributes + JSP expressions | 70% | Default values from markup |
| `functional_requirements.fields[].options` | AST | STEP02 | Select option tags + JSP option lists | 85% | Option/choice lists from HTML/JSP |
| `functional_requirements.fields[].css_classes` | AST | STEP02 | CSS class attributes in HTML/JSP | 75% | Class attributes from markup |
| `functional_requirements.fields[].help_text` | AST + LLM | STEP02 + STEP04 | HTML placeholders + LLM interpretation | 60% | Placeholder text + semantic analysis |
| `functional_requirements.fields[].error_messages` | CONFIG + AST | STEP04 + STEP02 | Validation message properties + inline text | 70% | Message bundles + JSP error text |

#### **Actions Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `functional_requirements.actions[].name` | AST | STEP02 | Form action names + button IDs | 85% | Form names, button identifiers |
| `functional_requirements.actions[].type` | AST | STEP02 | Form submission type + AJAX detection | 80% | Submit buttons, AJAX calls |
| `functional_requirements.actions[].endpoint` | AST + CONFIG | STEP02 + STEP04 | Form action URLs + controller mappings | 85% | Action attributes + @RequestMapping |
| `functional_requirements.actions[].method` | AST | STEP02 | Form method attributes | 90% | HTTP method from form/AJAX |
| `functional_requirements.actions[].trigger` | AST | STEP02 | Button types + event handlers | 75% | Submit buttons, click handlers |
| `functional_requirements.actions[].validation` | AST + CONFIG | STEP02 + STEP04 | Client/server validation detection | 70% | JS validation + server annotations |
| `functional_requirements.actions[].confirmation_required` | AST + LLM | STEP02 + STEP05 | JS confirm dialogs + LLM analysis | 65% | confirm() calls + semantic analysis |
| `functional_requirements.actions[].success_redirect` | AST + CONFIG | STEP02 + STEP04 | Controller redirect logic | 75% | Redirect URLs from controllers |
| `functional_requirements.actions[].error_handling` | AST + CONFIG | STEP02 + STEP04 | Try-catch blocks + error pages | 70% | Exception handling patterns |
| `functional_requirements.actions[].permissions_required` | AST + CONFIG | STEP02 + STEP04 | Security annotations + ACL config | 80% | @PreAuthorize, role requirements |

#### **Validations Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `functional_requirements.validations[].field` | AST + CONFIG | STEP02 + STEP04 | Validation annotation targets | 85% | Field names from validation rules |
| `functional_requirements.validations[].rules` | CONFIG + AST | STEP04 + STEP02 | Bean Validation + JS validation | 80% | @NotNull, @Size + client rules |
| `functional_requirements.validations[].client_side` | AST | STEP02 | JavaScript validation detection | 75% | JS validation libraries |
| `functional_requirements.validations[].server_side` | CONFIG + AST | STEP04 + STEP02 | Bean Validation annotations | 85% | Server-side validation annotations |
| `functional_requirements.validations[].error_messages` | CONFIG | STEP04 | Message properties + inline messages | 70% | Validation message configuration |

#### **Conditional Display Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `functional_requirements.conditional_display[].condition` | AST + LLM | STEP02 + STEP04 | JavaScript conditions + JSP logic | 60% | Complex business logic detection |
| `functional_requirements.conditional_display[].shows` | AST + LLM | STEP02 + STEP04 | DOM manipulation + JSP conditionals | 65% | Element visibility logic |
| `functional_requirements.conditional_display[].hides` | AST + LLM | STEP02 + STEP04 | DOM manipulation + JSP conditionals | 65% | Element hiding logic |
| `functional_requirements.conditional_display[].enables` | AST + LLM | STEP02 + STEP04 | Element state changes | 60% | Enable/disable logic |
| `functional_requirements.conditional_display[].disables` | AST + LLM | STEP02 + STEP04 | Element state changes | 60% | Enable/disable logic |

### **Service Components (component_type: "service")**

#### **Operations Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `functional_requirements.operations[].name` | AST | STEP02 | Method name extraction | 95% | Direct method name from AST |
| `functional_requirements.operations[].type` | AST + LLM | STEP02 + STEP04 | Method annotations + semantic analysis | 75% | @Service, @Repository + purpose |
| `functional_requirements.operations[].description` | LLM | STEP04 | LLM-generated method description | 65% | Generated from code analysis |
| `functional_requirements.operations[].parameters[].name` | AST | STEP02 | Method parameter names | 95% | Direct parameter extraction |
| `functional_requirements.operations[].parameters[].type` | AST | STEP02 | Parameter type information | 90% | Java type system |
| `functional_requirements.operations[].parameters[].required` | AST + CONFIG | STEP02 + STEP04 | Nullable annotations + validation | 80% | @Nullable, @NotNull detection |
| `functional_requirements.operations[].parameters[].validation_rules` | CONFIG + AST | STEP04 + STEP02 | Bean Validation on parameters | 75% | Parameter validation annotations |
| `functional_requirements.operations[].parameters[].default_value` | AST | STEP02 | Default parameter values | 70% | Method signature defaults |
| `functional_requirements.operations[].returns.type` | AST | STEP02 | Return type from method signature | 95% | Direct return type extraction |
| `functional_requirements.operations[].returns.description` | LLM | STEP04 | LLM-generated return description | 60% | Generated description |
| `functional_requirements.operations[].error_handling` | AST | STEP02 | Exception declarations + throws | 85% | Throws clauses + try-catch |
| `functional_requirements.operations[].business_logic` | LLM | STEP04 | LLM analysis of method implementation | 50% | Semantic analysis of code |
| `functional_requirements.operations[].side_effects` | AST + LLM | STEP02 + STEP04 | Database calls + external service calls | 70% | DAO calls + HTTP clients |

### **Utility Components (component_type: "utility")**

#### **Utilities Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `functional_requirements.utilities[].name` | AST | STEP02 | Method/class name extraction | 95% | Direct name from code |
| `functional_requirements.utilities[].type` | AST + LLM | STEP02 + STEP04 | Class purpose + semantic analysis | 75% | Pattern recognition + LLM |
| `functional_requirements.utilities[].description` | LLM | STEP04 | LLM-generated description | 65% | Generated from code analysis |
| `functional_requirements.utilities[].parameters` | AST | STEP02 | Method parameter extraction | 95% | Same as service operations |
| `functional_requirements.utilities[].returns` | AST | STEP02 | Return type extraction | 95% | Same as service operations |
| `functional_requirements.utilities[].usage_patterns` | AST + RELATIONSHIP | STEP02 + STEP05 | Call site analysis | 70% | Where utility is used |
| `functional_requirements.utilities[].is_static` | AST | STEP02 | Static method detection | 95% | Static modifier detection |
| `functional_requirements.utilities[].thread_safe` | AST + LLM | STEP02 + STEP04 | Synchronization + semantic analysis | 60% | Thread safety indicators |

#### **Constants Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `functional_requirements.constants[].name` | AST | STEP02 | Constant field names | 95% | Static final field detection |
| `functional_requirements.constants[].value` | AST | STEP02 | Constant values | 90% | Field initialization values |
| `functional_requirements.constants[].type` | AST | STEP02 | Field type information | 95% | Java type system |
| `functional_requirements.constants[].description` | LLM | STEP04 | LLM-generated description | 60% | Purpose analysis |
| `functional_requirements.constants[].usage_context` | RELATIONSHIP | STEP05 | Where constant is referenced | 75% | Usage analysis |
| `functional_requirements.constants[].scope` | AST | STEP02 | Visibility modifiers | 95% | public/private/protected |

#### **Enums Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `functional_requirements.enums[].name` | AST | STEP02 | Enum class names | 95% | Enum declaration detection |
| `functional_requirements.enums[].values` | AST | STEP02 | Enum value extraction | 95% | Enum constant names |
| `functional_requirements.enums[].description` | LLM | STEP04 | LLM-generated description | 60% | Purpose analysis |
| `functional_requirements.enums[].usage_context` | RELATIONSHIP | STEP05 | Where enum is used | 75% | Usage analysis |

### **Integration Components (component_type: "integration")**

#### **Integrations Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `functional_requirements.integrations[].name` | AST + CONFIG | STEP02 + STEP03 | Class name + configuration name | 85% | Service class + config bean name |
| `functional_requirements.integrations[].type` | AST + CONFIG | STEP02 + STEP03 | Interface analysis + framework detection | 80% | RestTemplate, JMS, JDBC patterns |
| `functional_requirements.integrations[].description` | LLM | STEP04 | LLM-generated description | 65% | Purpose analysis |
| `functional_requirements.integrations[].external_system` | CONFIG + LLM | STEP03 + STEP04 | Configuration properties + analysis | 70% | URLs, connection strings |
| `functional_requirements.integrations[].protocol` | CONFIG + AST | STEP03 + STEP02 | Configuration + import analysis | 75% | HTTP, JMS, JDBC detection |
| `functional_requirements.integrations[].operations[].name` | AST | STEP02 | Method names in client classes | 90% | Client method extraction |
| `functional_requirements.integrations[].operations[].method` | AST + CONFIG | STEP02 + STEP04 | HTTP method + configuration | 80% | @PostMapping, config properties |
| `functional_requirements.integrations[].operations[].endpoint` | CONFIG + AST | STEP03 + STEP02 | URL configuration + annotations | 75% | Base URLs + path mappings |
| `functional_requirements.integrations[].operations[].request_format` | AST + CONFIG | STEP02 + STEP03 | Content-Type headers + serialization | 70% | JSON/XML detection |
| `functional_requirements.integrations[].operations[].response_format` | AST + CONFIG | STEP02 + STEP03 | Accept headers + deserialization | 70% | Response format detection |
| `functional_requirements.integrations[].operations[].timeout_ms` | CONFIG | STEP03 | Timeout configuration properties | 80% | Client timeout settings |
| `functional_requirements.integrations[].operations[].retry_policy` | CONFIG + AST | STEP03 + STEP02 | Retry configuration + annotations | 70% | Retry mechanism detection |
| `functional_requirements.integrations[].operations[].circuit_breaker` | CONFIG + AST | STEP03 + STEP02 | Circuit breaker annotations/config | 70% | Hystrix, Resilience4j detection |
| `functional_requirements.integrations[].authentication.type` | CONFIG + AST | STEP03 + STEP02 | Security configuration + headers | 75% | Auth mechanism detection |
| `functional_requirements.integrations[].authentication.mechanism` | CONFIG + AST | STEP03 + STEP02 | Implementation details | 70% | How auth is implemented |
| `functional_requirements.integrations[].authentication.credentials_source` | CONFIG | STEP03 | Configuration properties | 75% | Where credentials are stored |
| `functional_requirements.integrations[].error_handling` | AST | STEP02 | Exception handling in clients | 75% | Error handling patterns |
| `functional_requirements.integrations[].fallback_strategy` | AST + LLM | STEP02 + STEP04 | Fallback logic analysis | 60% | What happens on failure |

#### **Message Patterns Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `functional_requirements.message_patterns[].pattern` | CONFIG + AST | STEP03 + STEP02 | JMS configuration + usage patterns | 70% | Message pattern detection |
| `functional_requirements.message_patterns[].queue_name` | CONFIG | STEP03 | JMS queue configuration | 85% | Queue names from config |
| `functional_requirements.message_patterns[].message_format` | AST + CONFIG | STEP02 + STEP03 | Serialization + configuration | 70% | Message format detection |
| `functional_requirements.message_patterns[].routing_key` | CONFIG | STEP03 | Message routing configuration | 75% | Routing configuration |
| `functional_requirements.message_patterns[].durability` | CONFIG | STEP03 | Queue durability settings | 80% | Persistence configuration |

---

## ⚙️ Technical Requirements Mapping

### **Dependencies Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `technical_requirements.dependencies[].name` | AST + CONFIG | STEP02 + STEP03 | @Autowired fields + configuration | 85% | Dependency injection detection |
| `technical_requirements.dependencies[].type` | AST | STEP02 | Field/parameter types | 90% | Interface/class types |
| `technical_requirements.dependencies[].required` | AST | STEP02 | @Autowired(required=false) detection | 80% | Injection requirement |
| `technical_requirements.dependencies[].injection_mechanism` | AST + CONFIG | STEP02 + STEP03 | @Autowired, @Inject, XML config | 85% | How dependency is injected |
| `technical_requirements.dependencies[].scope` | CONFIG + AST | STEP03 + STEP02 | @Scope annotations + config | 75% | Bean scope detection |
| `technical_requirements.dependencies[].qualifier` | AST | STEP02 | @Qualifier annotations | 80% | Specific bean qualifiers |
| `technical_requirements.dependencies[].interface` | AST | STEP02 | Interface implemented by dependency | 90% | Type hierarchy analysis |
| `technical_requirements.dependencies[].async_capable` | AST + LLM | STEP02 + STEP04 | @Async annotations + analysis | 70% | Async capability detection |

### **Data Storage Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `technical_requirements.data_storage[].table` | AST + CONFIG | STEP02 + STEP03 | @Table annotations + SQL queries | 85% | JPA entities + query analysis |
| `technical_requirements.data_storage[].operations` | AST | STEP02 | Repository method analysis + SQL | 80% | CRUD operation detection |
| `technical_requirements.data_storage[].key_fields` | AST + CONFIG | STEP02 + STEP03 | @Id, @Column annotations | 85% | Primary key detection |
| `technical_requirements.data_storage[].indexes` | CONFIG + AST | STEP03 + STEP02 | @Index annotations + DDL | 70% | Index configuration |
| `technical_requirements.data_storage[].constraints` | AST + CONFIG | STEP02 + STEP03 | JPA constraints + DDL | 75% | Database constraints |
| `technical_requirements.data_storage[].transaction_scope` | AST | STEP02 | @Transactional placement | 80% | Transaction boundary detection |
| `technical_requirements.data_storage[].isolation_level` | AST + CONFIG | STEP02 + STEP03 | @Transactional + config | 75% | Isolation level settings |

### **Security Constraints Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `technical_requirements.security_constraints[].type` | CONFIG + AST | STEP03 + STEP02 | Security config + annotations | 85% | Security constraint types |
| `technical_requirements.security_constraints[].mechanism` | CONFIG + AST | STEP03 + STEP02 | Security implementation details | 80% | How security is enforced |
| `technical_requirements.security_constraints[].required` | CONFIG + AST | STEP03 + STEP02 | Security requirement detection | 80% | Whether security is mandatory |
| `technical_requirements.security_constraints[].patterns` | CONFIG | STEP03 | URL patterns + method patterns | 85% | Security pattern matching |
| `technical_requirements.security_constraints[].roles` | CONFIG + AST | STEP03 + STEP02 | Required roles from config | 85% | Role requirements |
| `technical_requirements.security_constraints[].permissions` | CONFIG + AST | STEP03 + STEP02 | Permission requirements | 80% | Permission-based security |
| `technical_requirements.security_constraints[].expression` | AST | STEP02 | SpEL expressions in annotations | 75% | Security expressions |
| `technical_requirements.security_constraints[].enforcement_level` | CONFIG + AST | STEP03 + STEP02 | Where security is enforced | 80% | Method/class/global level |

### **Performance Patterns**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `technical_requirements.performance_patterns.caching.strategy` | CONFIG + AST | STEP03 + STEP02 | @Cacheable + cache config | 80% | Caching strategy detection |
| `technical_requirements.performance_patterns.caching.providers` | CONFIG | STEP03 | Cache provider configuration | 85% | EhCache, Redis, etc. |
| `technical_requirements.performance_patterns.caching.ttl_default` | CONFIG | STEP03 | Cache TTL configuration | 80% | Time-to-live settings |
| `technical_requirements.performance_patterns.caching.cache_regions` | CONFIG + AST | STEP03 + STEP02 | Cache region definitions | 75% | Named cache regions |
| `technical_requirements.performance_patterns.caching.eviction_policy` | CONFIG | STEP03 | Cache eviction configuration | 75% | Eviction strategies |
| `technical_requirements.performance_patterns.connection_pooling.type` | CONFIG | STEP03 | DataSource configuration | 85% | Pool implementation type |
| `technical_requirements.performance_patterns.connection_pooling.max_connections` | CONFIG | STEP03 | Pool size configuration | 90% | Maximum connections |
| `technical_requirements.performance_patterns.connection_pooling.min_connections` | CONFIG | STEP03 | Pool size configuration | 90% | Minimum connections |
| `technical_requirements.performance_patterns.connection_pooling.timeout_ms` | CONFIG | STEP03 | Connection timeout config | 85% | Connection timeout |
| `technical_requirements.performance_patterns.connection_pooling.validation_query` | CONFIG | STEP03 | Validation query configuration | 80% | Connection validation |
| `technical_requirements.performance_patterns.connection_pooling.validation_enabled` | CONFIG | STEP03 | Validation enablement | 85% | Whether validation is used |
| `technical_requirements.performance_patterns.transaction_management.type` | CONFIG + AST | STEP03 + STEP02 | Transaction manager config | 85% | Declarative vs programmatic |
| `technical_requirements.performance_patterns.transaction_management.propagation` | AST | STEP02 | @Transactional propagation | 80% | Transaction propagation |
| `technical_requirements.performance_patterns.transaction_management.isolation` | AST | STEP02 | @Transactional isolation | 80% | Isolation level |
| `technical_requirements.performance_patterns.transaction_management.timeout_seconds` | AST + CONFIG | STEP02 + STEP03 | Transaction timeout | 75% | Timeout configuration |
| `technical_requirements.performance_patterns.transaction_management.read_only` | AST | STEP02 | @Transactional readOnly | 85% | Read-only transactions |
| `technical_requirements.performance_patterns.async_processing.enabled` | AST + CONFIG | STEP02 + STEP03 | @Async annotations + config | 80% | Async processing detection |
| `technical_requirements.performance_patterns.async_processing.thread_pool_size` | CONFIG | STEP03 | Thread pool configuration | 75% | Async thread pool settings |
| `technical_requirements.performance_patterns.async_processing.queue_capacity` | CONFIG | STEP03 | Queue configuration | 75% | Async queue settings |
| `technical_requirements.performance_patterns.async_processing.executor_type` | CONFIG | STEP03 | Executor configuration | 75% | Type of executor used |

### **Performance Indicators** (Simpler Detection)

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `technical_requirements.performance_indicators.caching_strategy` | CONFIG + AST | STEP03 + STEP02 | Simple cache detection | 75% | Basic caching indicator |
| `technical_requirements.performance_indicators.async_processing` | AST | STEP02 | @Async detection | 85% | Simple async indicator |
| `technical_requirements.performance_indicators.connection_pooling.max_connections` | CONFIG | STEP03 | Basic pool size detection | 85% | Simple pool indicator |
| `technical_requirements.performance_indicators.connection_pooling.timeout_ms` | CONFIG | STEP03 | Basic timeout detection | 80% | Simple timeout indicator |
| `technical_requirements.performance_indicators.pagination_patterns` | AST | STEP02 | Pagination method detection | 70% | Pageable, Offset patterns |

### **External Dependencies Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `technical_requirements.external_dependencies[].name` | CONFIG + AST | STEP03 + STEP02 | Service names + configuration | 80% | External system names |
| `technical_requirements.external_dependencies[].type` | CONFIG + AST | STEP03 + STEP02 | Connection type detection | 75% | Database, API, queue types |
| `technical_requirements.external_dependencies[].connection_string` | CONFIG | STEP03 | Connection configuration | 85% | Database URLs, API endpoints |
| `technical_requirements.external_dependencies[].authentication` | CONFIG | STEP03 | Authentication configuration | 75% | Auth method detection |
| `technical_requirements.external_dependencies[].timeout_ms` | CONFIG | STEP03 | Timeout configuration | 80% | Connection timeouts |
| `technical_requirements.external_dependencies[].retry_policy` | CONFIG + AST | STEP03 + STEP02 | Retry configuration | 70% | Retry strategies |
| `technical_requirements.external_dependencies[].circuit_breaker` | CONFIG + AST | STEP03 + STEP02 | Circuit breaker detection | 70% | Resilience patterns |
| `technical_requirements.external_dependencies[].required` | CONFIG + LLM | STEP03 + STEP04 | Criticality analysis | 65% | Dependency criticality |

### **Data Dependencies Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `technical_requirements.data_dependencies[]` | AST + CONFIG | STEP02 + STEP03 | Table references + entity analysis | 80% | Simple table name list |

### **Error Handling**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `technical_requirements.error_handling.global_handler` | AST + CONFIG | STEP02 + STEP03 | @ControllerAdvice detection | 85% | Global error handler detection |
| `technical_requirements.error_handling.exception_mapping` | CONFIG + AST | STEP03 + STEP02 | Exception-to-status mapping | 75% | Error mapping configuration |
| `technical_requirements.error_handling.logging_strategy` | CONFIG + AST | STEP03 + STEP02 | Logging configuration + usage | 80% | How errors are logged |
| `technical_requirements.error_handling.user_error_messages` | CONFIG + AST | STEP03 + STEP02 | User-friendly error messages | 70% | Error message handling |
| `technical_requirements.error_handling.retry_mechanisms` | AST + CONFIG | STEP02 + STEP03 | Retry logic detection | 70% | Error retry strategies |

### **Service Interactions Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `technical_requirements.service_interactions[].service_name` | RELATIONSHIP | STEP05 | Call graph analysis | 85% | Service interaction detection |
| `technical_requirements.service_interactions[].service_domain` | LLM + RELATIONSHIP | STEP04 + STEP05 | Domain classification | 70% | Business domain mapping |
| `technical_requirements.service_interactions[].interactions[].action` | RELATIONSHIP | STEP05 | Method call analysis | 80% | Action that triggers call |
| `technical_requirements.service_interactions[].interactions[].service_method` | RELATIONSHIP | STEP05 | Called method identification | 85% | Target method name |
| `technical_requirements.service_interactions[].interactions[].data_flow` | RELATIONSHIP + LLM | STEP05 + STEP04 | Data flow analysis | 65% | How data flows between components |
| `technical_requirements.service_interactions[].interactions[].trigger` | RELATIONSHIP | STEP05 | What triggers the interaction | 75% | Trigger event identification |

---

## 🔗 Service Interactions (Top-level)

### **Service Interactions Array**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `service_interactions[].service_name` | RELATIONSHIP | STEP05 | Call graph analysis | 85% | Service relationship mapping |
| `service_interactions[].service_domain` | LLM + RELATIONSHIP | STEP04 + STEP05 | Domain classification | 70% | Business domain mapping |
| `service_interactions[].interaction_type` | RELATIONSHIP + LLM | STEP05 + STEP04 | Interaction pattern analysis | 65% | Type of interaction |
| `service_interactions[].description` | LLM | STEP04 | LLM-generated description | 60% | Interaction description |
| `service_interactions[].interactions[].action` | RELATIONSHIP | STEP05 | Action identification | 80% | Triggering action |
| `service_interactions[].interactions[].service_method` | RELATIONSHIP | STEP05 | Method call analysis | 85% | Called method |
| `service_interactions[].interactions[].data_flow` | RELATIONSHIP + LLM | STEP05 + STEP04 | Data flow description | 65% | Data movement description |
| `service_interactions[].interactions[].trigger` | RELATIONSHIP | STEP05 | Trigger identification | 75% | What causes interaction |
| `service_interactions[].interactions[].synchronous` | AST + RELATIONSHIP | STEP02 + STEP05 | Sync/async detection | 75% | Call synchronicity |
| `service_interactions[].interactions[].transaction_boundary` | AST + RELATIONSHIP | STEP02 + STEP05 | Transaction scope analysis | 70% | Transaction boundaries |
| `service_interactions[].interactions[].error_handling` | AST + RELATIONSHIP | STEP02 + STEP05 | Error handling in interactions | 70% | How errors are handled |
| `service_interactions[].interactions[].retry_policy` | CONFIG + AST | STEP03 + STEP02 | Retry configuration | 65% | Retry strategies |
| `service_interactions[].interactions[].timeout_ms` | CONFIG + AST | STEP03 + STEP02 | Timeout configuration | 70% | Interaction timeouts |
| `service_interactions[].interactions[].circuit_breaker` | CONFIG + AST | STEP03 + STEP02 | Circuit breaker detection | 65% | Resilience patterns |

---

## ✅ Validation Results Mapping

### **Validation Results**

| Attribute | Source | Step | Method | Confidence | Notes |
|-----------|--------|------|--------|------------|-------|
| `validation_results.schema_compliance` | AGGREGATION | STEP07 | Schema validation logic | 100% | JSON schema validation |
| `validation_results.completeness_score` | AGGREGATION | STEP07 | Field population percentage | 95% | Calculated completeness |
| `validation_results.consistency_score` | AGGREGATION | STEP07 | Cross-reference validation | 90% | Data consistency checks |
| `validation_results.business_logic_validation` | AGGREGATION | STEP07 | Business rule validation | 85% | Logic consistency |
| `validation_results.issues_identified` | AGGREGATION | STEP07 | Issue counting | 95% | Total issues found |
| `validation_results.recommendations` | AGGREGATION + LLM | STEP07 + STEP04 | Improvement suggestions | 70% | Generated recommendations |
| `validation_results.confidence_distribution.high_confidence` | AGGREGATION | STEP07 | Confidence counting | 100% | Count >0.8 confidence |
| `validation_results.confidence_distribution.medium_confidence` | AGGREGATION | STEP07 | Confidence counting | 100% | Count 0.6-0.8 confidence |
| `validation_results.confidence_distribution.low_confidence` | AGGREGATION | STEP07 | Confidence counting | 100% | Count <0.6 confidence |
| `validation_results.confidence_distribution.average_confidence` | AGGREGATION | STEP07 | Average calculation | 100% | Weighted average |
| `validation_results.extraction_quality.ast_analysis_coverage` | AGGREGATION | STEP07 | AST analysis percentage | 95% | % of files analyzed by AST |
| `validation_results.extraction_quality.configuration_coverage` | AGGREGATION | STEP07 | Config analysis percentage | 95% | % of configs analyzed |
| `validation_results.extraction_quality.llm_analysis_coverage` | AGGREGATION | STEP07 | LLM analysis percentage | 90% | % analyzed by LLM |
| `validation_results.extraction_quality.relationship_coverage` | AGGREGATION | STEP07 | Relationship mapping percentage | 85% | % of relationships mapped |

---

## 📊 Extraction Priority Matrix

### **High Priority (90%+ Confidence)**
1. **File System Metadata** - Direct file system data
2. **AST Structural Data** - Class names, method signatures, annotations
3. **Configuration Properties** - Direct configuration values
4. **Component Counting** - Aggregated statistics

### **Medium Priority (70-90% Confidence)**
1. **Framework Detection** - Pattern-based analysis
2. **Security Annotations** - Spring Security detection
3. **Database Operations** - JPA entity analysis
4. **Service Dependencies** - Injection analysis

### **Lower Priority (50-70% Confidence)**
1. **LLM-Generated Content** - Descriptions, business logic
2. **Complex Business Rules** - Semantic analysis required
3. **Integration Patterns** - Complex pattern recognition
4. **Conditional Logic** - JavaScript/JSP logic analysis

---

## 🧠 STEP03: Embeddings & FAISS Integration

### **Purpose & Enhancement Strategy**
STEP03 enhances the structural data from STEP02 by adding semantic vector analysis without changing the output schema. The same JSON structure is maintained, but key attributes are enriched with higher confidence scores and improved accuracy through semantic similarity analysis. **Components are NOT created in STEP03** - it works with subdomain-based groupings and prepares semantic context for component creation in STEP05.

### **Enhanced Attributes via Embeddings** (Subdomain-Level Analysis)

#### **Subdomain Classification Enhancement**
| Original Attribute | Enhancement Method | Confidence Improvement | Details |
|-------------------|-------------------|----------------------|---------|
| `subdomains[].preliminary_subdomain_type` | Semantic clustering of similar code patterns | +10% | Group subdomain files by semantic similarity to improve type classification |
| `subdomains[].layers` | Vector similarity clustering | +5% | Cluster files by semantic meaning to better identify architectural layers |
| `subdomains[].framework_hints` | Context-aware semantic analysis | +5% | Use similar subdomain context to enhance framework detection |

#### **Method & Function Enhancement** (Within Subdomains)
| Original Attribute | Enhancement Method | Confidence Improvement | Details |
|-------------------|-------------------|----------------------|---------|
| `files[].role` | Pattern similarity matching | +5% (75% → 80%) | Match against known role patterns from embedding clusters |
| `files[].framework_hints` | Context from similar files | Enhanced quality | Improve framework detection using context from semantically similar files |

### **FAISS Vector Database Structure**

#### **Chunking Strategy**
- **Method-Level Chunks**: Individual Java methods with surrounding context
- **Class-Level Chunks**: Complete class definitions with key methods
- **Configuration Chunks**: Configuration blocks and their related code sections
- **Subdomain Chunks**: Related files grouped by semantic similarity within subdomains

#### **Vector Enhancement Process**
1. **Code Vectorization**: Convert code chunks to embeddings using code-specific models
2. **Similarity Clustering**: Group semantically similar files within and across subdomains using FAISS
3. **Pattern Recognition**: Identify recurring patterns across similar files and subdomains
4. **Context Enrichment**: Enhance attribute extraction using similar file/subdomain context
5. **Semantic Preparation**: Prepare semantic clusters for component creation in STEP05

### **Integration Points with Other Steps**

#### **STEP02 → STEP03 Enhancement Flow** (Subdomain-Based)
```
STEP02 Output: {
  "subdomains": [{
    "name": "billing",
    "preliminary_subdomain_type": "service",      // 75% confidence from file patterns
    "framework_hints": ["spring"],               // 80% confidence from imports
    "files": [...]
  }]
}

STEP03 Output: {
  "subdomains": [{
    "name": "billing",
    "preliminary_subdomain_type": "service",      // 85% confidence (enhanced by semantic clustering)
    "framework_hints": ["spring", "hibernate"],  // 85% confidence (enhanced by similar subdomains)
    "files": [...],
    "_embedding_metadata": {                      // Optional: debugging/tracing info
      "similar_subdomains": ["billing-mgmt", "invoice"],
      "semantic_cluster": "financial-services",
      "confidence_boost": "+10%"
    }
  }]
}
```

#### **STEP05 Integration (Component Creation from Enhanced Subdomains)**
- STEP03 embeddings provide semantic clusters that help STEP05 understand which subdomains should be grouped into components
- Similar subdomain blocks can be analyzed together for component boundary decisions
- Semantic understanding helps LLM make better component creation decisions

### **Technical Implementation Notes**
- **Output Schema**: Identical to STEP02 (step03_output.json = enhanced step02_output.json)
- **Subdomain Focus**: Works with subdomain groupings, not components
- **Semantic Preparation**: Prepares semantic context for component creation in STEP05
- **Performance**: Vector operations run in parallel with STEP02 processing where possible
- **Memory Management**: FAISS indices managed efficiently for large codebases
- **Component Creation**: **NO COMPONENTS CREATED** - semantic enhancement only

---

## 🎯 Implementation Guidelines

### **Step Responsibilities**
- **STEP01**: File discovery, basic metadata, language detection, subdomain grouping
- **STEP02**: All AST-based extraction, structural analysis of code within subdomains (NO component creation)
- **STEP03**: Embeddings analysis, semantic enhancement (same output schema as STEP02)
- **STEP04**: Configuration analysis, framework-specific patterns
- **STEP05**: LLM enhancement, semantic analysis, descriptions, **COMPONENT CREATION** via semantic clustering
- **STEP06**: Relationship mapping, interaction analysis
- **STEP07**: Data consolidation, validation, confidence calculation

### **Confidence Calculation**
- Each attribute extraction method has a base confidence
- Multiple sources can improve confidence through validation
- Final confidence is weighted average of contributing sources
- Component confidence is weighted average of attribute confidences

### **Quality Thresholds**
- **Required Fields**: 90%+ population rate
- **Optional Fields**: 60%+ population rate
- **Cross-References**: 80%+ resolution rate
- **Business Logic**: 50%+ extraction rate (due to complexity)

---

**Next Actions:**
1. Review and validate this mapping
2. Update individual STEP documents with specific extraction logic
3. Implement extraction methods according to this blueprint
4. Create validation logic based on confidence thresholds
