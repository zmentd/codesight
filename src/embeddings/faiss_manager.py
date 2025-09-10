"""Step03 FAISS index management for vector storage and retrieval."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import faiss
import numpy as np

from config.config import Config
from domain.embedding_models import (
    EmbeddingChunk,
    EmbeddingMetadata,
    ModelInfo,
    SearchFilters,
    SearchHit,
    SemanticCluster,
    SimilarityResult,
)
from utils.logging.logger_factory import LoggerFactory


class FaissManager:
    """
    Step03-specific FAISS index management for:
    - High-performance vector storage with Step02 domain objects
    - Similarity search operations for embedding chunks
    - Index persistence and loading with project structure compliance
    - Batch operations for large codebases
    - Semantic clustering and pattern detection
    """
    
    def __init__(self) -> None:
        """Initialize FAISS manager with Step03 configuration."""
        self.config = Config.get_instance()
        self.logger = LoggerFactory.get_logger(__name__)
        self.chunk_metadata: Dict[int, EmbeddingChunk] = {}
        
        # Get Step03-specific configuration
        self.step03_config = self.config.steps.step03
        self.faiss_config = self.step03_config.faiss
        
        self.dimension = self.faiss_config.dimension
        self.index_type = self.faiss_config.index_type
        self.similarity_threshold = self.faiss_config.similarity_threshold
        self.max_results = self.faiss_config.max_results_per_query
        # IVF-specific knobs with safe defaults
        self.nlist: int = int(getattr(self.faiss_config, "nlist", 100) or 100)
        self.nprobe: int = int(getattr(self.faiss_config, "nprobe", max(1, min(10, self.nlist))) or max(1, min(10, self.nlist)))
        self.index = self._initialize_index()
    
    def _initialize_index(self) -> Union[faiss.IndexFlat, faiss.IndexIVFFlat]:
        """Initialize FAISS index for Step03.
        """
        index = None
        try:
            metric = str(getattr(self.faiss_config, "metric", "ip") or "ip").lower()
            if self.index_type == "IndexFlatIP" or (self.index_type == "IndexFlat" and metric == "ip"):
                index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "IndexFlatL2" or (self.index_type == "IndexFlat" and metric == "l2"):
                index = faiss.IndexFlatL2(self.dimension)
            elif self.index_type == "IndexIVFFlat":
                # Choose quantizer based on metric
                quantizer = faiss.IndexFlatIP(self.dimension) if metric == "ip" else faiss.IndexFlatL2(self.dimension)
                index = faiss.IndexIVFFlat(quantizer, self.dimension, int(self.nlist), faiss.METRIC_INNER_PRODUCT if metric == "ip" else faiss.METRIC_L2)
                try:
                    index.nprobe = int(self.nprobe)
                except Exception:  # noqa: BLE001  # pylint: disable=W0718
                    pass
            else:
                # Fallback
                index = faiss.IndexFlatIP(self.dimension)
            self.logger.info(
                "Step03 FAISS index initialized: type=%s, dim=%d, metric=%s%s",
                self.index_type,
                self.dimension,
                metric,
                f", nlist={self.nlist}, nprobe={self.nprobe}" if isinstance(index, faiss.IndexIVFFlat) else "",
            )
        except ImportError as e:
            self.logger.error("Failed to initialize FAISS index - FAISS not available: %s", e)
        except (RuntimeError, OSError) as e:
            self.logger.error("Failed to initialize FAISS index: %s", e)
        if index is None:
            raise RuntimeError("Failed to initialize FAISS index")
        return index

    def _use_inner_product(self) -> bool:
        """Whether the index uses inner-product similarity (IP)."""
        metric = str(getattr(self.faiss_config, "metric", "ip") or "ip").lower()
        return metric == "ip"

    def _l2_normalize(self, x: np.ndarray) -> np.ndarray:
        """L2-normalize vectors row-wise, safe for zeros."""
        if x.ndim == 1:
            x = x.reshape(1, -1)
        norms = np.linalg.norm(x, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        result: np.ndarray = x / norms
        return result

    def build_index_from_chunks(self, chunks: List[EmbeddingChunk]) -> bool:
        """
        Build FAISS index from embedding chunks.
        
        Args:
            chunks: List of embedding chunks with vectors
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not chunks:
                self.logger.warning("No chunks provided for index building")
                return False
            
            # Filter chunks with valid embeddings
            valid_chunks = [chunk for chunk in chunks if chunk.embedding is not None]
            
            if not valid_chunks:
                self.logger.warning("No valid embeddings found in chunks")
                return False
            
            # Extract embeddings and store chunk metadata
            embeddings = np.asarray([chunk.embedding for chunk in valid_chunks], dtype=np.float32)
            
            # Preconditions
            if embeddings.ndim != 2 or embeddings.shape[1] != self.dimension:
                self.logger.error(
                    "Embedding tensor shape mismatch, expected (*, %d), got %s",
                    self.dimension,
                    embeddings.shape,
                )
                return False

            if self.index is None:
                self.logger.error("FAISS index not initialized")
                self.logger.debug("Would add embeddings with shape: %s", embeddings.shape)
                return False

            # Normalize for IP-based similarity
            if self._use_inner_product():
                embeddings = self._l2_normalize(embeddings).astype(np.float32, copy=False)

            # Train IVF if required
            if isinstance(self.index, faiss.IndexIVFFlat) and not self.index.is_trained:
                try:
                    if embeddings.shape[0] < int(self.nlist):
                        self.logger.info(
                            "Adjusting nlist from %d to %d due to limited training vectors (%d)",
                            self.nlist,
                            embeddings.shape[0],
                            embeddings.shape[0],
                        )
                        # Rebuild IVF with smaller nlist to allow training
                        quant = faiss.IndexFlatIP(self.dimension)
                        self.index = faiss.IndexIVFFlat(quant, self.dimension, int(embeddings.shape[0]))
                        try:
                            self.index.nprobe = max(1, min(int(self.nprobe), int(embeddings.shape[0])))
                        except Exception:  # noqa: BLE001  # pylint: disable=W0718
                            pass
                    self.logger.info("Training IVF index with %d vectors", embeddings.shape[0])
                    self.index.train(embeddings)  # pyright: ignore[reportCallIssue]
                except Exception as e:  # noqa: BLE001  # pylint: disable=W0718
                    self.logger.error("Failed to train IVF index: %s", e)
                    return False

            # Add vectors to index
            start_id = int(self.index.ntotal)
            self.index.add(embeddings)  # pyright: ignore[reportCallIssue]
            
            # Store chunk metadata by FAISS id
            for i, chunk in enumerate(valid_chunks):
                self.chunk_metadata[start_id + i] = chunk
            
            self.logger.info("Built FAISS index with %d chunks", len(valid_chunks))
            return True
            
        except (ValueError, RuntimeError, MemoryError) as e:
            self.logger.error("Failed to build index from chunks: %s", e)
            return False
    
    def find_similar_chunks(
        self, 
        query_chunk: EmbeddingChunk, 
        k: int = 10
    ) -> List[SimilarityResult]:
        """
        Find chunks similar to query chunk.
        
        Args:
            query_chunk: Query chunk with embedding
            k: Number of results to return
            
        Returns:
            List of SimilarityResult objects
        """
        try:
            if query_chunk.embedding is None:
                self.logger.warning("Query chunk has no embedding")
                return []
            
            if self.index is None:
                self.logger.warning("FAISS index not initialized")
                return []
            
            # Prepare query vector
            q = np.asarray(query_chunk.embedding, dtype=np.float32).reshape(1, -1)
            if q.shape[1] != self.dimension:
                self.logger.error("Query embedding dimension %d != index dimension %d", q.shape[1], self.dimension)
                return []
            if self._use_inner_product():
                q = self._l2_normalize(q).astype(np.float32, copy=False)

            k_eff = max(1, min(int(k), int(self.max_results)))

            # Perform search
            distances, ids = self.index.search(q, k_eff)  # pyright: ignore[reportCallIssue]

            similar_chunks: List[Tuple[str, float]] = []
            for idx, score in zip(ids[0].tolist(), distances[0].tolist()):
                if idx < 0:
                    continue
                chunk = self.chunk_metadata.get(idx)
                if not chunk or chunk.chunk_id == query_chunk.chunk_id:
                    continue
                # For IP similarity, higher is better; apply threshold
                if score >= float(self.similarity_threshold):
                    similar_chunks.append((chunk.chunk_id, float(score)))
            
            # Calculate confidence boost
            confidence_boost = self._calculate_confidence_boost(similar_chunks)
            
            return [SimilarityResult(
                target_chunk_id=query_chunk.chunk_id,
                similar_chunks=similar_chunks,
                confidence_boost=confidence_boost
            )]
            
        except (ValueError, RuntimeError, AttributeError) as e:
            self.logger.error("Failed to find similar chunks: %s", e)
            return []
    
    def find_similar_by_type(
        self, 
        query_chunk: EmbeddingChunk, 
        chunk_type: str, 
        k: int = 10
    ) -> List[SimilarityResult]:
        """
        Find similar chunks of a specific type.
        
        Args:
            query_chunk: Query chunk with embedding
            chunk_type: Type of chunks to search for (method, class, jsp, config)
            k: Number of results to return
            
        Returns:
            List of SimilarityResult objects
        """
        # Get all results first
        all_results = self.find_similar_chunks(query_chunk, k * 3)  # Get more to filter
        
        # Filter by chunk type
        filtered_results = []
        for result in all_results:
            filtered_chunks = []
            for chunk_id, score in result.similar_chunks:
                # Find chunk by ID and check type
                chunk = self._get_chunk_by_id(chunk_id)
                if chunk and chunk.chunk_type == chunk_type:
                    filtered_chunks.append((chunk_id, score))
                    if len(filtered_chunks) >= k:
                        break
            
            if filtered_chunks:
                filtered_results.append(SimilarityResult(
                    target_chunk_id=result.target_chunk_id,
                    similar_chunks=filtered_chunks,
                    confidence_boost=self._calculate_confidence_boost(filtered_chunks)
                ))
        
        return filtered_results
    
    # --- Typed Search API ---

    def search_text(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[SearchFilters] = None,
        threshold: Optional[float] = None,
    ) -> List[SearchHit]:
        """Search by free-text using domain-based filters and return typed hits.
        This uses the configured embedding model to embed the query text.
        """
        try:
            # Lazy import to avoid circulars at module load
            from embeddings.embedding_generator import (
                EmbeddingGenerator,  # pylint: disable=import-outside-toplevel
            )
        except Exception as e:  # noqa: BLE001  # pylint: disable=W0718
            self.logger.error("Embedding generator unavailable: %s", e)
            return []

        eg = EmbeddingGenerator()
        temp_chunk = EmbeddingChunk(
            chunk_id=f"query_{int(np.datetime64('now').astype('int64') % 10**12)}",
            content=query,
            chunk_type="query",
            source_path="<query>",
            start_line=0,
            end_line=0,
        )
        er = eg._generate_embedding(query)  # noqa: SLF001
        if not er.success or er.embedding is None:
            return []
        temp_chunk.embedding = er.embedding

        # Use type filter early if present
        base_results = (
            self.find_similar_by_type(temp_chunk, filters.chunk_type, max(1, top_k * 3))
            if (filters and filters.chunk_type)
            else self.find_similar_chunks(temp_chunk, max(1, top_k * 3))
        )
        return self._to_hits_with_filters(base_results, filters, threshold, top_k)

    def search_chunk(
        self,
        chunk_id: str,
        top_k: int = 10,
        filters: Optional[SearchFilters] = None,
        threshold: Optional[float] = None,
    ) -> List[SearchHit]:
        """Search using an existing chunk as the query and return typed hits."""
        base_chunk = self._get_chunk_by_id(chunk_id)
        if not base_chunk or base_chunk.embedding is None:
            return []
        base_results = (
            self.find_similar_by_type(base_chunk, filters.chunk_type, max(1, top_k * 3))
            if (filters and filters.chunk_type)
            else self.find_similar_chunks(base_chunk, max(1, top_k * 3))
        )
        return self._to_hits_with_filters(base_results, filters, threshold, top_k)

    def _to_hits_with_filters(
        self,
        results: List[SimilarityResult],
        filters: Optional[SearchFilters],
        threshold: Optional[float],
        top_k: int,
    ) -> List[SearchHit]:
        hits: List[SearchHit] = []
        th = float(self.similarity_threshold if threshold is None else threshold)
        for res in results:
            for cid, score in res.similar_chunks:
                if score < th:
                    continue
                ch = self._get_chunk_by_id(cid)
                if not ch:
                    continue
                if filters and not self._apply_filters(ch, filters):
                    continue
                hits.append(SearchHit(chunk=ch, score=float(score)))
                if len(hits) >= top_k:
                    break
            if len(hits) >= top_k:
                break
        return hits

    def _apply_filters(self, ch: EmbeddingChunk, f: SearchFilters) -> bool:
        """AND all provided filters against chunk fields and metadata (case-insensitive exact)."""
        meta = ch.metadata or {}
        
        def norm(x: Optional[str]) -> Optional[str]:
            return x.lower() if isinstance(x, str) else None
        
        if f.chunk_type and norm(ch.chunk_type) != norm(f.chunk_type):
            return False
        if f.subdomain_name and norm(meta.get("subdomain_name")) != norm(f.subdomain_name):
            return False
        if f.source_directory_name and norm(meta.get("source_directory_name")) != norm(f.source_directory_name):
            return False
        if f.file_language and norm(meta.get("file_language")) != norm(f.file_language):
            return False
        if f.file_type and norm(meta.get("file_type")) != norm(f.file_type):
            return False
        if f.file_path and norm(meta.get("file_path")) != norm(f.file_path):
            return False
        if f.source_relative_path and norm(meta.get("source_relative_path")) != norm(f.source_relative_path):
            return False
        # Class / package / method filters sourced from Step02-derived metadata
        pkg_meta = meta.get("package") or meta.get("package_name")
        if f.package_name and norm(pkg_meta) != norm(f.package_name):
            return False
        cls_meta = meta.get("class_name")
        if f.class_name and norm(cls_meta) != norm(f.class_name):
            return False
        mth_meta = meta.get("method_name")
        if f.method_name and norm(mth_meta) != norm(f.method_name):
            return False
        # Reverse-engineering filters
        if f.has_sql is not None:
            has_sql_meta = meta.get("has_sql")
            if isinstance(has_sql_meta, bool):
                if has_sql_meta is not f.has_sql:
                    return False
            else:
                return False
        if f.stored_procedure_name:
            sp_list = meta.get("stored_procedure_names") or []
            if not any(norm(x) == norm(f.stored_procedure_name) for x in sp_list if isinstance(x, str)):
                return False
        if f.entity_mapping_table and norm(meta.get("entity_mapping_table")) != norm(f.entity_mapping_table):
            return False
        return True

    def perform_semantic_clustering(self, n_clusters: int = 10) -> List[SemanticCluster]:
        """
        Perform semantic clustering on indexed chunks.
        
        Args:
            n_clusters: Number of clusters to create
            
        Returns:
            List of SemanticCluster objects
        """
        try:
            clusters: List[SemanticCluster] = []
            
            if not self.chunk_metadata:
                self.logger.warning("No chunks available for clustering")
                return clusters
            
            # Placeholder clustering implementation
            # This would typically use k-means clustering on the embeddings
            chunks_per_cluster = max(1, len(self.chunk_metadata) // n_clusters)
            
            for i in range(n_clusters): 
                start_idx = i * chunks_per_cluster
                end_idx = min(start_idx + chunks_per_cluster, len(self.chunk_metadata))
                
                cluster_chunks = []
                chunk_types = []
                
                for idx in range(start_idx, end_idx):
                    if idx in self.chunk_metadata:
                        chunk = self.chunk_metadata[idx]
                        cluster_chunks.append(chunk.chunk_id)
                        chunk_types.append(chunk.chunk_type)
                
                # Determine dominant type
                dominant_type = max(set(chunk_types), key=chunk_types.count) if chunk_types else None
                
                cluster = SemanticCluster(
                    cluster_id=f"cluster_{i:03d}",
                    chunks=cluster_chunks,
                    avg_similarity=0.7 + np.random.random() * 0.2,  # Placeholder
                    dominant_type=dominant_type,
                    domain_confidence=0.6 + np.random.random() * 0.3  # Placeholder
                )
                
                clusters.append(cluster)
            
            self.logger.info("Generated %d semantic clusters", len(clusters))
            return clusters

        except (ValueError, RuntimeError, MemoryError) as e:
            self.logger.error("Failed to perform semantic clustering: %s", e)
            return []
    
    def compute_cluster_cohesion(self, clusters: List[SemanticCluster]) -> float:
        """Compute simple cohesion metric: average of cluster avg_similarity."""
        if not clusters:
            return 0.0
        vals = [float(getattr(c, "avg_similarity", 0.0) or 0.0) for c in clusters]
        return float(sum(vals) / max(1, len(vals)))

    def save_index_with_metadata(self) -> bool:
        """
        Save FAISS index and metadata following Step03 storage requirements.
        
        Args:
            project_name: Project name for storage path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.index is None:
                self.logger.error("No index to save")
                return False
            
            # Get storage paths following CodeSight path requirements
            storage_paths = self._get_storage_paths()
            
            # Ensure directory exists
            storage_paths["base_dir"].mkdir(parents=True, exist_ok=True)
            
            # Save index
            faiss.write_index(self.index, str(storage_paths["faiss_index"]))
            
            # Create and save metadata
            metadata = self._create_embedding_metadata()
            with open(storage_paths["metadata"], 'w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
            # Save configuration
            config_data = {
                "model_info": metadata.model_info.to_dict(),
                "faiss_config": {
                    "index_type": self.index_type,
                    "dimension": self.dimension,
                    "similarity_threshold": self.similarity_threshold
                },
                "generation_timestamp": np.datetime64('now').item().timestamp()
            }
            
            with open(storage_paths["config"], 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Index and metadata saved to: %s", storage_paths["base_dir"]) 
            return True
            
        except (OSError, IOError, json.JSONDecodeError, RuntimeError) as e:
            self.logger.error("Failed to save index with metadata: %s", e)
            return False
    
    def load_index_with_metadata(self) -> bool:
        """
        Load FAISS index and metadata from Step03 storage.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            storage_paths = self._get_storage_paths()

            index_loaded = False
            if storage_paths["faiss_index"].exists():
                # Load index
                self.index = faiss.read_index(str(storage_paths["faiss_index"]))
                # Basic dimension validation
                if hasattr(self.index, 'd') and self.index.d != self.dimension:
                    self.logger.warning(
                        "Loaded index dimension %d does not match configured %d",
                        self.index.d,
                        self.dimension,
                    )
                index_loaded = True
            else:
                self.logger.warning("Index file not found: %s", storage_paths["faiss_index"]) 
            
            # Load metadata (even if index missing, to restore mappings)
            if storage_paths["metadata"].exists():
                with open(storage_paths["metadata"], 'r', encoding='utf-8') as f:
                    metadata_dict = json.load(f)
                    metadata = EmbeddingMetadata.from_dict(metadata_dict)
                    
                    # Restore chunk metadata from stored mappings
                    self.chunk_metadata = {}
                    for i, chunk_mapping in enumerate(metadata.chunk_mappings):
                        chunk = EmbeddingChunk.from_dict(chunk_mapping)
                        faiss_idx = int(chunk_mapping.get("faiss_index", i))
                        self.chunk_metadata[faiss_idx] = chunk
            else:
                self.logger.warning("Metadata file not found: %s", storage_paths["metadata"]) 
            
            if index_loaded:
                self.logger.info("Index and metadata loaded from: %s", storage_paths["base_dir"]) 
            return index_loaded
            
        except (OSError, IOError, json.JSONDecodeError, KeyError, RuntimeError) as e:
            self.logger.error("Failed to load index with metadata: %s", e)
            return False
    
    def get_index_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the current index.
        
        Returns:
            Dictionary with index statistics
        """
        stats = {
            "total_chunks": len(self.chunk_metadata),
            "dimension": self.dimension,
            "index_type": self.index_type,
            "similarity_threshold": self.similarity_threshold,
            "is_trained": bool(getattr(self.index, "is_trained", True)),
            "memory_usage_mb": len(self.chunk_metadata) * self.dimension * 4 / (1024 * 1024)  # Estimate
        }
        
        # Chunk type distribution
        chunk_types: Dict[str, int] = {}
        for chunk in self.chunk_metadata.values():
            chunk_type = chunk.chunk_type
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        stats["chunk_type_distribution"] = chunk_types
        
        # Source file distribution
        source_files: Dict[str, int] = {}
        for chunk in self.chunk_metadata.values():
            source_file = chunk.source_path
            source_files[source_file] = source_files.get(source_file, 0) + 1
        
        stats["source_file_distribution"] = dict(list(source_files.items())[:10])  # Top 10
        
        # Index size
        try:
            stats["ntotal"] = int(getattr(self.index, "ntotal", len(self.chunk_metadata)))
        except Exception:  # noqa: BLE001  # pylint: disable=W0718
            stats["ntotal"] = len(self.chunk_metadata)
        
        return stats
    
    def _get_storage_paths(self) -> Dict[str, Path]:
        """Get storage paths following CodeSight path requirements."""
        # Unix-style paths, relative to project root
        base_dir = Path(self.config.get_project_embeddings_path())
        return {
            "base_dir": base_dir,
            "faiss_index": base_dir / "faiss_index.bin",
            "metadata": base_dir / "metadata.json",
            "config": base_dir / "embedding_config.json"
        }
    
    def _create_embedding_metadata(self) -> EmbeddingMetadata:
        """Create embedding metadata from current state."""
        chunk_mappings = []
        
        for i, chunk in self.chunk_metadata.items():
            chunk_mapping = chunk.to_dict()
            chunk_mapping["faiss_index"] = i
            chunk_mappings.append(chunk_mapping)
        model_info = ModelInfo(
            primary=self.step03_config.models.primary,
            fallback=self.step03_config.models.fallback,
            dimension=self.dimension,
            device=self.step03_config.models.device,
            batch_size=self.step03_config.models.batch_size,
            max_sequence_length=self.step03_config.models.max_sequence_length
        )
        return EmbeddingMetadata(
            version="1.0",
            model_info=model_info,
            total_chunks=len(self.chunk_metadata),
            chunk_mappings=chunk_mappings,
            generation_timestamp=np.datetime64('now').item().timestamp()
        )
    
    def _get_chunk_by_id(self, chunk_id: str) -> Optional[EmbeddingChunk]:
        """Get chunk by chunk ID."""
        for chunk in self.chunk_metadata.values():
            if chunk.chunk_id == chunk_id:
                return chunk
        return None
    
    def _calculate_confidence_boost(self, similar_chunks: List[Tuple[str, float]]) -> float:
        """Calculate confidence boost based on similarity results."""
        if not similar_chunks:
            return 0.0
        
        # Get configuration thresholds
        enhancement_config = self.step03_config.enhancement
        boost_threshold = enhancement_config.confidence_boost_threshold
        
        # Calculate boost based on number and quality of similar chunks
        num_similar = len(similar_chunks)
        avg_similarity = sum(score for _, score in similar_chunks) / num_similar
        
        # Higher boost for more similar chunks with high similarity scores
        if avg_similarity > 0.8 and num_similar >= 3:
            return boost_threshold
        elif avg_similarity > 0.7 and num_similar >= 2:
            return boost_threshold * 0.7
        elif avg_similarity > 0.6:
            return boost_threshold * 0.5
        
        return 0.0
