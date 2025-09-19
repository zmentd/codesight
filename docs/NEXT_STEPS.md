# CodeSight Pipeline Improvement Plan

## Executive Summary

Based on analysis of the ct-hr-storm project outputs, the CodeSight pipeline requires significant improvements to deliver on its mission of extracting comprehensive business and technical requirements for modernization planning. The current output resembles a code inventory rather than actionable business requirements.

## Key Issues Identified

- **Step 04** ✅ **COMPLETED**: Added JSP functional classification (business_screen, menu_navigation, report_dashboard, etc.) with UI complexity analysis
- **Step 05** produces 81 fine-grained capabilities instead of 5-15 business domains  
- **Missing technical depth** required for modernization (CRUD matrices, security architecture, integration inventory)
- **Poor data quality** with 120K+ filtered relationships suggesting false positives
- **Wrong output format** - needs CSV/HTML reports and queryable outputs for stakeholders

---

## Primary Solutions Required

### 1. Fix Step 05 - Capability Assembly & Business Grouping

**Current Problem**: Step 05 creates one capability per route (81 capabilities) instead of grouping routes by business function

**Solution**: Step 05 needs to implement:

- **Pre-LLM Business Grouping**: Group routes by URL patterns, shared data tables, and common security roles before LLM processing
- **HR Domain-Aware LLM Prompts**: Include HR business taxonomy (Employee Management, Scheduling, Payroll, etc.) to guide business understanding
- **Business Aggregation Logic**: Use LLM to identify when multiple technical routes serve the same business capability (e.g., "Employee Scheduling" vs separate route capabilities)
- **Route Pattern Analysis**: Cluster routes by URL segments (/employee/*, /schedule/*, /payroll/*) and shared backend resources

### 2. ✅ Step 04 JSP Classification - COMPLETED

**Problem Solved**: JSP entities were generic without functional differentiation

**Solution Implemented**: Enhanced Step 04 with comprehensive JSP classification:

- **Functional Classification**: Categorizes JSPs as business_screen, menu_navigation, report_dashboard, error_utility, admin_setup, dialog_modal
- **UI Complexity Analysis**: Rates JSPs as simple/medium/complex based on content analysis  
- **Enhanced Metadata**: All JSP entities now include jsp_function_type, ui_complexity, is_component, has_forms, has_security, classification_confidence
- **Business Domain Hints**: Extracts domain context from file path structure (asl, dsl, gsl, isl)

**Impact**: Step 05 can now distinguish between actual business screens (~500+) vs navigation/utility components, leading to better business domain analysis.

### 3. 🎯 CURRENT WORK: Step 05 Business Grouping Implementation

**Current Status**: Enhanced Step 05 with business domain grouping algorithm

**Solution Implemented**: Business-domain-first grouping:

1. **✅ Pre-LLM Route Clustering**: Group routes by URL patterns (/employee/*, /schedule/*, /payroll/*), shared tables, and security roles
2. **✅ Enhanced LLM Context**: Give LLM multiple related routes to identify business capabilities vs individual technical routes  
3. **✅ Business Domain Discovery**: Extract business domains from URL patterns (employee_management, scheduling, payroll, etc.)
4. **✅ Resource-Based Merging**: Merge routes that share tables or security roles into coherent business capabilities
5. **✅ Quality Validation**: Create 5-15 meaningful business domains instead of 81+ technical routes

**Expected Impact**: Step 05 will now create business capabilities like "Employee Management" (covering multiple employee routes) instead of separate capabilities for each route.

### 4. Fix Step 04 Data Quality - REMAINING WORK

**Current Problem**: Missing the detailed technical analysis required for modernization

**Solution**: Add extractors for:

- **CRUD Matrices**: Which components read/write/delete which data entities
- **Performance Signals**: Pagination patterns, caching, threading, heavy queries
- **Security Architecture**: Complete IAM mapping, permission matrices, crypto usage
- **Integration Inventory**: External APIs, databases, file systems, scheduled jobs
- **Risk Analysis**: God classes, tight coupling, direct DB access from UI

### 4. Improve Data Quality & Confidence

**Current Problem**: 120K+ filtered relationships suggests data quality issues

**Solution**:

- **Better Confidence Scoring**: Weight relationships by multiple factors (frequency, context, naming patterns)
- **False Positive Reduction**: Improve AST parsing to reduce spurious relationships
- **Evidence Bundling**: Include actual code snippets and line numbers for each relationship
- **Quality Gates**: Enforce minimum evidence thresholds before including relationships

### 5. Fix Output Format & Presentation

**Current Problem**: Wrong output format for modernization planning

**Solution**: Step 06 needs to generate:

- **Multiple Output Formats**: CSV/HTML reports for different stakeholders
- **Queryable Outputs**: Support "what changes if we modify X" queries
- **Component Documentation**: Per-component technical specs with APIs, dependencies, data ownership
- **Migration Planning**: IAM policy templates, service boundary recommendations, dependency cut-lines

---

## Implementation Priority

### Phase 1 (High Impact) - IMMEDIATE NEXT STEPS
1. **✅ COMPLETED: Step 04 JSP Classification** - Added functional differentiation (business_screen vs menu_navigation, etc.)
2. **🎯 NEXT: Fix Step 05 Business Grouping** - Change from route-per-capability to business domain grouping using our enhanced JSP data

### Phase 2 (Data Quality) - Weeks 2-3  
3. **Fix Step 04 Data Quality** - Reduce false positives and improve confidence scoring
4. **Add Missing Technical Extractors** - CRUD, security, performance, integration analysis

### Phase 3 (Output Enhancement) - Weeks 4-5
5. **Fix Step 06 Output Format** - Multiple formats, queryable outputs, migration planning

---

## Specific Code Changes Needed

### Step 05 Enhancements
- Implement business-first grouping algorithm (group routes by URL patterns, shared tables, security roles)
- Add HR domain taxonomy to LLM prompts (Employee Management, Scheduling, Payroll, Benefits, etc.)
- Create business aggregation logic to merge related technical routes into business capabilities
- Enhance confidence scoring based on business coherence rather than technical metrics

### Step 04 Improvements  
- Reduce false positive relationships through better AST analysis and context filtering
- Implement evidence bundling to group similar relationships and reduce noise
- Add relationship type-specific confidence thresholds and quality gates
- Improve rationale generation to explain why relationships were included/excluded

### New Technical Extractors
- Security analysis module (IAM mapping, crypto detection)
- Performance detector (pagination, caching patterns)
- Integration discovery (external APIs, file interfaces)
- Risk analyzer (coupling metrics, anti-patterns)

### Configuration Updates
- Business domain taxonomies for HR systems
- Confidence weighting schemes
- Output format templates
- Quality gate thresholds

---

## Success Criteria

**Output Quality**:
- 5-15 meaningful business domains (not 81 capabilities)
- Complete CRUD matrices showing data ownership
- User journeys with route→screen→data flows
- Comprehensive security and integration inventories

**Modernization Readiness**:
- CSV/HTML reports for different stakeholders
- Queryable outputs for impact analysis
- IAM policy templates and service boundary recommendations
- Evidence-backed technical debt and risk assessments

**Fundamental Shift**: The issue isn't that Steps 01-02 should do business analysis (they're correctly doing programmatic code analysis), but that **Step 05 isn't effectively using the LLM to aggregate technical data into business domains**. The current 1-capability-per-route approach needs to become business-domain-driven grouping.