from __future__ import annotations

from typing import Any, Dict, List, Tuple

from steps.step05.models import Capability, CapabilityOutput


def build_summary(output: CapabilityOutput, top_k: int = 10) -> Dict[str, Any]:
    """Compute a human-readable summary for Step05 CapabilityOutput.

    Returns a dict safe to serialize alongside exec_result.
    """
    try:
        caps: List[Capability] = output.capabilities or []
        rel_count = len(output.relations or [])
        cov = float(output.stats.get("route_coverage_pct", 0.0)) if isinstance(output.stats, dict) else 0.0

        # Aggregate tags
        tag_freq: Dict[str, int] = {}
        for c in caps:
            for t in (c.tags or []):
                if isinstance(t, str) and t:
                    tag_freq[t] = tag_freq.get(t, 0) + 1
        top_tags: List[Tuple[str, int]] = sorted(tag_freq.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

        # Aggregate domains if present
        dom_freq: Dict[str, int] = {}
        for c in caps:
            d = getattr(c, 'domain', None)
            if isinstance(d, str) and d:
                dom_freq[d] = dom_freq.get(d, 0) + 1
        top_domains: List[Tuple[str, int]] = sorted(dom_freq.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

        # Example capabilities: highest citations then confidence
        def cite_count(c: Capability) -> int:
            try:
                return len(c.citations or [])
            except Exception:
                return 0
        examples: List[Dict[str, Any]] = []
        for c in sorted(caps, key=lambda x: (cite_count(x), getattr(x, 'confidence', 0.0)), reverse=True)[: min(5, len(caps))]:
            examples.append({
                "id": c.id,
                "name": c.name,
                "confidence": float(getattr(c, 'confidence', 0.0) or 0.0),
                "citations": cite_count(c),
                "tags": list(c.tags or []),
            })

        return {
            "project_name": output.project_name,
            "capability_count": len(caps),
            "relation_count": rel_count,
            "route_coverage_pct": cov,
            "top_tags": top_tags,
            "top_domains": top_domains,
            "examples": examples,
        }
    except Exception as e:  # pragma: no cover - summary best-effort
        return {
            "error": f"summary_failed: {e}",
            "project_name": output.project_name,
            "capability_count": len(getattr(output, 'capabilities', []) or []),
            "relation_count": len(getattr(output, 'relations', []) or []),
            "route_coverage_pct": float((getattr(output, 'stats', {}) or {}).get("route_coverage_pct", 0.0)),
        }
