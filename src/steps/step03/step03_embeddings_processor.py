"""
Step03 Embeddings Processor for CodeSight.

This module implements the Step03 processing pipeline for generating and managing
code embeddings and semantic analysis. It integrates with Step02 domain objects
to create vector representations of code components and enable similarity search.

Key Responsibilities:
- Process Step02 AST extraction results
- Generate embeddings for code components (classes, methods, JSPs, configs)
- Build and manage FAISS vector indices
- Perform semantic clustering and analysis
- Output structured embedding results following CodeSight patterns

Path Requirements:
- Uses Unix-style forward slashes for all paths
- Relative paths from project root
- Output follows projects/{project_name}/embeddings structure

Type Safety:
- Full type annotations using domain objects
- Type-safe integration with Step02 outputs
- Proper error handling and validation
"""

import json
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Union

from config.config import Config
from config.exceptions import ConfigurationError
from core.base_node import BaseNode, ValidationResult
from domain.source_inventory import SourceInventory
from utils.logging.logger_factory import LoggerFactory


class ProcessingError(Exception):
    """Processing error for Step03."""


from domain.embedding_models import (
    EmbeddingChunk,
    EmbeddingMetadata,
    EnhancementResult,
    ModelInfo,
    SemanticCluster,
    SimilarityResult,
)
from domain.step02_output import Step02AstExtractorOutput
from embeddings.embedding_generator import EmbeddingGenerator
from embeddings.faiss_manager import FaissManager


