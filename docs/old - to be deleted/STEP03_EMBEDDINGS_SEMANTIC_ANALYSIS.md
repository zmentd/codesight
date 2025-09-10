# STEP03: Embeddings & Semantic Vector Analysis Implementation

**Version:** 1.0  
**Date:** July 23, 2025  
**Purpose:** Detailed implementation specification for vector embeddings and FAISS-based semantic similarity analysis to enhance structural code analysis

> See also: STEP03_OUTPUTS_AND_SEARCH_API.md for persisted artifacts, schema, typed search API, and REPL usage.

---

## 📋 Step Overview

### **Primary Responsibility**
Vector embeddings generation and FAISS-based semantic similarity analysis to enhance the structural data from STEP02 through semantic clustering, pattern recognition, and context-aware enhancement without modifying the output schema.

### **Processing Context**
- **Pipeline Position:** Third step in the CodeSight pipeline
- **Dependencies:** STEP01 (file inventory) and STEP02 (AST structural data)
- **Processing Time:** 15-20% of total pipeline time
- **Confidence Level:** 75%+ (vector-based semantic analysis)

### **Data Flow Integration**
```
Input:  step01_output.json + step02_output.json + source code files
```


## 🧠 Technical Architecture

### **Vector Database Structure**

#### **Chunk Types & Strategy**
1. **Method-Level Chunks**
   - Individual Java methods with 3-5 lines of surrounding context
   - Include method signature, annotations, and key business logic
   - Size: 50-200 tokens per chunk

2. **Class-Level Chunks**
   - Complete class definitions with key methods
   - Include class annotations, inheritance, and primary methods
   - Size: 200-500 tokens per chunk

3. **Configuration Chunks**
   - Configuration blocks with related code sections
   - Include Spring configurations, property mappings
   - Size: 100-300 tokens per chunk

4. **Domain Chunks**
   - Related classes grouped by package or semantic purpose
   - Include cross-class relationships and patterns
   - Size: 300-800 tokens per chunk

#### **Vector Model Requirements**
- **Primary Model:** Code-specific embedding model (e.g., CodeBERT, GraphCodeBERT)
- **Fallback Model:** Generic text embedding model for configuration files
- **Vector Dimensions:** 768 (standard for most code models)
- **Similarity Metric:** Cosine similarity for semantic relationships

### **FAISS Index Configuration**
```yaml
faiss_config:
  index_type: "IndexFlatIP"  # Inner Product for cosine similarity
  dimension: 768
  memory_mapping: true
  batch_size: 1000
  similarity_threshold: 0.7
  max_results_per_query: 20
```

### **Data Storage & Persistence**

#### **Index Storage Location**
```yaml
storage_config:
  # All paths relative to project root, Unix-style forward slashes
  # Following CODE_STRUCTURE_SPECIFICATION.md requirements
  embeddings_directory: "projects/{project_name}/embeddings"
  faiss_index_file: "projects/{project_name}/embeddings/faiss_index.bin"
  metadata_file: "projects/{project_name}/embeddings/metadata.json"
  embedding_config_file: "projects/{project_name}/embeddings/embedding_config.json"
```

#### **Metadata Storage Schema**
```json
{
  "embeddings_metadata": {
    "version": "1.0",
    "model_info": {
      "primary_model": "microsoft/codebert-base",
      "model_hash": "sha256:abc123...",
      "vector_dimension": 768,
      "total_chunks": 1250
    },
    "chunk_mappings": [
      {
        "chunk_id": "chunk_001",
        "functional_name": "UserService",
        "path": "src/main/java/com/storm/user/UserService.java",
        "source_location": "Deployment/Storm_Aux/src",
        "chunk_type": "method",
        "start_line": 45,
        "end_line": 68,
        "method_name": "authenticateUser",
        "faiss_index": 0,
        "content_hash": "sha256:def456..."
      }
    ],
    "similarity_clusters": [
      {
        "cluster_id": "user_management_services",
        "subdomains": ["authenticate", "approvals", "reporting"],
        "avg_similarity": 0.82,
        "domain_confidence": 0.85
      }
    ]
  }
}
```

