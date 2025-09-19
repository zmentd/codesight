from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from config.config import Config
from steps.step05.models import Capability, CapabilityOutput
from steps.step06.models import DomainSection, Step06DocBundle


def _group_capabilities_by_domain(capabilities: List[Capability]) -> Dict[Tuple[str, Optional[str], Optional[str]], List[Capability]]:
    groups: Dict[Tuple[str, Optional[str], Optional[str]], List[Capability]] = defaultdict(list)
    for c in capabilities:
        dom = (c.domain or "Unclassified").strip() if isinstance(getattr(c, 'domain', None), str) else "Unclassified"
        # Parse optional tags Layer: and Subdomain: if present when domain_call returned them
        layer = None
        subdomain = None
        for t in (c.tags or []):
            if isinstance(t, str) and t.startswith("Layer:"):
                layer = t.split(":", 1)[1].strip() or layer
            if isinstance(t, str) and t.startswith("Subdomain:"):
                subdomain = t.split(":", 1)[1].strip() or subdomain
        groups[(dom, subdomain, layer)].append(c)
    return groups


def _group_capabilities_for_brd(capabilities: List[Capability]) -> Dict[str, List[Capability]]:
    """Group only by business domain label for BRD (hide technical layer/subdomain)."""
    groups: Dict[str, List[Capability]] = defaultdict(list)
    for c in capabilities:
        dom = (c.domain or "Unclassified").strip() if isinstance(getattr(c, 'domain', None), str) else "Unclassified"
        groups[dom].append(c)
    return groups


def _md_h(text: str, level: int = 2) -> str:
    level = max(1, min(6, level))
    return f"{'#' * level} {text}"  # Confluence accepts GitHub-style headings


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    # Confluence wiki renderer supports GitHub-style pipe tables in recent versions
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join(["| " + " | ".join(r) + " |" for r in rows])
    return "\n".join([head, sep, body]) if rows else "\n".join([head, sep])


