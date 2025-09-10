# Step03 Outputs and Typed Search API

Version: 1.0

Purpose: Describe Step03 persisted artifacts, metadata schema, typed search API, and the interactive REPL.

---

## Quickstart

- Build and persist embeddings via Step03 processor.
- Launch REPL:
  - cmd.exe: python scripts\embedding_repl.py --project ct-hr-storm-test
- Example session:
  - :stats
  - :subdomains; :subdomain service; :type method
  - :where package_name=com.storm.user
  - find approvals by manager
  - :clusters 12; :cluster cluster_003

---

## Artifacts and Paths

All Step03 outputs are stored under the project embeddings directory:
- Base directory: projects/{project_name}/embeddings
- Files:
  - faiss_index.bin: FAISS index (IndexFlatIP or IndexIVFFlat)
  - metadata.json: JSON-serialized chunk metadata and mappings
  - embedding_config.json: Model and FAISS configuration snapshot

Notes
- Paths are Unix-style and relative to the repository root.
- Embeddings use cosine similarity via L2-normalized inner product.

---

## metadata.json schema (high level)

Top-level fields:
- version: string (e.g., "1.0")
- model_info:
  - primary, fallback, dimension, device, batch_size, max_sequence_length
- total_chunks: number
- generation_timestamp: number (epoch seconds)
- chunk_mappings: array of EmbeddingChunk dictionaries (see below)

EmbeddingChunk (stored form; JSON-safe):
- chunk_id: string
- chunk_type: string (e.g., class, method, jsp, config)
- source_path: string (relative path to the source file)
- start_line: number
- end_line: number
- faiss_index: number (position in FAISS index)
- content: string (chunk text)
- metadata: object with enriched attributes (examples below)

Common metadata keys (present when available):
- project_name: string
- file_language: string (e.g., java, jsp)
- file_type: string (e.g., source, web, config)
- file_path: string (file path relative to its source location)
- source_relative_path: string (e.g., Storm/src/main/java)
- source_directory_name: string (e.g., java, webapp)
- subdomain_name: string
- preliminary_subdomain_name: string
- subdomain_type: string
- package_name: string
- class_name: string
- method_name: string
- has_sql: boolean
- stored_procedure_names: string[]
- entity_mapping_table: string

All values are JSON-safe (enums, numpy types, etc. are converted).

---

## Programmatic API

Module: src/embeddings/faiss_manager.py

Core methods:
- search_text(query: str, top_k: int = 10, filters: Optional[SearchFilters] = None, threshold: Optional[float] = None) -> List[SearchHit]
- search_chunk(chunk_id: str, top_k: int = 10, filters: Optional[SearchFilters] = None, threshold: Optional[float] = None) -> List[SearchHit]
- get_index_statistics() -> Dict[str, Any]
- perform_semantic_clustering(n_clusters: int = 10) -> List[SemanticCluster]

Types (domain/embedding_models.py):
- SearchFilters: specify exact, case-insensitive filters (ANDed)
  - chunk_type, subdomain_name, source_directory_name, file_language, file_type,
    file_path, source_relative_path, package_name, class_name, method_name,
    has_sql, stored_procedure_name, entity_mapping_table
- SearchHit: { chunk: EmbeddingChunk, score: float }
- SemanticCluster: { cluster_id, chunks[], avg_similarity, dominant_type, domain_confidence }

Examples

Python (pseudo):

from embeddings.faiss_manager import FaissManager
from domain.embedding_models import SearchFilters

fm = FaissManager()
fm.load_index_with_metadata()
filters = SearchFilters(chunk_type="method", subdomain_name="service")
hits = fm.search_text("lookup user approval", top_k=5, filters=filters)
for h in hits:
    print(h.score, h.chunk.chunk_id, h.chunk.metadata.get("class_name"))

clusters = fm.perform_semantic_clustering(n_clusters=10)
print(len(clusters), clusters[0].cluster_id)

---

## Interactive REPL (scripts/embedding_repl.py)

Start the REPL and query the persisted index for your project. Supported commands:
- Free text: any text runs a search over all chunks or current filters
- :topk N — set max results to N
- :type T — filter by chunk type (e.g., method, class, jsp, config)
- :subdomains — list available subdomains from metadata
- :subdomain NAME — set subdomain filter
- :values KEY — list distinct values for a metadata key (e.g., package_name, class_name)
- :where k=v — add a filter (multiple allowed)
- :filters — show active filters
- :stats — show index statistics
- :clusters [N] — compute and list N clusters
- :cluster ID — show details of a cluster from the last :clusters run
- :chunk CHUNK_ID — search similar to a specific chunk
- :show CHUNK_ID — print chunk details
- :help — show help
- :quit — exit

---

## Configuration and tuning

FAISS (config.config -> steps.step03.faiss):
- index_type: IndexFlatIP | IndexIVFFlat
- dimension: int (must match model)
- similarity_threshold: float (e.g., 0.65–0.8)
- max_results_per_query: int
- nlist: int (IVF only; default 100; auto-adjusted if training vectors are fewer)
- nprobe: int (IVF only; default min(10, nlist))

Models (steps.step03.models):
- primary, fallback, device, batch_size, max_sequence_length

Behavior
- Vectors are L2-normalized for inner-product indices to approximate cosine.
- IVF is trained automatically; nlist/nprobe are adjusted when data is small.

---

## End-to-end outline

- Generate embeddings and build index via Step03EmbeddingsProcessor
- Persist index and metadata (faiss_manager.save_index_with_metadata)
- Load for search or REPL (faiss_manager.load_index_with_metadata)
- Use typed API or REPL to query with optional filters and browse clusters

Troubleshooting
- If dimensions mismatch, ensure model dimension equals faiss_config.dimension
- If IVF training fails on small data, the manager reduces nlist automatically
- Ensure Config.initialize(project_name=...) before using the manager