#### **Storage Path Compliance**
```python
def ensure_storage_path_compliance():
    """
    All storage paths MUST follow CodeSight path requirements:
    - Unix-style forward slashes only
    - Relative paths from project root
    - No absolute paths or Windows-style backslashes
    - Follow CODE_STRUCTURE_SPECIFICATION.md exactly
    """
    # ✅ CORRECT paths (per CODE_STRUCTURE_SPECIFICATION.md)
    embeddings_dir = "projects/storm/embeddings"
    faiss_index = "projects/storm/embeddings/faiss_index.bin"
    metadata_file = "projects/storm/embeddings/metadata.json"
    
    # ❌ WRONG paths - violates established structure
    # embeddings_dir = "workflow/temp/step03"
    # embeddings_dir = "workflow/cache/storm/step03"
    # faiss_index = "C:\\project\\embeddings\\faiss_index.bin"
```

---

## 📊 Data Processing Pipeline

### **Phase 1: Code Chunking & Vectorization**

#### **Input Processing**
1. **Load STEP02 Output**
   ```python
   # Load structural data from previous step
   step02_data = load_json("step02_output.json")
   source_inventory = step02_data["source_inventory"]
   ```

2. **Extract Code Chunks**
   ```python
   chunks = []
   for source_location in source_inventory.source_locations:
       for file_inventory_item in source_location:
           # Extract method-level chunks
           method_chunks = extract_method_chunks(file_inventory_item)
           # Extract class-level chunks  
           class_chunks = extract_class_chunks(file_inventory_item)
           chunks.extend(method_chunks + class_chunks)
   ```

3. **Generate Embeddings**
   ```python
   # Vectorize code chunks using code-specific model
   embeddings = []
   for chunk in chunks:
       vector = embedding_model.encode(chunk.content)
       embeddings.append({
           "chunk_id": chunk.id,
           "vector": vector,
           "metadata": chunk.metadata
       })
   ```

#### **FAISS Index Construction**
Note that this is psuedo code and methods or utilities may or may not exists, review the code to determine what is available
```python
# Build FAISS index for similarity search
import faiss
from pathlib import Path

def build_and_persist_faiss_index(embeddings, config):
    """Build FAISS index and persist to project embeddings directory"""
    
    # Create FAISS index
    index = faiss.IndexFlatIP(768)  # Inner product for cosine similarity
    vectors = np.array([emb["vector"] for emb in embeddings])
    index.add(vectors)
    
    # Prepare storage paths (Unix-style, relative to project root)
    # Following CODE_STRUCTURE_SPECIFICATION.md requirements
    project_name = config.get("project_name", "storm")
    embeddings_dir = Path(f"projects/{project_name}/embeddings")
    
    # Ensure directory exists
    embeddings_dir.mkdir(parents=True, exist_ok=True)
    
    # Save index per established file structure
    faiss_index_path = embeddings_dir / "faiss_index.bin"
    faiss.write_index(index, str(faiss_index_path))
    
    # Save metadata per established file structure
    metadata = {
        "embeddings_metadata": {
            "total_chunks": len(embeddings),
            "vector_dimension": 768,
            "index_type": "IndexFlatIP",
            "chunk_mappings": [
                {
                    "chunk_id": emb["chunk_id"],
                    "faiss_index": idx,
                    "metadata": emb["metadata"]
                }
                for idx, emb in enumerate(embeddings)
            ]
        }
    }
    
    metadata_path = embeddings_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Save embedding configuration per established file structure
    embedding_config = {
        "model_info": config.get("model_config", {}),
        "generation_timestamp": time.time(),
        "faiss_config": config.get("faiss_config", {})
    }
    
    config_path = embeddings_dir / "embedding_config.json"
    with open(config_path, 'w') as f:
        json.dump(embedding_config, f, indent=2)
    
    return index, metadata

def load_existing_embeddings(config):
    """Load previously generated embeddings if available and valid"""
    project_name = config.get("project_name", "storm")
    embeddings_dir = Path(f"projects/{project_name}/embeddings")
    faiss_index_path = embeddings_dir / "faiss_index.bin"
    metadata_path = embeddings_dir / "metadata.json"
    
    if faiss_index_path.exists() and metadata_path.exists():
        try:
            index = faiss.read_index(str(faiss_index_path))
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return index, metadata
        except Exception as e:
            logger.warning(f"Failed to load existing embeddings: {e}")
            return None, None
    
    return None, None
```

### **Phase 2: Semantic Clustering & Pattern Recognition**

