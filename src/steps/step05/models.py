from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Capability:
    id: str
    name: str
    # Purpose replaces the previous summary and aligns with Step05 spec
    purpose: str
    confidence: float
    # Evidence citations (file:line, chunk_id, etc.)
    citations: List[Dict] = field(default_factory=list)
    # Business synonyms suggested by LLM
    synonyms: List[str] = field(default_factory=list)
    # Members of this capability (route/jsp/handler ids) and enriched metadata for Step06
    members: Dict[str, Any] = field(default_factory=dict)
    # Tags and optional domain label
    tags: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    # Rationale text (can include LLM paraphrases or caveats)
    rationale: Optional[str] = None
    # Trace ids associated with the capability
    trace_ids: List[str] = field(default_factory=list)
    # Provenance information including LLM usage
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityRelation:
    id: str
    from_id: str
    to_id: str
    type: str
    confidence: float = 0.9
    evidence: List[Dict] = field(default_factory=list)
    rationale: Optional[str] = None


@dataclass
class CapabilityOutput:
    project_name: str
    capabilities: List[Capability] = field(default_factory=list)
    relations: List[CapabilityRelation] = field(default_factory=list)
    stats: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "project_name": self.project_name,
            "capabilities": [
                {
                    **{k: v for k, v in c.__dict__.items() if k != "purpose"},
                    # Keep backward compatibility for any consumer still reading 'summary'
                    "summary": c.purpose,
                }
                for c in self.capabilities
            ],
            "relations": [r.__dict__ for r in self.relations],
            "stats": self.stats,
        }
