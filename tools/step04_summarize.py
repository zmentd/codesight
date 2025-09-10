#!/usr/bin/env python3
"""
Summarize Step04 output for a project:
- Counts by entity and relation type
- Top tables by reads/writes/deletes
- Top procedures invoked
- Sample route -> handlesRoute -> renders chains
- Security summary (securedBy relations)
- Traces summary (count and a few samples)
- Optional: JSP security signals from Step02 (pattern_hits, tags)
Writes a human-readable report to projects/<project>/output/step04_summary.txt
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from typing import Counter as CounterT
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

# Optional imports for Step02 scan
try:
    from domain.jsp_details import JspDetails  # type: ignore
    from domain.step02_output import Step02AstExtractorOutput  # type: ignore
    from steps.step02.source_inventory_query import SourceInventoryQuery  # type: ignore
except Exception:  # pragma: no cover
    Step02AstExtractorOutput = None  # type: ignore
    SourceInventoryQuery = None  # type: ignore
    JspDetails = None  # type: ignore


def load_step04(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    return data


def summarize_entities(entities: List[Dict[str, Any]]) -> CounterT[str]:
    c: CounterT[str] = Counter()
    for e in entities:
        t = e.get("type")
        if isinstance(t, str):
            c[t] += 1
    return c


def summarize_relations(relations: List[Dict[str, Any]]) -> CounterT[str]:
    c: CounterT[str] = Counter()
    for r in relations:
        t = r.get("type")
        if isinstance(t, str):
            c[t] += 1
    return c


def _rel_from(r: Dict[str, Any]) -> Any:
    return r.get("from") if "from" in r else r.get("from_id")


def _rel_to(r: Dict[str, Any]) -> Any:
    return r.get("to") if "to" in r else r.get("to_id")


def top_tables(relations: List[Dict[str, Any]], top_n: int = 25) -> Dict[str, List[Tuple[str, int]]]:
    # to like table_<name>
    reads: CounterT[str] = Counter()
    writes: CounterT[str] = Counter()
    deletes: CounterT[str] = Counter()
    for r in relations:
        t = r.get("type")
        to_id = _rel_to(r)
        if not isinstance(to_id, str) or not to_id.startswith("table_"):
            continue
        table = to_id[len("table_"):]
        if t == "readsFrom":
            reads[table] += 1
        elif t == "writesTo":
            writes[table] += 1
        elif t == "deletesFrom":
            deletes[table] += 1
    return {
        "reads": reads.most_common(top_n),
        "writes": writes.most_common(top_n),
        "deletes": deletes.most_common(top_n),
    }


def top_procedures(relations: List[Dict[str, Any]], top_n: int = 25) -> List[Tuple[str, int]]:
    inv: CounterT[str] = Counter()
    for r in relations:
        if r.get("type") == "invokesProcedure":
            to_id = _rel_to(r)
            if isinstance(to_id, str) and to_id.startswith("proc_"):
                inv[to_id[len("proc_"):]] += 1
    return inv.most_common(top_n)


def sample_route_chains(
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    max_samples: int = 20,
) -> List[Dict[str, Any]]:
    # Build quick index
    ents: Dict[str, Dict[str, Any]] = {e["id"]: e for e in entities if isinstance(e.get("id"), str)}
    by_from: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in relations:
        fid = _rel_from(r)
        if isinstance(fid, str):
            by_from[fid].append(r)

    def _name_for(id_val: Any) -> Any:
        if isinstance(id_val, str):
            return ents.get(id_val, {}).get("name")
        return None

    samples: List[Dict[str, Any]] = []
    for e in entities:
        if e.get("type") != "Route":
            continue
        rid = e.get("id")
        if not isinstance(rid, str):
            continue
        handles = [r for r in by_from.get(rid, []) if r.get("type") == "handlesRoute"]
        renders = [r for r in by_from.get(rid, []) if r.get("type") == "renders"]
        if not handles and not renders:
            continue
        item = {
            "route": e.get("name"),
            "handles": [_name_for(h.get("to") if "to" in h else h.get("to_id")) for h in handles][:2],
            "renders": [_name_for(r.get("to") if "to" in r else r.get("to_id")) for r in renders][:2],
        }
        samples.append(item)
        if len(samples) >= max_samples:
            break
    return samples


def security_summary(entities: List[Dict[str, Any]], relations: List[Dict[str, Any]]) -> Dict[str, Any]:
    ents: Dict[str, Dict[str, Any]] = {e["id"]: e for e in entities if isinstance(e.get("id"), str)}
    roles: CounterT[str] = Counter()
    secured_from_types: CounterT[str] = Counter()
    examples: List[Dict[str, Any]] = []
    for r in relations:
        if r.get("type") != "securedBy":
            continue
        from_id = _rel_from(r)
        to_id = _rel_to(r)
        from_e = ents.get(from_id) if isinstance(from_id, str) else None
        to_e = ents.get(to_id) if isinstance(to_id, str) else None
        if to_e and to_e.get("type") == "Role":
            roles[str(to_e.get("name"))] += 1
        if from_e:
            secured_from_types[str(from_e.get("type"))] += 1
            if len(examples) < 10:
                examples.append({
                    "from": from_e.get("name") or from_e.get("id"),
                    "from_type": from_e.get("type"),
                    "role": to_e.get("name") if to_e else to_id,
                    "rationale": r.get("rationale"),
                })
    return {
        "roles": roles.most_common(),
        "secured_from_types": secured_from_types.most_common(),
        "examples": examples,
    }


def traces_summary(traces: List[Dict[str, Any]], max_samples: int = 10) -> Tuple[int, List[Dict[str, Any]]]:
    total = len(traces or [])
    samples: List[Dict[str, Any]] = []
    for t in (traces or [])[:max_samples]:
        samples.append({
            "id": t.get("id"),
            "route": t.get("route"),
            "screen": t.get("screen"),
            "path": t.get("path"),
            "tables": t.get("tables"),
            "crud_summary": t.get("crud_summary"),
            "confidence": t.get("confidence"),
        })
    return total, samples


def jsp_security_from_step02(project: str) -> Dict[str, Any]:
    """Best-effort summary of JSP security signals from Step02 using domain classes.
    Looks at pattern_hits.security and known security tag prefixes in jsp_tags.
    """
    result = {
        "jsp_files": 0,
        "files_with_security_hits": 0,
        "security_tag_counts": [],
        "examples": [],
    }
    if Step02AstExtractorOutput is None or SourceInventoryQuery is None or JspDetails is None:
        return result

    step02_path = ROOT / "projects" / project / "output" / "step02_output.json"
    if not step02_path.exists():
        return result
    try:
        with step02_path.open("r", encoding="utf-8") as f:
            raw: Dict[str, Any] = json.load(f)
        step02 = Step02AstExtractorOutput.from_dict(raw)  # type: ignore[attr-defined]
    except Exception:
        return result

    q = SourceInventoryQuery(step02.source_inventory).files().detail_type("jsp")  # type: ignore[attr-defined]
    files = q.execute().items
    sec_tag_counter: CounterT[str] = Counter()
    examples: List[Dict[str, Any]] = []
    total = 0
    with_hits = 0

    # Recognize common security tag prefixes
    sec_prefixes = {"sec", "security"}
    code_role_re = re.compile(r"role\s*=\s*\"([^\"]+)\"|access\s*=\s*\"([^\"]+)\"", re.IGNORECASE)

    for f in files:
        details = f.details
        if not isinstance(details, JspDetails):  # type: ignore[arg-type]
            continue
        total += 1
        hits = 0
        # pattern_hits.security
        try:
            ph = getattr(details, "pattern_hits", None)
            if ph and getattr(ph, "security", None):
                hits += len(ph.security)
                if len(examples) < 5:
                    examples.append({"file": f.path, "pattern_hits.security": ph.security[:3]})
        except Exception:
            pass
        # jsp_tags with sec:* or security:*
        try:
            for t in getattr(details, "jsp_tags", []) or []:
                tag = getattr(t, "tag_name", "") or ""
                if ":" in tag and tag.split(":", 1)[0] in sec_prefixes:
                    sec_tag_counter[tag] += 1
                    hits += 1
                    if len(examples) < 5:
                        # Extract role/access attr from full_text if present
                        fx = getattr(t, "full_text", "") or ""
                        m = code_role_re.search(fx)
                        role_or_access = m.group(1) or m.group(2) if m else None
                        examples.append({"file": f.path, "tag": tag, "attr": role_or_access})
        except Exception:
            pass
        if hits:
            with_hits += 1

    result["jsp_files"] = total
    result["files_with_security_hits"] = with_hits
    result["security_tag_counts"] = sec_tag_counter.most_common()
    result["examples"] = examples
    return result


def write_report(project: str, out: Dict[str, Any], dest: Path) -> None:
    entities = out.get("entities", [])
    relations = out.get("relations", [])
    traces = out.get("traces", [])

    ent_counts = summarize_entities(entities)
    rel_counts = summarize_relations(relations)
    tables = top_tables(relations)
    procs = top_procedures(relations)
    route_samples = sample_route_chains(entities, relations)
    sec = security_summary(entities, relations)
    trace_total, trace_samples = traces_summary(traces)
    jsp_sec = jsp_security_from_step02(project)

    lines: List[str] = []
    lines.append(f"Project: {project}")
    lines.append(f"Version: {out.get('version')}  Generated: {out.get('generated_at')}")
    lines.append("")

    lines.append("== Entities ==")
    for k, v in ent_counts.most_common():
        lines.append(f"  {k:16} {v}")
    lines.append("")

    lines.append("== Relations ==")
    for k, v in rel_counts.most_common():
        lines.append(f"  {k:16} {v}")
    lines.append("")

    lines.append("== Top Tables ==")
    lines.append("-- Reads --")
    for name, cnt in tables["reads"]:
        lines.append(f"  {name:40} {cnt}")
    lines.append("-- Writes --")
    for name, cnt in tables["writes"]:
        lines.append(f"  {name:40} {cnt}")
    lines.append("-- Deletes --")
    for name, cnt in tables["deletes"]:
        lines.append(f"  {name:40} {cnt}")
    lines.append("")

    lines.append("== Top Procedures Invoked ==")
    for name, cnt in procs:
        lines.append(f"  {name:40} {cnt}")
    lines.append("")

    lines.append("== Route Chains (sample) ==")
    for s in route_samples:
        lines.append(f"  {s['route']} -> handles: {s['handles']} -> renders: {s['renders']}")
    lines.append("")

    lines.append("== Security (securedBy) ==")
    lines.append("-- Roles --")
    for role, cnt in sec["roles"]:
        lines.append(f"  {role:24} {cnt}")
    lines.append("-- From Types --")
    for t, cnt in sec["secured_from_types"]:
        lines.append(f"  {t:16} {cnt}")
    lines.append("-- Examples --")
    for ex in sec["examples"]:
        lines.append(f"  {ex['from_type']}: {ex['from']} -> role:{ex['role']}  ({ex['rationale']})")
    lines.append("")

    lines.append("== JSP Security (Step02) ==")
    if jsp_sec.get("jsp_files", 0) == 0:
        lines.append("  (Step02 not available or could not parse)")
    else:
        lines.append(f"  JSP files: {jsp_sec['jsp_files']}  with security hits: {jsp_sec['files_with_security_hits']}")
        lines.append("  -- Security tags --")
        for tag, cnt in jsp_sec.get("security_tag_counts", []):
            lines.append(f"    {tag:24} {cnt}")
        lines.append("  -- Examples --")
        for ex in jsp_sec.get("examples", []):
            lines.append(f"    {ex['file']}  tag={ex.get('tag')}  pattern_hits={ex.get('pattern_hits.security')}  attr={ex.get('attr')}")
    lines.append("")

    lines.append(f"== Traces ==  total={trace_total}")
    for s in trace_samples:
        lines.append(f"  {s['id']}")
        lines.append(f"    route={s['route']}  screen={s['screen']}  conf={s['confidence']}")
        lines.append(f"    path={s['path']}")
        lines.append(f"    tables={s['tables']} crud={s['crud_summary']}")
    lines.append("")

    dest.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    project = sys.argv[1] if len(sys.argv) > 1 else "ct-hr-storm"
    out_path = ROOT / "projects" / project / "output" / "step04_output.json"
    if not out_path.exists():
        print(f"Step04 output not found: {out_path}")
        sys.exit(1)

    data = load_step04(out_path)
    report_path = ROOT / "projects" / project / "output" / "step04_summary.txt"
    write_report(project, data, report_path)
    print(f"Wrote summary: {report_path}")
    write_report(project, data, report_path)
    print(f"Wrote summary: {report_path}")
