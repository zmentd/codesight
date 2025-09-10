# STEP02: Minimal Structural Extraction

**Version:** 2.0  
**Date:** July 30, 2025  
**Purpose:** Minimal AST parsing for explicit structural data extraction - NO component creation

---

## 📋 Step Overview

### **Primary Responsibility**
**Pure structural extraction only** - parse source code to extract explicit structural elements without interpretation or component creation. Component creation happens in STEP05 based on semantic similarity analysis.

### **Processing Context**
- **Pipeline Position:** Second step in the CodeSight pipeline  
- **Dependencies:** STEP01 output (step01_output.json) with Unix relative paths
- **Processing Time:** 15-20% of total pipeline time (reduced scope)
- **Confidence Level:** 95%+ (direct code parsing, no interpretation)

### **What STEP02 Does (Minimal Scope):**
- Extract class structures, method signatures, and field definitions
- Parse explicit configuration files (Struts XML, web.xml, etc.)
- Identify explicit linking patterns (JPA mappings, Struts actions)
- Collect all structural data for semantic analysis in STEP05

### **What STEP02 Does NOT Do:**
- ❌ **No component creation** - components are created in STEP05
- ❌ **No framework assumptions** - no hardcoded Spring/modern framework patterns
- ❌ **No component type classification** - semantic analysis handles this
- ❌ **No architectural interpretation** - raw structural data only

### **Data Flow Integration**

#### **Data Requirements from STEP01:**
- **File inventory with Unix relative paths** - For parsing target identification
- **Project root path** - For path normalization
- **Language version detection** - For parser configuration

---

## �️ Design Principles

### **Project and Language Agnostic Design**
- **All core AST parsing logic must be project and language agnostic**
- **Language-specific parsers must be abstracted into configurable modules**
- **Framework detection patterns are configuration-driven, not hard-coded**
- **Component type classification uses configurable rules from STEP01**
- **Project-specific architectural patterns (asl, dsl, gsl, isl) are handled through configuration**

### **Standardized Path Handling**
- **All file paths in output must be relative to the project root directory**
- **All paths must use Unix-style forward slashes (/) regardless of host operating system**
- **No absolute paths are permitted in any output or intermediate data**
- **Every file reference must include a relative path for complete traceability**
- **Path normalization from STEP01 is maintained throughout processing**

### **Architectural Override Support**
- **Custom architectural patterns from STEP01 are applied during component classification**
- **Package pattern matching uses configuration-driven rules with confidence scoring**
- **Component type hints are enhanced based on project-specific patterns**

---

## �🎯 Requirements Alignment

### **Functional Requirements Covered**
- **FR-001: Multi-Technology Support** - Parse Java 8-21 syntax, Spring annotations
- **FR-002: Comprehensive Component Analysis** - Extract detailed component structures
- **FR-003: Business Rule Extraction** - Identify validation annotations and method logic patterns
- **FR-006: Project and Language Agnostic Design** - All parsing logic is configurable and language-neutral
- **FR-006: Standardized Path Handling** - All paths are Unix relative format
- **FR-007: Project-Specific Architectural Overrides** - Support custom architectural directories


## 📥 Input Specifications

### **Primary Input**
- **step01_output.json** - File inventory and metadata from STEP01
- **Source Code Files** - Java, JSP, HTML files identified in STEP01 (Unix relative paths)
- **Configuration** - Two-tier YAML configuration system from STEP01:
  - `config.yaml` - Common configuration settings (framework patterns, parsing settings)
  - `config-<project>.yaml` - Project-specific configuration (architectural overrides)