def _nz(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _humanize_name(name: str) -> str:
    s = (name or "").strip()
    if not s:
        return ""
    # Replace separators with spaces
    for ch in ["_", "-", ".", "/", "\\"]:
        s = s.replace(ch, " ")
    # Split camel case (simple heuristic)
    import re
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    # Remove common technical suffixes/prefixes
    for suf in ["Action", "Controller", "Servlet", "Frame", "Helper", "Catalog", "List", "Dashboard", "Mail", "Mgr", "Bean", "DTO", "Impl"]:
        if s.endswith(" " + suf):
            s = s[: -(len(suf) + 1)]
    # Collapse spaces and title-case
    s = " ".join(s.split())
    return s[:1].upper() + s[1:]


def _cap_row_for_brd(c: Capability) -> List[str]:
    # Prefer human-friendly name; fall back to purpose if name looks code-ish
    name = _humanize_name(c.name or c.id)
    if len(name) <= 2:
        name = c.purpose[:60] + ("…" if len(c.purpose) > 60 else "")
    members = c.members or {}
    menu = _nz(members.get("menu_path"))
    display = f"{name} (Menu: {menu})" if menu else name
    return [
        display,
        (c.purpose or "").strip(),
    ]


def _cap_row_for_tech(c: Capability) -> List[str]:
    members = c.members or {}
    screens = members.get("screens_details") or []
    handlers = members.get("handlers_details") or []
    db_usage = members.get("db_usage") or []
    procs = members.get("procedures_usage") or []

    def _nz(val: Any) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None

    screen_names: List[str] = []
    for s in screens:
        if isinstance(s, dict):
            val = _nz(s.get('title') or s.get('view') or s.get('name') or s.get('id'))
            if val:
                screen_names.append(val)
    screens_s = ", ".join(sorted(set(screen_names)))

    handler_names: List[str] = []
    for h in handlers:
        if isinstance(h, dict):
            val = _nz(h.get('class') or h.get('name') or h.get('id'))
            if val:
                handler_names.append(val)
    handlers_s = ", ".join(sorted(set(handler_names)))

    table_names: List[str] = []
    for u in db_usage:
        if isinstance(u, dict) and _nz(u.get('table')):
            table_names.append(str(u.get('table')))
    tables_s = ", ".join(sorted(set(table_names)))

    proc_names: List[str] = []
    for p in procs:
        if isinstance(p, dict) and _nz(p.get('procedure')):
            proc_names.append(str(p.get('procedure')))
    procs_s = ", ".join(sorted(set(proc_names)))

    return [
        c.name,
        screens_s or "-",
        handlers_s or "-",
        tables_s or "-",
        procs_s or "-",
    ]


def _render_domain_section_brd(domain: str, caps: List[Capability]) -> str:
    title = f"{domain}"
    rows = [_cap_row_for_brd(c) for c in caps]
    table = _md_table(["Capability", "Business Purpose"], rows)
    return "\n\n".join([
        _md_h(title, 3),
        table,
    ])


def _render_domain_section_tech(key: Tuple[str, Optional[str], Optional[str]], caps: List[Capability]) -> str:
    dom, sub, layer = key
    title_bits = [dom]
    if sub:
        title_bits.append(f"/ {sub}")
    if layer:
        title_bits.append(f" — {layer}")
    title = "".join(title_bits)

    rows = [_cap_row_for_tech(c) for c in caps]
    table = _md_table(["Capability", "Screens", "Handlers", "Tables", "Procedures"], rows)

    details_parts: List[str] = [
        _md_h(title, 3),
        table,
    ]

    # Append per-capability rationale and evidence counts for traceability
    for c in caps:
        cite_count = len(c.citations or [])
        rationale = (c.rationale or "").strip()
        details_parts.append(f"- {c.name} — Evidence: {cite_count} citations" + (f" — Rationale: {rationale}" if rationale else ""))

    return "\n\n".join(details_parts)


def render_documents(step05: CapabilityOutput) -> Step06DocBundle:
    project_name = step05.project_name

    # Group by domain/subdomain/layer for Technical Spec
    groups = _group_capabilities_by_domain(step05.capabilities or [])
    # Group by domain only for BRD
    brd_groups = _group_capabilities_for_brd(step05.capabilities or [])

    # Render BRD: business-focused; only capability and purpose
    brd_parts: List[str] = [
        _md_h(f"{project_name} — Business Requirements Document", 1),
        "Business-focused view of capabilities grouped by domain.",
    ]
    # Optional domain summary
    if brd_groups:
        summary_lines = [f"- {dom}: {len(caps)} capabilities" for dom, caps in sorted(brd_groups.items(), key=lambda kv: kv[0] or "")]
        brd_parts.append(_md_h("Domains", 2))
        brd_parts.append("\n".join(summary_lines))
    for dom, caps in sorted(brd_groups.items(), key=lambda kv: kv[0] or ""):
        brd_parts.append(_render_domain_section_brd(dom, caps))
    brd_md = "\n\n".join(brd_parts)

    # Render Technical Spec: technical drill-down; includes screens/handlers/db/procs
    tech_parts: List[str] = [
        _md_h(f"{project_name} — Technical Specification", 1),
        "Generated from Step05 capability graph with citations and provenance.",
    ]
    for key, caps in sorted(groups.items(), key=lambda kv: (kv[0][0] or "", kv[0][1] or "", kv[0][2] or "")):
        tech_parts.append(_render_domain_section_tech(key, caps))
    tech_md = "\n\n".join(tech_parts)

    # Build structured sections metadata if needed downstream (optional)
    sections: List[DomainSection] = []
    for key, caps in groups.items():
        dom, sub, layer = key
        sections.append(DomainSection(
            domain=dom,
            subdomain=sub,
            layer=layer,
            title=f"{dom}{(' / ' + sub) if sub else ''}{(' — ' + layer) if layer else ''}",
            summary=f"{len(caps)} capabilities",
            capabilities=[{"id": c.id, "name": c.name} for c in caps]
        ))

    return Step06DocBundle(
        project_name=project_name,
        brd_markdown=brd_md,
        tech_spec_markdown=tech_md,
        sections=sections,
    )
