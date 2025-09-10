"""Step03 embedding generator for domain objects and semantic analysis."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from config.config import Config
from config.exceptions import ConfigurationError
from domain.embedding_models import EmbeddingChunk, SimilarityResult
from domain.java_details import EntityMappingDetails, JavaClass, JavaDetails, JavaMethod
from domain.source_inventory import FileInventoryItem, SourceLocation, Subdomain
from domain.step02_output import Step02AstExtractorOutput
from utils.logging.logger_factory import LoggerFactory


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    success: bool
    embedding: Optional[np.ndarray] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EmbeddingGenerator:
    """
    Step03-specific embedding generator for domain objects:
    - Generate embeddings from Step02 domain objects  
    - Extract meaningful code chunks for semantic analysis
    - Support Java, JSP, and configuration file embedding
    - Enable semantic similarity and clustering analysis
    """
    # Explicit attribute annotations for static checkers
    model: Optional[Any] = None
    enable_disk_cache: bool
    _model_id: str
    _model_id_sanitized: str

    def __init__(self) -> None:
        """Initialize embedding generator with Step03 configuration."""
        self.config = Config.get_instance()
        self.logger = LoggerFactory.get_logger(__name__)
        self.model = None
        self.step03_config = self.config.steps.step03
        # Target embedding dimension used across Step03 (match FAISS index dimension)
        self.embedding_dim = self._get_target_dimension()
        # Common encode knobs from config
        self.device = getattr(self.step03_config.models, 'device', 'cpu') or 'cpu'
        self.batch_size = int(getattr(self.step03_config.models, 'batch_size', 32) or 32)
        self.max_seq_len = int(getattr(self.step03_config.models, 'max_sequence_length', 0) or 0)
        # Simple in-memory cache of embeddings by content hash
        self._cache: Dict[str, np.ndarray] = {}
        # Disk cache controls (enabled by default); namespace by model id and dimension
        self.enable_disk_cache: bool = bool(getattr(self.step03_config, 'enable_disk_cache', True)) or bool(getattr(self.step03_config.models, 'enable_disk_cache', True))
        self._model_id: str = str(getattr(self.step03_config.models, 'primary', 'placeholder'))
        self._model_id_sanitized: str = self._model_id.replace('/', '__').replace('\\', '__')
        self._cache_dir: Path = self._resolve_disk_cache_dir()
        self.logger.info(
            "Initializing Step03 config loaded: %s (embedding_dim=%s, device=%s, batch_size=%s, max_seq_len=%s, disk_cache=%s)",
            self.step03_config,
            self.embedding_dim,
            self.device,
            self.batch_size,
            self.max_seq_len,
            self.enable_disk_cache,
        )
        self._initialize_model()
    
    def _get_target_dimension(self) -> int:
        """Resolve the embedding dimension to use, preferring FAISS config."""
        try:
            faiss_dim = int(getattr(self.step03_config.faiss, 'dimension', 0) or 0)
        except Exception:  # pylint: disable=broad-except
            faiss_dim = 0
        if faiss_dim > 0:
            return faiss_dim
        # Fallback to models config if available, else default 768
        try:
            model_dim = int(getattr(self.step03_config.models, 'dimension', 0) or 0)
        except Exception:  # pylint: disable=broad-except
            model_dim = 0
        return model_dim if model_dim > 0 else 768

    def _resolve_disk_cache_dir(self) -> Path:
        """Resolve and create the on-disk embedding cache directory."""
        # Base embeddings directory from Config if available
        try:
            base = Path(self.config.get_project_embeddings_path())
        except Exception:  # pylint: disable=broad-except
            # Fallback: try constructing from known structure, else cwd/embeddings
            try:
                projects_root = Path(getattr(self.config, 'projects_root', 'projects'))
                project_name = str(getattr(self.config, 'project_name', 'default'))
                base = projects_root / project_name / 'embeddings'
            except Exception:  # pylint: disable=broad-except
                base = Path.cwd() / 'embeddings'
        # Namespaced by dimension and model to avoid collisions across configs
        cache_dir = base / 'cache' / f'dim{self.embedding_dim}' / self._model_id_sanitized
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:  # pylint: disable=broad-except
            pass
        return cache_dir

    def _disk_cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.npy"

    def _disk_cache_get(self, key: str) -> Optional[np.ndarray]:
        """Load an embedding from disk cache if present and enabled."""
        if not self.enable_disk_cache:
            return None
        path = self._disk_cache_path(key)
        if not path.exists():
            return None
        try:
            arr = np.load(path)
            arr = np.asarray(arr, dtype=np.float32)
            if arr.ndim != 1:
                arr = arr.reshape(-1)
            return self._ensure_dimension(arr)
        except Exception:  # pylint: disable=broad-except
            return None

    def _disk_cache_set(self, key: str, vec: np.ndarray) -> None:
        """Persist an embedding to disk cache (only for real model outputs)."""
        if not self.enable_disk_cache or self.model is None:
            return
        path = self._disk_cache_path(key)
        try:
            np.save(path, self._ensure_dimension(vec))
        except Exception:  # pylint: disable=broad-except
            pass

    def _initialize_model(self) -> None:
        """Initialize the embedding model with Step03 configuration."""
        try:
            models_config = self.step03_config.models
            primary_model = models_config.primary
            fallback_model = getattr(models_config, 'fallback', None)
            self.logger.info("Initializing Step03 embedding model: %s", primary_model)

            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                self.logger.warning(
                    "sentence-transformers not installed; using placeholder embeddings. Error: %s",
                    e,
                )
                self.model = None
                return

            # Try primary model first
            try:
                # Newer versions accept device kwarg; if not, we'll move the model after init
                self.model = SentenceTransformer(primary_model, device=self.device)
            except TypeError:
                self.model = SentenceTransformer(primary_model)
                try:
                    import torch

                    # Some versions may lack .to attribute; ignore if unsupported
                    if hasattr(self.model, "to"):
                        self.model.to(torch.device(self.device))
                except Exception:  # pylint: disable=broad-except
                    pass
            except Exception as e:  # pylint: disable=broad-except
                self.logger.warning("Failed to load primary model '%s': %s", primary_model, e)
                if not fallback_model:
                    self.model = None
                else:
                    self.logger.info("Attempting fallback model: %s", fallback_model)
                    try:
                        self.model = SentenceTransformer(fallback_model, device=self.device)
                    except Exception as ee:  # pylint: disable=broad-except
                        self.logger.error("Failed to load fallback model '%s': %s", fallback_model, ee)
                        self.model = None

            # Configure max sequence length for truncation if supported
            if self.model is not None and self.max_seq_len > 0:
                try:
                    # sentence-transformers uses tokens, not chars; guard attribute
                    if hasattr(self.model, "max_seq_length"):
                        self.model.max_seq_length = self.max_seq_len
                except Exception:  # pylint: disable=broad-except
                    pass

            if self.model is not None:
                self.logger.info("Step03 embedding model initialized: %s", primary_model)
            else:
                self.logger.warning("Embedding model not available; placeholder embeddings will be used.")
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to initialize embedding model: %s", e)
            self.model = None
    
    def generate_embeddings_from_step02(self, step02_output: Step02AstExtractorOutput) -> List[EmbeddingChunk]:
        """
        Generate embeddings from Step02 domain objects.
        
        Args:
            step02_output: Complete Step02 output with domain objects
            
        Returns:
            List of EmbeddingChunk objects with generated embeddings
        """
        chunks: List[EmbeddingChunk] = []
        
        try:
            # Extract chunks from all source locations
            for source_location in step02_output.source_inventory.source_locations:
                for subdomain in source_location.subdomains:
                    for file_item in subdomain.file_inventory:
                        file_chunks = self._extract_chunks_from_file(file_item, subdomain=subdomain, source_location=source_location)
                        chunks.extend(file_chunks)
            
            # Batch-generate embeddings for all collected chunks (handles caching and dimension alignment)
            enriched = self.batch_generate_embeddings(chunks)
            self.logger.info("Generated %d embedding chunks from Step02 output", len(enriched))
            return enriched
            
        except (AttributeError, ValueError, RuntimeError) as e:
            self.logger.error("Failed to generate embeddings from Step02 output: %s", e)
            return []
    
    def _extract_chunks_from_file(self, file_item: FileInventoryItem, subdomain: Subdomain, source_location: SourceLocation) -> List[EmbeddingChunk]:
        """Extract embedding chunks from a file inventory item, with context for metadata enrichment."""
        chunks: List[EmbeddingChunk] = []
        
        # Check file type and details
        if file_item.details and isinstance(file_item.details, JavaDetails):
            chunks.extend(self._extract_java_chunks(file_item.details, file_item.path))
        
        # Check if file has JSP details  
        elif file_item.details and str(getattr(file_item, 'language', '')).lower() == 'jsp':
            chunks.extend(self._extract_jsp_chunks(file_item.details, file_item.path))
        
        # Check if file has configuration details
        elif file_item.details and str(getattr(file_item, 'type', '')).lower() in ['config', 'configuration']:
            chunks.extend(self._extract_config_chunks(file_item.details, file_item.path))
        
        # Enrich chunk metadata with file/subdomain/source context
        for ch in chunks:
            self._augment_chunk_metadata(ch, file_item, subdomain, source_location)
        
        return chunks

    def _augment_chunk_metadata(self, chunk: EmbeddingChunk, file_item: FileInventoryItem, subdomain: Subdomain, source_location: SourceLocation) -> None:
        """Add useful file, subdomain, and source location attributes into chunk.metadata using domain attributes."""
        meta: Dict[str, Any] = dict(chunk.metadata or {})
        sap = getattr(subdomain, 'architectural_pattern', None)

        # File attributes (from FileInventoryItem domain object)
        meta.update({
            "file_path": file_item.path,
            "file_language": file_item.language,
            "file_type": file_item.type,
        })
        # Include hash if present on the domain type
        try:
            meta["file_hash"] = file_item.hash  # type: ignore[attr-defined]
        except AttributeError:
            pass

        # Subdomain attributes (from Subdomain domain object)
        meta.update({
            "subdomain_name": subdomain.preliminary_subdomain_name or subdomain.name,
            "subdomain_type": subdomain.type,
            "subdomain_path": subdomain.path,
        })
        if sap is not None and hasattr(sap, 'pattern'):
            architectural_pattern = getattr(sap, 'pattern', None)
            meta.update({"architectural_pattern": architectural_pattern})

        # Source location attributes (from SourceLocation domain object)
        meta.update({
            "source_relative_path": source_location.relative_path,
            "source_directory_name": source_location.directory_name,
            "source_language_type": source_location.language_type,
            "source_primary_language": source_location.primary_language,
        })

        # Project name from Config (domain-backed config)
        meta.setdefault("project_name", self.config.project_name)

        chunk.metadata = meta

    def _extract_java_chunks(self, java_details: JavaDetails, file_path: str) -> List[EmbeddingChunk]:
        """Extract embedding chunks from Java classes."""
        chunks: List[EmbeddingChunk] = []
        
        for java_class in java_details.classes:
            # Class-level chunk
            class_chunk = self._create_class_chunk(java_class, file_path)
            if class_chunk:
                chunks.append(class_chunk)
            
            # Method-level chunks
            for method in java_class.methods:
                method_chunk = self._create_method_chunk(method, java_class.class_name, file_path)
                if method_chunk:
                    chunks.append(method_chunk)
        
        return chunks
    
    def _extract_jsp_chunks(self, jsp_details: Any, file_path: str) -> List[EmbeddingChunk]:
        """Extract embedding chunks from JSP files.""" 
        chunks: List[EmbeddingChunk] = []
        
        # Create chunk for JSP content
        jsp_content = self._jsp_to_text(jsp_details)
        if jsp_content:
            chunk_id = f"jsp_{Path(file_path).stem}_{len(chunks)}"
            
            chunk = EmbeddingChunk(
                chunk_id=chunk_id,
                content=jsp_content,
                chunk_type="jsp",
                source_path=file_path,
                start_line=1,
                end_line=len(jsp_content.split('\n')),
                metadata={
                    "forms_count": len(getattr(jsp_details, 'forms', [])),
                    "elements_count": len(getattr(jsp_details, 'elements', [])),
                    "has_embedded_java": bool(getattr(jsp_details, 'embedded_java_blocks', []))
                }
            )
            
            # Generate embedding
            embedding_result = self._generate_embedding(jsp_content)
            if embedding_result.success:
                chunk.embedding = embedding_result.embedding
                chunks.append(chunk)
        
        return chunks
    
    def _extract_config_chunks(self, config_details: Any, file_path: str) -> List[EmbeddingChunk]:
        """Extract embedding chunks from configuration files."""
        chunks: List[EmbeddingChunk] = []
        
        # Basic configuration chunk
        config_content = f"Configuration file: {file_path}"
        chunk_id = f"config_{Path(file_path).stem}_{len(chunks)}"
        
        chunk = EmbeddingChunk(
            chunk_id=chunk_id,
            content=config_content,
            chunk_type="config",
            source_path=file_path,
            start_line=1,
            end_line=1,
            metadata={"file_type": "configuration"}
        )
        
        # Generate embedding
        embedding_result = self._generate_embedding(config_content)
        if embedding_result.success:
            chunk.embedding = embedding_result.embedding
            chunks.append(chunk)
        
        return chunks
    
    def _create_class_chunk(self, java_class: JavaClass, file_path: str) -> Optional[EmbeddingChunk]:
        """Create an embedding chunk for a Java class."""
        class_content = self._class_to_text(java_class)
        entity_mapping_table: Optional[str] = None
        emd = getattr(java_class, 'entity_mapping', None)
        if emd is not None and hasattr(emd, 'table_name'):
            entity_mapping_table = getattr(emd, 'table_name', None)

        if not class_content:
            return None
        
        chunk_id = f"class_{java_class.class_name}_{getattr(java_class, 'line_number', 0) or 0}"
        
        chunk = EmbeddingChunk(
            chunk_id=chunk_id,
            content=class_content,
            chunk_type="class",
            source_path=file_path,
            start_line=getattr(java_class, 'line_number', 1) or 1,
            end_line=(getattr(java_class, 'line_number', 1) or 1) + (getattr(java_class, 'line_count', 50) or 50),
            metadata={
                "class_name": java_class.class_name,
                "package": java_class.package_name,
                "methods_count": len(java_class.methods),
                "fields_count": len(java_class.fields),
                "annotations": [ann.name for ann in java_class.annotations],
                "entity_mapping_table": entity_mapping_table,
            },
        )
        
        # Generate embedding
        embedding_result = self._generate_embedding(class_content)
        if embedding_result.success:
            chunk.embedding = embedding_result.embedding
            return chunk
        
        return None
    
    def _create_method_chunk(self, method: JavaMethod, class_name: str, file_path: str) -> Optional[EmbeddingChunk]:
        """Create an embedding chunk for a Java method."""
        method_content = self._method_to_text(method, class_name)
        if not method_content:
            return None

        has_sql = len(method.sql_statements) > 0
        stored_procedure_names = [sp.procedure_name for sp in method.sql_stored_procedures]
        chunk_id = f"method_{class_name}_{method.name}_{hash(method_content) % 10000}"
        
        # Estimate line numbers (basic implementation)
        start_line = 1  # Would need actual AST line info
        end_line = start_line + (getattr(method, 'line_count', 10) or 10)
        
        chunk = EmbeddingChunk(
            chunk_id=chunk_id,
            content=method_content,
            chunk_type="method",
            source_path=file_path,
            start_line=start_line,
            end_line=end_line,
            metadata={
                "method_name": method.name,
                "class_name": class_name,
                "visibility": method.visibility,
                "return_type": method.return_type,
                "parameters_count": len(method.parameters),
                "annotations": [ann.name for ann in method.annotations],
                "complexity_score": getattr(method, 'complexity_score', None),
                "has_sql": has_sql,
                "stored_procedure_names": stored_procedure_names,
            },
        )
        
        # Generate embedding
        embedding_result = self._generate_embedding(method_content)
        if embedding_result.success:
            chunk.embedding = embedding_result.embedding
            return chunk
        
        return None
    
    def _class_to_text(self, java_class: Any) -> str:
        """Convert Java class to text representation for embedding."""
        text_parts = []
        
        # Add class information
        text_parts.append(f"class {java_class.class_name}")
        
        if java_class.package_name:
            text_parts.append(f"package {java_class.package_name}")
        
        # Add annotations
        for annotation in java_class.annotations:
            text_parts.append(f"annotation {annotation.name}")
        
        # Add inheritance info
        if getattr(java_class, 'superclass', None):
            text_parts.append(f"extends {java_class.superclass}")
        
        for interface in getattr(java_class, 'interfaces', []):
            text_parts.append(f"implements {interface}")
        
        # Add method signatures
        for method in java_class.methods[:5]:  # Limit to first 5 methods
            text_parts.append(f"method {method.visibility} {method.return_type or 'void'} {method.name}")
        
        # Add field information
        for field in java_class.fields[:5]:  # Limit to first 5 fields
            text_parts.append(f"field {field.visibility} {field.type} {field.name}")
        
        return " ".join(text_parts)
    
    def _method_to_text(self, method: Any, class_name: str) -> str:
        """Convert Java method to text representation for embedding."""
        text_parts = []
        
        # Add method signature
        text_parts.append(f"method {method.name} in class {class_name}")
        text_parts.append(f"visibility {method.visibility}")
        
        if method.return_type:
            text_parts.append(f"returns {method.return_type}")
        
        # Add parameters
        for param in method.parameters:
            text_parts.append(f"parameter {param.type} {param.name}")
        
        # Add annotations
        for annotation in method.annotations:
            text_parts.append(f"annotation {annotation.name}")
        
        # Add modifiers
        for modifier in method.modifiers:
            text_parts.append(f"modifier {modifier}")
        
        return " ".join(text_parts)
    
    def _jsp_to_text(self, jsp_details: Any) -> str:
        """Convert JSP details to text representation for embedding."""
        text_parts = []
        
        text_parts.append("jsp page")
        
        # Add form information
        for form in getattr(jsp_details, 'forms', []):
            text_parts.append(f"form {form.name}")
            for field in form.fields:
                text_parts.append(f"field {field.type} {field.name}")
            for button in form.buttons:
                text_parts.append(f"button {button.type} {button.name}")
        
        # Add elements
        for element in getattr(jsp_details, 'elements', []):
            text_parts.append(f"element {getattr(element, 'tag_name', 'unknown')}")
        
        # Add embedded Java info
        if getattr(jsp_details, 'embedded_java_blocks', []):
            text_parts.append("embedded java blocks")
        
        return " ".join(text_parts)
    
    def _text_hash(self, text: str) -> str:
        """Compute a stable hash for caching based on text content."""
        return hashlib.sha1(text.encode('utf-8')).hexdigest()

    def _deterministic_placeholder(self, key: str) -> np.ndarray:
        """Generate a deterministic placeholder embedding from a cache key hex string."""
        # Use first 16 hex chars as seed for reproducibility, but bound to 32-bit
        try:
            seed = int(key[:16], 16) & 0xFFFFFFFF
        except Exception:  # pylint: disable=broad-except
            seed = 0
        rng = np.random.default_rng(seed)
        vec = rng.random(self.embedding_dim)
        return vec.astype(np.float32)

    def _encode_texts(self, texts: List[str]) -> np.ndarray:
        """Encode a list of texts with the model, returning float32 numpy array."""
        if not self.model:
            # Deterministic placeholder batch output
            arr = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
            for i, t in enumerate(texts):
                key = self._text_hash(t)
                arr[i] = self._deterministic_placeholder(key)
            return arr
        try:
            # sentence-transformers encode API
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=False,
            )
            # Ensure float32 and correct dim
            arr = np.asarray(embeddings, dtype=np.float32)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            if arr.shape[1] != self.embedding_dim:
                # Align by truncate/pad
                aligned = np.zeros((arr.shape[0], self.embedding_dim), dtype=np.float32)
                d = min(arr.shape[1], self.embedding_dim)
                aligned[:, :d] = arr[:, :d]
                return aligned
            return arr
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Model encode failed; falling back to placeholder. Error: %s", e)
            arr = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
            for i, t in enumerate(texts):
                key = self._text_hash(t)
                arr[i] = self._deterministic_placeholder(key)
            return arr

    def find_similar_chunks(
        self, 
        target_chunk: EmbeddingChunk, 
        all_chunks: List[EmbeddingChunk], 
        threshold: float = 0.7
    ) -> List[SimilarityResult]:
        """
        Find chunks similar to target chunk using cosine similarity.
        
        Args:
            target_chunk: Target chunk for similarity search
            all_chunks: List of chunks to search within
            threshold: Similarity threshold
            
        Returns:
            List of SimilarityResult objects
        """
        if target_chunk.embedding is None:
            return []
        
        similar_chunks: List[Tuple[str, float]] = []
        
        for chunk in all_chunks:
            if chunk.chunk_id == target_chunk.chunk_id or chunk.embedding is None:
                continue
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(target_chunk.embedding, chunk.embedding)
            
            if similarity >= threshold:
                similar_chunks.append((chunk.chunk_id, similarity))
        
        # Sort by similarity score (descending)
        similar_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate confidence boost
        confidence_boost = self._calculate_confidence_boost(similar_chunks)
        
        return [SimilarityResult(
            target_chunk_id=target_chunk.chunk_id,
            similar_chunks=similar_chunks,
            confidence_boost=confidence_boost
        )]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)
        
        if norm_vec1 == 0 or norm_vec2 == 0:
            return 0.0
        
        return float(dot_product / (norm_vec1 * norm_vec2))
    
    def _calculate_confidence_boost(self, similar_chunks: List[Tuple[str, float]]) -> float:
        """Calculate confidence boost based on similarity results."""
        if not similar_chunks:
            return 0.0
        
        # Get configuration thresholds
        enhancement_config = self.step03_config.enhancement
        boost_threshold = float(enhancement_config.confidence_boost_threshold or 0.05)
        
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
    
    def batch_generate_embeddings(self, chunks: List[EmbeddingChunk]) -> List[EmbeddingChunk]:
        """
        Generate embeddings for multiple chunks in batch.
        
        Args:
            chunks: List of chunks to generate embeddings for
            
        Returns:
            List of chunks with embeddings generated
        """
        results: List[EmbeddingChunk] = []
        if not chunks:
            return results

        # Prepare texts and indices for items missing embeddings or not cached
        texts: List[str] = []
        idxs: List[int] = []
        keys: List[str] = []
        for i, chunk in enumerate(chunks):
            key = self._text_hash(chunk.content)
            cached = self._cache.get(key)
            if cached is not None:
                chunk.embedding = cached
                results.append(chunk)
            else:
                # Try disk cache next
                disk_vec = self._disk_cache_get(key)
                if disk_vec is not None:
                    self._cache[key] = disk_vec
                    chunk.embedding = disk_vec
                    results.append(chunk)
                else:
                    texts.append(chunk.content)
                    keys.append(key)
                    idxs.append(i)

        # Encode remaining in mini-batches using model if available
        for start in range(0, len(texts), self.batch_size):
            batch_texts = texts[start:start + self.batch_size]
            batch_keys = keys[start:start + self.batch_size]
            arr = self._encode_texts(batch_texts)
            # Assign back
            for j, emb in enumerate(arr):
                k = batch_keys[j]
                emb_vec = self._ensure_dimension(np.asarray(emb, dtype=np.float32))
                self._cache[k] = emb_vec
                # Persist to disk cache only for real model outputs
                self._disk_cache_set(k, emb_vec)
                chunk_index = idxs[start + j]
                chunks[chunk_index].embedding = emb_vec
                results.append(chunks[chunk_index])

        return results

    def _ensure_dimension(self, vec: np.ndarray) -> np.ndarray:
        """Ensure vector matches configured embedding_dim by truncation/padding."""
        if vec.ndim != 1:
            vec = vec.reshape(-1)
        d = vec.shape[0]
        if d == self.embedding_dim:
            return vec.astype(np.float32, copy=False)
        if d > self.embedding_dim:
            self.logger.warning("Embedding dim %d > target %d; truncating", d, self.embedding_dim)
            return vec[: self.embedding_dim].astype(np.float32, copy=False)
        # Pad with zeros if smaller
        self.logger.warning("Embedding dim %d < target %d; padding with zeros", d, self.embedding_dim)
        out = np.zeros((self.embedding_dim,), dtype=np.float32)
        out[:d] = vec.astype(np.float32, copy=False)
        return out

    def _generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding for text; uses model when available, otherwise placeholder.
        Includes simple caching by content hash.
        """
        try:
            key = self._text_hash(text)
            cached = self._cache.get(key)
            if cached is not None:
                return EmbeddingResult(success=True, embedding=cached, metadata={"cache": True, "dimension": self.embedding_dim})

            # Try disk cache before computing
            disk_vec = self._disk_cache_get(key)
            if disk_vec is not None:
                self._cache[key] = disk_vec
                return EmbeddingResult(success=True, embedding=disk_vec, metadata={"cache": "disk", "dimension": self.embedding_dim})

            if not self.model:
                # Deterministic placeholder implementation (do not persist placeholders to disk)
                embedding = self._deterministic_placeholder(key)
                self._cache[key] = embedding
                return EmbeddingResult(
                    success=True,
                    embedding=embedding,
                    metadata={"model": "placeholder", "text_length": len(text), "dimension": self.embedding_dim}
                )

            # Real model path
            vecs = self._encode_texts([text])
            embedding = self._ensure_dimension(np.asarray(vecs[0], dtype=np.float32))
            self._cache[key] = embedding
            # Persist real embeddings to disk cache
            self._disk_cache_set(key, embedding)
            return EmbeddingResult(
                success=True,
                embedding=embedding,
                metadata={"model": "sentence-transformers", "text_length": len(text), "dimension": int(embedding.shape[0])}
            )
        except (RuntimeError, AttributeError, ImportError) as e:
            self.logger.error("Failed to generate embedding: %s", e)
            return EmbeddingResult(success=False, error_message=str(e))
    
    def generate_and_index_from_step02(self, step02_output: Step02AstExtractorOutput, persist: bool = True) -> Tuple[List[EmbeddingChunk], bool]:
        """Convenience: generate embeddings from Step02 output, build FAISS index, and optionally persist.
        Returns the enriched chunks and whether the index was built successfully.
        """
        chunks = self.generate_embeddings_from_step02(step02_output)
        try:
            # Import here to avoid circular imports at module load time
            from embeddings.faiss_manager import (
                FaissManager,  # pylint: disable=import-outside-toplevel
            )
        except Exception:  # pylint: disable=broad-except
            self.logger.error("FAISS manager not available; skipping index build")
            return chunks, False

        fm = FaissManager()
        built = fm.build_index_from_chunks(chunks)
        if built and persist:
            _ = fm.save_index_with_metadata()
        return chunks, built
