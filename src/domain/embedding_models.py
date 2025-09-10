"""
Domain models for Step03 embeddings and semantic analysis.

This module contains classes for representing embedding chunks, similarity results,
and semantic analysis metadata for the Step03 pipeline.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class EmbeddingChunk:
    """Represents a code chunk with its embedding vector."""
    chunk_id: str
    content: str
    chunk_type: str  # "method", "class", "config", "domain", "jsp"
    source_path: str  # Unix relative path from project root
    start_line: int
    end_line: int
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation (excluding embedding vector)."""
        def _json_safe(obj: Any) -> Any:
            if isinstance(obj, Enum):
                try:
                    return obj.value
                except Exception:  # pylint: disable=broad-except
                    return str(obj)
            if isinstance(obj, np.generic):
                try:
                    return obj.item()
                except Exception:  # pylint: disable=broad-except
                    return str(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (set, frozenset)):
                return list(obj)
            if isinstance(obj, dict):
                return {k: _json_safe(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_json_safe(v) for v in obj]
            return obj
        
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "chunk_type": self.chunk_type,
            "source_path": self.source_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "metadata": _json_safe(self.metadata),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingChunk":
        """Create instance from dictionary."""
        return cls(
            chunk_id=data["chunk_id"],
            content=data["content"],
            chunk_type=data["chunk_type"],
            source_path=data["source_path"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            metadata=data.get("metadata", {})
        )


@dataclass
class SimilarityResult:
    """Result of similarity analysis for a chunk."""
    target_chunk_id: str
    similar_chunks: List[Tuple[str, float]]  # [(chunk_id, similarity_score)]
    confidence_boost: float
    cluster_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "target_chunk_id": self.target_chunk_id,
            "similar_chunks": [{"chunk_id": chunk_id, "score": score} 
                             for chunk_id, score in self.similar_chunks],
            "confidence_boost": self.confidence_boost,
            "cluster_info": self.cluster_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimilarityResult":
        """Create instance from dictionary."""
        similar_chunks = [(item["chunk_id"], item["score"]) 
                         for item in data.get("similar_chunks", [])]
        
        return cls(
            target_chunk_id=data["target_chunk_id"],
            similar_chunks=similar_chunks,
            confidence_boost=data["confidence_boost"],
            cluster_info=data.get("cluster_info", {})
        )


@dataclass
class SemanticCluster:
    """Represents a cluster of semantically similar code chunks."""
    cluster_id: str
    chunks: List[str]  # List of chunk IDs
    center_embedding: Optional[np.ndarray] = None
    avg_similarity: float = 0.0
    dominant_type: Optional[str] = None  # Most common chunk_type in cluster
    domain_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation (excluding center_embedding)."""
        return {
            "cluster_id": self.cluster_id,
            "chunks": self.chunks,
            "avg_similarity": self.avg_similarity,
            "dominant_type": self.dominant_type,
            "domain_confidence": self.domain_confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticCluster":
        """Create instance from dictionary."""
        return cls(
            cluster_id=data["cluster_id"],
            chunks=data["chunks"],
            avg_similarity=data["avg_similarity"],
            dominant_type=data.get("dominant_type"),
            domain_confidence=data["domain_confidence"]
        )


@dataclass
class ModelInfo:
    """ModelInfo configuration."""
    primary: str = "microsoft/codebert-base"
    fallback: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 768
    device: str = "cpu"
    batch_size: int = 32
    max_sequence_length: int = 512

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "primary": self.primary,
            "fallback": self.fallback,
            "dimension": self.dimension,
            "device": self.device,
            "batch_size": self.batch_size,
            "max_sequence_length": self.max_sequence_length
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelInfo":
        """Create ModelInfo from dictionary."""
        if isinstance(data, ModelInfo):
            return data
        return cls(
            primary=data.get("primary", "microsoft/codebert-base"),
            fallback=data.get("fallback", "sentence-transformers/all-MiniLM-L6-v2"),
            dimension=int(data.get("dimension", 768)),
            device=data.get("device", "cpu"),
            batch_size=int(data.get("batch_size", 32)),
            max_sequence_length=int(data.get("max_sequence_length", 512)),
        )


@dataclass
class EmbeddingMetadata:
    """Metadata for embeddings storage and management."""
    version: str
    model_info: ModelInfo
    total_chunks: int
    chunk_mappings: List[Dict[str, Any]]
    similarity_clusters: List[SemanticCluster] = field(default_factory=list)
    generation_timestamp: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "version": self.version,
            "model_info": self.model_info.to_dict() if self.model_info else {},
            "total_chunks": self.total_chunks,
            "chunk_mappings": self.chunk_mappings,
            "similarity_clusters": [cluster.to_dict() for cluster in self.similarity_clusters],
            "generation_timestamp": self.generation_timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingMetadata":
        """Create instance from dictionary."""
        clusters = [SemanticCluster.from_dict(cluster_data) 
                   for cluster_data in data.get("similarity_clusters", [])]
        # ModelInfo may be provided as dict in persisted file
        mi = data.get("model_info")
        model_info = ModelInfo.from_dict(mi) if isinstance(mi, dict) else (mi if isinstance(mi, ModelInfo) else ModelInfo())
        
        return cls(
            version=data["version"],
            model_info=model_info,
            total_chunks=data["total_chunks"],
            chunk_mappings=data["chunk_mappings"],
            similarity_clusters=clusters,
            generation_timestamp=data.get("generation_timestamp", 0.0)
        )


@dataclass
class EnhancementResult:
    """Result of semantic enhancement for components."""
    original_confidence: float
    enhanced_confidence: float
    confidence_boost: float
    enhancement_method: str
    similar_items: List[str] = field(default_factory=list)
    cluster_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "original_confidence": self.original_confidence,
            "enhanced_confidence": self.enhanced_confidence,
            "confidence_boost": self.confidence_boost,
            "enhancement_method": self.enhancement_method,
            "similar_items": self.similar_items,
            "cluster_id": self.cluster_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnhancementResult":
        """Create instance from dictionary."""
        return cls(
            original_confidence=data["original_confidence"],
            enhanced_confidence=data["enhanced_confidence"],
            confidence_boost=data["confidence_boost"],
            enhancement_method=data["enhancement_method"],
            similar_items=data.get("similar_items", []),
            cluster_id=data.get("cluster_id")
        )


# --- Search API domain classes ---

@dataclass
class SearchFilters:
    """Typed filters for semantic search over embedding chunks (all matches are case-insensitive exact matches)."""
    chunk_type: Optional[str] = None
    subdomain_name: Optional[str] = None
    source_directory_name: Optional[str] = None
    file_language: Optional[str] = None
    file_type: Optional[str] = None
    package_name: Optional[str] = None
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    # Reverse-engineering-oriented filters
    has_sql: Optional[bool] = None
    stored_procedure_name: Optional[str] = None
    entity_mapping_table: Optional[str] = None
    file_path: Optional[str] = None
    source_relative_path: Optional[str] = None


@dataclass
class SearchHit:
    """Typed search hit that returns the matched chunk and score."""
    chunk: EmbeddingChunk
    score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk": self.chunk.to_dict(),
            "score": self.score,
        }
