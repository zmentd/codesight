from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DomainSection:
    domain: str
    subdomain: Optional[str]
    layer: Optional[str]
    title: str
    summary: str
    capabilities: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Step06DocBundle:
    project_name: str
    # Confluence-ready markdown
    brd_markdown: str
    tech_spec_markdown: str
    # Optional: raw sections for downstream processing
    sections: List[DomainSection] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "brd_markdown": self.brd_markdown,
            "tech_spec_markdown": self.tech_spec_markdown,
            "sections": [s.__dict__ for s in self.sections],
        }
