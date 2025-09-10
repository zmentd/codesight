"""Vector-based analysis (from modernization-project-flow)."""
from .embedding_generator import EmbeddingGenerator, EmbeddingResult
from .faiss_manager import FaissManager

__all__ = ["EmbeddingGenerator", "EmbeddingResult", "FaissManager"]