#### **Component Similarity Analysis**
```python
def enhance_component_classification(component, embeddings, index):
    # Get component's code chunks
    component_chunks = get_component_chunks(component)
    
    # Find similar components via FAISS search
    similar_components = []
    for chunk in component_chunks:
        similarities, indices = index.search(chunk.vector, k=10)
        similar_components.extend(get_components_from_indices(indices))
    
    # Analyze similarity patterns
    type_consensus = analyze_type_consensus(similar_components)
    confidence_boost = calculate_confidence_boost(type_consensus)
    
    # Enhance component classification
    if confidence_boost > 0.05:  # 5% threshold
        component["component_type_confidence"] += confidence_boost
        component["_embedding_metadata"] = {
            "similar_components": [c["name"] for c in similar_components[:5]],
            "confidence_boost": f"+{confidence_boost*100:.1f}%"
        }
```

#### **Domain Clustering**
```python
def enhance_domain_detection(components, embeddings, index):
    # Cluster components by semantic similarity
    component_vectors = get_component_vectors(components, embeddings)
    clusters = perform_semantic_clustering(component_vectors)
    
    # Enhance domain classification based on clusters
    for cluster in clusters:
        domain_consensus = analyze_cluster_domain(cluster)
        for component in cluster.components:
            if domain_consensus.confidence > 0.7:
                component["domain"] = domain_consensus.domain
                component["domain_confidence"] += 0.05  # 5% boost
```

### **Phase 3: Attribute Enhancement**

#### **Enhanced Attributes Mapping**
```python
enhancement_rules = {
    "component_type": {
        "base_confidence": 0.85,
        "enhancement_method": "semantic_clustering",
        "boost_threshold": 0.7,
        "max_boost": 0.05
    },
    "domain": {
        "base_confidence": 0.70,
        "enhancement_method": "vector_similarity_clustering", 
        "boost_threshold": 0.6,
        "max_boost": 0.05
    },
    "files[].role": {
        "base_confidence": 0.75,
        "enhancement_method": "pattern_similarity_matching",
        "boost_threshold": 0.65,
        "max_boost": 0.05
    }
}
```

---

## 🔧 Implementation Requirements

### **Configuration System**

#### **config.yaml Extensions**
```yaml
step03_embeddings:
  enabled: true
  model_config:
    primary_model: "microsoft/codebert-base"
    fallback_model: "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: 32
    max_sequence_length: 512
  
  faiss_config:
    index_type: "IndexFlatIP"
    dimension: 768
    memory_mapping: true
    similarity_threshold: 0.7
    max_results_per_query: 20
  
  storage_config:
    # All paths relative to project root with Unix-style forward slashes
    # Following CODE_STRUCTURE_SPECIFICATION.md requirements
    embeddings_directory: "projects/{project_name}/embeddings"
    cleanup_on_failure: false
    preserve_embeddings: true
  
  chunking_config:
    method_chunk_size: 200
    class_chunk_size: 500
    config_chunk_size: 300
    overlap_tokens: 20
  
  enhancement_config:
    confidence_boost_threshold: 0.05
    minimum_similarity_score: 0.6
    max_similar_components: 10
```

#### **Project-Specific Overrides (config-storm.yaml)**
```yaml
step03_embeddings:
  model_config:
    # Use specialized model for Java enterprise applications
    primary_model: "microsoft/graphcodebert-base"
  
  storage_config:
    # Storm-specific embeddings location per CODE_STRUCTURE_SPECIFICATION.md
    embeddings_directory: "projects/storm/embeddings"
  
  enhancement_config:
    # More conservative boosts for enterprise code
    confidence_boost_threshold: 0.03
    minimum_similarity_score: 0.7
  
  storm_specific:
    architectural_layers: ["asl", "dsl", "gsl", "isl"]
    layer_aware_clustering: true
```

### **Path Handling Standards**
```python
def normalize_paths_for_embeddings():
    """All paths must use Unix-style forward slashes and be relative to project root"""
    # ✅ CORRECT: src/main/java/com/example/Service.java
    # ❌ WRONG: C:\project\src\main\java\com\example\Service.java
    # ❌ WRONG: src\main\java\com\example\Service.java
    pass
```

### **Language & Framework Agnostic Design**
```python
class EmbeddingsProcessor:
    def __init__(self, config):
        """
        Project and language agnostic design principles:
        - No hard-coded Java-specific logic
        - Configurable file patterns and extensions
        - Framework detection through configuration
        """
        self.file_patterns = config.get("file_patterns", {})
        self.framework_hints = config.get("framework_hints", {})
        self.language_config = config.get("language_config", {})
    
    def process_files(self, file_list):
        """Process files based on configuration, not hard-coded assumptions"""
        for file_path in file_list:
            file_type = self.detect_file_type(file_path)  # Configuration-driven
            if file_type in self.supported_types:
                self.process_file(file_path, file_type)
```

---