class Step03EmbeddingsProcessor(BaseNode):
    """
    Step03 processor for comprehensive code embeddings and semantic analysis.
    
    Follows CodeSight BaseNode pattern for consistent pipeline integration
    with configuration-driven operation and type-safe domain objects.
    """

    def __init__(self, node_id: str = "step03_embeddings_processor") -> None:
        """Initialize Step03 processor with dependencies."""
        super().__init__(node_id=node_id)
        
        try:
            self.config = Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"Failed to initialize Step03 processor: {e}") from e

        self.logger = LoggerFactory.get_logger("steps.step03")

        # Initialize Step03 components
        self.embedding_generator = EmbeddingGenerator()
        self.faiss_manager = FaissManager()
        
        # Get Step03-specific configuration
        self.step03_config = self.config.steps.step03
        self.enhancement_config = self.step03_config.enhancement
        
        # Processing thresholds and parameters
        self.min_chunks_for_clustering = self.enhancement_config.min_chunks_for_clustering
        self.confidence_boost_threshold = self.enhancement_config.confidence_boost_threshold
        
        self.logger.info("Step03 embeddings processor initialized")
    
    def _prep_implementation(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare Step03 implementation - required by BaseNode."""
        self.logger.info("Preparing Step 03 embeddings processing")

        # Get Step 02 output from shared state (stored by BaseNode using node_id as key)
        step02_result = shared.get("step02_ast_extractor")
        if not step02_result:
            raise ValueError("Step 02 output not found in shared state")

        # Extract the actual output data from the step02 result
        step02_data = step02_result.get("output_data")
        if not step02_data:
            raise ValueError("Step 02 output_data not found in step02 result")

        # Convert to domain object if needed
        if isinstance(step02_data, Step02AstExtractorOutput):
            step02_output = step02_data
        elif isinstance(step02_data, dict):
            step02_output = Step02AstExtractorOutput.from_dict(step02_data)
        else:
            raise ValueError("Invalid Step 02 output data type: expected dict or Step02AstExtractorOutput")
        
        return {
            "step02_output": step02_output,
            "project_path": shared.get("project_path"),
            "project_name": shared.get("project_name")
        }
    
    def _exec_implementation(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Step02 AST extraction results to generate embeddings and semantic analysis.
        
        Args:
            prep_result: Dict containing Step02AstExtractorOutput and project info
        
        Returns:
            Dict with "output_data" wrapper, processing time, and statistics
            suitable for PocketFlow downstream nodes
        
        Raises:
            ProcessingError: If embeddings generation or analysis fails
        """
        try:
            project_name = prep_result["project_name"]
            step02_output: Step02AstExtractorOutput = prep_result["step02_output"]

            self.logger.info("Starting Step03 embeddings processing for project: %s", project_name)
            
            start_time = time.time()
            processing_stats: Dict[str, Union[int, float]] = {
                "total_files_processed": 0,
                "total_chunks_generated": 0,
                "total_embeddings_created": 0,
                "semantic_clusters_found": 0,
                "similarity_enhancements": 0,
                # New: coverage and cohesion placeholders
                "embedding_coverage_pct": 0.0,
                "cluster_cohesion": 0.0,
            }

            # Progress context with phases
            total_files: int = 0
            try:
                total_files = sum(
                    len(subdomain.file_inventory)
                    for src in step02_output.source_inventory.source_locations
                    for subdomain in src.subdomains
                )
            except Exception:  # pylint: disable=broad-except
                total_files = 0

            with self.create_progress_context(total_files) as progress:
                # Phase: extract + embed
                progress.start_phase("extract", "🔎 Extracting and embedding chunks", total_files or 1)
                all_chunks = self._generate_embeddings_from_step02(step02_output, processing_stats, progress)
                if not all_chunks:
                    raise ProcessingError("No embedding chunks generated from Step02 output")

                # Phase: index
                progress.start_phase("index", "📦 Building FAISS index", 1)
                # Validate dims/dtype before indexing
                self._validate_dimension_compatibility()
                if not self.faiss_manager.build_index_from_chunks(all_chunks):
                    raise ProcessingError("Failed to build FAISS index from embedding chunks")
                progress.update(1, current_item="faiss_index")

                # Phase: cluster
                n_clusters = min(10, max(3, len(all_chunks) // 20)) if len(all_chunks) >= self.min_chunks_for_clustering else 0
                # Enforce min_cluster_size by bounding n_clusters
                if n_clusters and len(all_chunks) // max(1, n_clusters) < int(self.enhancement_config.min_cluster_size or 1):
                    n_clusters = max(0, len(all_chunks) // max(1, int(self.enhancement_config.min_cluster_size)))
                progress.start_phase("cluster", "🧩 Performing semantic clustering", max(n_clusters, 1))
                semantic_clusters = self._perform_semantic_clustering(all_chunks, processing_stats)
                if n_clusters > 0:
                    progress.update(n_clusters, current_item=f"clusters:{len(semantic_clusters)}")
                else:
                    progress.update(1, current_item="skipped")

                # Compute cohesion using FaissManager helper
                processing_stats["cluster_cohesion"] = float(self.faiss_manager.compute_cluster_cohesion(semantic_clusters)) if semantic_clusters is not None else 0.0

                # Phase: enhance
                sample_size = min(50, len(all_chunks))
                progress.start_phase("enhance", "✨ Generating similarity enhancements", max(sample_size, 1))
                enhancement_results = self._generate_similarity_enhancements(all_chunks, processing_stats, progress)
                # Ensure phase completes even if nothing to enhance
                if sample_size == 0:
                    progress.update(1, current_item="skipped")

                # Coverage metric after embedding generation
                processing_stats["embedding_coverage_pct"] = (
                    float(processing_stats["total_embeddings_created"]) / float(max(1, int(processing_stats["total_chunks_generated"])))
                )

                # Phase: persist
                progress.start_phase("persist", "💾 Saving embeddings index and metadata", 1)
                if not self.faiss_manager.save_index_with_metadata():
                    self.logger.warning("Failed to save FAISS index, continuing with in-memory results")
                progress.update(1, current_item="saved")

            # Gates: enforce after processing
            self._enforce_quality_gates(processing_stats)

            # Warnings: zero enhancements or skewed chunk distribution
            idx_stats = self.faiss_manager.get_index_statistics()
            chunk_dist = (idx_stats or {}).get("chunk_type_distribution", {})
            if int(processing_stats.get("similarity_enhancements", 0)) == 0:
                self.logger.warning("No similarity enhancements generated")
            # Warn on extreme skew: one type > 95%% of chunks
            total_chunks = max(1, sum(int(v) for v in chunk_dist.values()))
            for t, cnt in chunk_dist.items():
                if (int(cnt) / float(total_chunks)) > 0.95:
                    self.logger.warning("Chunk type '%s' dominates (%.1f%%) — review chunking settings", t, 100.0 * int(cnt) / float(total_chunks))

            # Create comprehensive output
            processing_time = time.time() - start_time
            processing_stats["processing_time_seconds"] = float(processing_time)
            
            step03_output = self._create_step03_output(
                all_chunks,
                semantic_clusters,
                enhancement_results,
                project_name,
                processing_stats
            )
            
            self.logger.info(
                "Step03 processing completed in %.2f seconds: %d chunks, %d clusters, %d enhancements",
                processing_time,
                len(all_chunks),
                len(semantic_clusters),
                len(enhancement_results)
            )
            
            # PocketFlow-compliant wrapper
            return {
                "output_data": step03_output,
                "processing_time": processing_time,
                "processing_statistics": processing_stats
            }
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Step03 processing failed: %s", e, exc_info=True)
            raise ProcessingError(f"Step03 embeddings processing failed: {e}") from e

    def _validate_dimension_compatibility(self) -> None:
        """Validate embedding model dimension vs FAISS index dimension/metric."""
        model_dim = int(getattr(self.step03_config.models, "dimension", 0) or 0)
        faiss_dim = int(getattr(self.step03_config.faiss, "dimension", 0) or 0)
        if faiss_dim and model_dim and faiss_dim != model_dim:
            self.logger.warning("Model dim %d != FAISS dim %d; embeddings will be aligned (truncate/pad)", model_dim, faiss_dim)
        elif model_dim and not faiss_dim:
            self.logger.info("Using model dimension %d as FAISS dimension", model_dim)
        elif faiss_dim and not model_dim:
            self.logger.info("Using FAISS dimension %d; model alignment handled in generator", faiss_dim)

    def _generate_embeddings_from_step02(
        self, 
        step02_output: Step02AstExtractorOutput, 
        stats: Dict[str, Any],
        progress: Optional[Any] = None,
    ) -> List[EmbeddingChunk]:
        """Generate embedding chunks from Step02 domain objects, with progress updates per file."""
        all_chunks: List[EmbeddingChunk] = []
        
        try:
            # Process files from source inventory
            for source_location in step02_output.source_inventory.source_locations:
                for subdomain in source_location.subdomains:
                    for file_item in subdomain.file_inventory:
                        # Extract chunks from file using embedding generator
                        if file_item.details:
                            file_chunks = self.embedding_generator._extract_chunks_from_file(
                                file_item,
                                subdomain=subdomain,
                                source_location=source_location,
                            )
                            all_chunks.extend(file_chunks)
                            stats["total_files_processed"] += 1
                            if progress is not None:
                                progress.update(1, current_item=getattr(file_item, 'path', 'file'))
            
            # Filter chunks with valid embeddings
            valid_chunks = [chunk for chunk in all_chunks if chunk.embedding is not None]
            
            stats["total_chunks_generated"] = len(all_chunks)
            stats["total_embeddings_created"] = len(valid_chunks)
            
            self.logger.info(
                "Generated %d chunks (%d with embeddings) from %d files",
                len(all_chunks),
                len(valid_chunks),
                stats["total_files_processed"]
            )
            
            return valid_chunks
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to generate embeddings from Step02: %s", e)
            raise ProcessingError(f"Embedding generation failed: {e}") from e
    
    def _perform_semantic_clustering(
        self, 
        chunks: List[EmbeddingChunk], 
        stats: Dict[str, Any]
    ) -> List[SemanticCluster]:
        """Perform semantic clustering on embedding chunks."""
        try:
            if len(chunks) < self.min_chunks_for_clustering:
                self.logger.info(
                    "Skipping clustering: %d chunks < minimum %d",
                    len(chunks),
                    self.min_chunks_for_clustering
                )
                return []
            
            # Determine optimal number of clusters based on chunk count
            n_clusters = min(10, max(3, len(chunks) // 20))
            
            clusters = self.faiss_manager.perform_semantic_clustering(n_clusters)
            stats["semantic_clusters_found"] = len(clusters)
            
            # Log cluster information
            for cluster in clusters:
                dominant_type = cluster.dominant_type or "mixed"
                self.logger.debug(
                    "Cluster %s: %d chunks, dominant type: %s, confidence: %.3f",
                    cluster.cluster_id,
                    len(cluster.chunks),
                    dominant_type,
                    cluster.domain_confidence
                )
            
            return clusters
            
        except (RuntimeError, ValueError, AttributeError) as e:
            self.logger.error("Semantic clustering failed: %s", e)
            return []  # Continue processing without clustering
    
    def _generate_similarity_enhancements(
        self, 
        chunks: List[EmbeddingChunk], 
        stats: Dict[str, Any],
        progress: Optional[Any] = None,
    ) -> List[EnhancementResult]:
        """Generate similarity-based enhancements for high-confidence chunks."""
        enhancement_results: List[EnhancementResult] = []
        try:
            # Sample a subset of chunks for enhancement analysis
            sample_size = min(50, len(chunks))  # Limit for performance
            sample_chunks = chunks[:sample_size]
            # Config-driven knn K
            K = int(getattr(self.step03_config, "knn_k", 5) or 5)
            for idx, chunk in enumerate(sample_chunks):
                # Find similar chunks with configured K
                similarity_results = self.faiss_manager.find_similar_chunks(chunk, k=max(1, K))
                for similarity_result in similarity_results:
                    if similarity_result.confidence_boost >= self.confidence_boost_threshold:
                        enhancement = EnhancementResult(
                            original_confidence=0.5,  # Baseline confidence
                            enhanced_confidence=0.5 + similarity_result.confidence_boost,
                            confidence_boost=similarity_result.confidence_boost,
                            enhancement_method="similarity_boost",
                            similar_items=[chunk_id for chunk_id, _ in similarity_result.similar_chunks],
                            cluster_id=None
                        )
                        enhancement_results.append(enhancement)
                        stats["similarity_enhancements"] = int(stats.get("similarity_enhancements", 0)) + 1
                if progress is not None:
                    progress.update(1, current_item=getattr(chunk, 'chunk_id', 'chunk'))
            self.logger.info("Generated %d similarity enhancements", len(enhancement_results))
            return enhancement_results
        except (RuntimeError, ValueError, AttributeError) as e:
            self.logger.error("Similarity enhancement generation failed: %s", e)
            return []  # Continue processing without enhancements
    
    def _create_step03_output(
        self,
        chunks: List[EmbeddingChunk],
        clusters: List[SemanticCluster],
        enhancements: List[EnhancementResult],
        project_name: str,
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comprehensive Step03 output dictionary."""
        
        model_info = ModelInfo(
            primary=self.step03_config.models.primary,
            fallback=self.step03_config.models.fallback,
            dimension=self.step03_config.models.dimension,
            device=self.step03_config.models.device,
            batch_size=self.step03_config.models.batch_size,
            max_sequence_length=self.step03_config.models.max_sequence_length
        )
        # Create embedding metadata
        embedding_metadata = EmbeddingMetadata(
            version="1.0",
            model_info=model_info,
            total_chunks=len(chunks),
            chunk_mappings=[chunk.to_dict() for chunk in chunks],
            generation_timestamp=time.time()
        )
        
        # Get index statistics
        index_stats = self.faiss_manager.get_index_statistics()
        
        # Organize chunks by type for analysis
        chunks_by_type: Dict[str, List[str]] = {}
        for chunk in chunks:
            chunk_type = chunk.chunk_type
            if chunk_type not in chunks_by_type:
                chunks_by_type[chunk_type] = []
            chunks_by_type[chunk_type].append(chunk.chunk_id)
        
        # JSON-serializable configuration snapshots
        step03_cfg = asdict(self.step03_config)
        models_cfg = asdict(self.step03_config.models)
        faiss_cfg = asdict(self.step03_config.faiss)
        enhancement_cfg = asdict(self.enhancement_config)
        
        return {
            "step03_results": {
                "project_name": project_name,
                "processing_timestamp": time.time(),
                "embedding_chunks": [chunk.to_dict() for chunk in chunks],
                "semantic_clusters": [cluster.to_dict() for cluster in clusters],
                "enhancement_results": [enhancement.to_dict() for enhancement in enhancements],
                "embedding_metadata": embedding_metadata.to_dict(),
                "index_statistics": index_stats,
                "chunk_analysis": {
                    "chunks_by_type": chunks_by_type,
                    "total_chunks": len(chunks),
                    "chunks_with_embeddings": len([c for c in chunks if c.embedding is not None])
                }
            },
            "processing_statistics": stats,
            "configuration": {
                "step03_config": step03_cfg,
                "model_info": models_cfg,
                "faiss_config": faiss_cfg,
                "enhancement_config": enhancement_cfg
            },
            "paths": {
                "embeddings_base": f"projects/{project_name}/embeddings",
                "faiss_index": f"projects/{project_name}/embeddings/faiss_index.bin",
                "metadata_file": f"projects/{project_name}/embeddings/metadata.json"
            }
        }
    
    def _post_implementation(self, shared: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> None:
        """Post-process Step03 results: validate and persist JSON artifact like Step02."""
        self.logger.info("Post-processing Step 03 results")
        
        if not isinstance(exec_result, dict) or "output_data" not in exec_result:
            self.logger.warning("No output_data found in exec_result; skipping Step03 post-processing")
            return
        
        output_data = exec_result["output_data"]
        
        # Validate using overridden validate_results
        validation = self.validate_results(output_data)
        if not validation.is_valid:
            raise ValueError(f"Step 03 output validation failed: {validation.errors}")
        if validation.warnings:
            self.logger.warning("Step 03 validation warnings: %s", validation.warnings)
        
        # Write output file using config pattern like Step02
        output_path = self.config.get_output_path_for_step("step03")
        self.logger.info("Writing Step 03 output to: %s", output_path)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            self.logger.info("Step 03 output written successfully")
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to write Step 03 output: %s", str(e))
            raise
        
        # Store validation and path for pipeline use
        exec_result["validation_result"] = validation
        exec_result["output_path"] = str(output_path)
    
    def validate_results(self, output_data: Dict[str, Any]) -> ValidationResult:
        """Validate Step03 output structure for PocketFlow compliance."""
        errors: List[str] = []
        warnings: List[str] = []
        
        # output_data is typed as Dict[str, Any], so basic dict checks are guaranteed
        
        # Required top-level sections
        for key in ("step03_results", "processing_statistics", "configuration", "paths"):
            if key not in output_data:
                errors.append(f"Missing '{key}' in Step03 output")
        
        # Basic inner checks
        step03_results = output_data.get("step03_results", {})
        if step03_results:
            for key in ("embedding_chunks", "embedding_metadata", "index_statistics"):
                if key not in step03_results:
                    warnings.append(f"Missing '{key}' in step03_results")
            if not isinstance(step03_results.get("embedding_chunks", []), list):
                warnings.append("embedding_chunks should be a list")
        
        stats = output_data.get("processing_statistics", {})
        if stats and "processing_time_seconds" not in stats:
            warnings.append("processing_time_seconds not set in processing_statistics")
        
        # Enforce Step03 gates based on processing_statistics present in output_data
        try:
            stats = output_data.get("processing_statistics", {}) if isinstance(output_data, dict) else {}
            coverage = float(stats.get("embedding_coverage_pct", 0.0))
            cohesion = float(stats.get("cluster_cohesion", 0.0))
            gates = self.config.quality_gates.step03
            if coverage < float(gates.min_embedding_coverage_pct):
                errors.append(
                    f"min_embedding_coverage_pct gate failed: {coverage:.2f} < {gates.min_embedding_coverage_pct:.2f}"
                )
            if cohesion < float(gates.min_cluster_cohesion):
                errors.append(
                    f"min_cluster_cohesion gate failed: {cohesion:.2f} < {gates.min_cluster_cohesion:.2f}"
                )
        except Exception as e:  # pylint: disable=broad-except
            warnings.append(f"Gate evaluation warning: {e}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _enforce_quality_gates(self, stats: Dict[str, Union[int, float]]) -> None:
        """Enforce Step03 gates (coverage and cohesion) and raise ProcessingError with reasons if failed."""
        gates = self.config.quality_gates.step03
        reasons: List[str] = []
        try:
            coverage = float(stats.get("embedding_coverage_pct", 0.0))
            cohesion = float(stats.get("cluster_cohesion", 0.0))
            if coverage < float(gates.min_embedding_coverage_pct):
                reasons.append(
                    f"min_embedding_coverage_pct gate failed: {coverage:.2f} < {gates.min_embedding_coverage_pct:.2f}"
                )
            if cohesion < float(gates.min_cluster_cohesion):
                reasons.append(
                    f"min_cluster_cohesion gate failed: {cohesion:.2f} < {gates.min_cluster_cohesion:.2f}"
                )
        except Exception as e:  # pylint: disable=broad-except
            reasons.append(f"Gate evaluation error: {e}")
        if reasons:
            raise ProcessingError("; ".join(reasons))

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of Step03 processing capabilities and configuration."""
        return {
            "processor_type": "Step03EmbeddingsProcessor",
            "version": "1.0",
            "capabilities": [
                "Code component embedding generation",
                "FAISS vector index management",
                "Semantic clustering analysis",
                "Similarity-based enhancements",
                "Multi-language support (Java, JSP, Config)"
            ],
            "supported_input": "Step02AstExtractorOutput",
            "output_format": "Embedding chunks with vector similarity analysis",
            "configuration_section": "step03_embeddings",
            "dependencies": [
                "Step02 domain objects",
                "Transformer models (CodeBERT/sentence-transformers)",
                "FAISS vector index library"
            ]
        }


def create_step03_processor() -> Step03EmbeddingsProcessor:
    """
    Factory function to create Step03 embeddings processor.
    
    Returns:
        Configured Step03EmbeddingsProcessor instance
        
    Raises:
        ConfigurationError: If processor initialization fails
    """
    try:
        return Step03EmbeddingsProcessor()
    except Exception as e:  # pylint: disable=broad-except
        raise ConfigurationError(f"Failed to create Step03 processor: {e}") from e
