from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# -----------------------------
# Evidence primitives
# -----------------------------
@dataclass
class Evidence:
    chunk_id: Optional[str] = None
    score: Optional[float] = None
    file: Optional[str] = None
    line: Optional[int] = None
    end_line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "score": self.score,
            "file": self.file,
            "line": self.line,
            "end_line": self.end_line,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        return cls(
            chunk_id=data.get("chunk_id"),
            score=data.get("score"),
            file=data.get("file"),
            line=data.get("line"),
            end_line=data.get("end_line"),
        )


# -----------------------------
# Core schema: Entity / Relation / Trace
# -----------------------------
@dataclass
class Entity:
    id: str
    type: str
    name: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    source_refs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "attributes": self.attributes,
            "source_refs": self.source_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            name=data.get("name"),
            attributes=dict(data.get("attributes", {})),
            source_refs=list(data.get("source_refs", [])),
        )


@dataclass
class Relation:
    id: str
    from_id: str
    to_id: str
    type: str
    confidence: float = 0.5
    evidence: List[Evidence] = field(default_factory=list)
    rationale: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from": self.from_id,
            "to": self.to_id,
            "type": self.type,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relation":
        f = data.get("from") or data.get("from_id")
        t = data.get("to") or data.get("to_id")
        if not isinstance(f, str) or not isinstance(t, str):
            raise ValueError("Relation.from_dict requires 'from'/'to' as strings")
        return cls(
            id=str(data["id"]),
            from_id=f,
            to_id=t,
            type=str(data["type"]),
            confidence=float(data.get("confidence", 0.5)),
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
            rationale=data.get("rationale"),
        )


@dataclass
class Trace:
    id: str
    screen: Optional[str]
    route: Optional[str]
    path: List[str]
    crud_summary: Dict[str, List[str]] = field(default_factory=dict)
    tables: List[str] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "screen": self.screen,
            "route": self.route,
            "path": list(self.path),
            "crud_summary": dict(self.crud_summary),
            "tables": list(self.tables),
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trace":
        return cls(
            id=str(data["id"]),
            screen=data.get("screen"),
            route=data.get("route"),
            path=[str(x) for x in data.get("path", [])],
            crud_summary={k: [str(x) for x in v] for k, v in dict(data.get("crud_summary", {})).items()},
            tables=[str(x) for x in data.get("tables", [])],
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
            confidence=float(data.get("confidence", 0.5)),
        )


# -----------------------------
# Top-level output wrapper
# -----------------------------
@dataclass
class Step04Output:
    version: str
    project_name: str
    generated_at: str
    config: Dict[str, Any] = field(default_factory=dict)
    entities: List[Entity] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    traces: List[Trace] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @classmethod
    def create(cls, project_name: str, version: str = "1.0", config: Optional[Dict[str, Any]] = None) -> "Step04Output":
        return cls(
            version=version,
            project_name=project_name,
            generated_at=cls.now_iso(),
            config=config or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "config": dict(self.config),
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "traces": [t.to_dict() for t in self.traces],
            "stats": dict(self.stats),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Step04Output":
        return cls(
            version=str(data.get("version", "1.0")),
            project_name=str(data.get("project_name", "")),
            generated_at=str(data.get("generated_at", cls.now_iso())),
            config=dict(data.get("config", {})),
            entities=[Entity.from_dict(e) for e in data.get("entities", [])],
            relations=[Relation.from_dict(r) for r in data.get("relations", [])],
            traces=[Trace.from_dict(t) for t in data.get("traces", [])],
            stats=dict(data.get("stats", {})),
        )
