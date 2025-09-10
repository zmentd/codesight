from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from steps.step04.models import Entity, Evidence, Relation, Trace


class TraceBuilder:
    """Build end-to-end traces from entities and relations.

    Builds paths: JSP <-renders- Route -handlesRoute-> JavaMethod -(readsFrom/writesTo)-> Table
    Aggregates CRUD summary per trace.
    """

    READ = {"readsFrom"}
    WRITE = {"writesTo"}
    DELETE = {"deletesFrom"}
    JSP_EDGE_TYPES = ("includesView", "embedsView", "redirectsTo")

    def _expand_jsp_chain(
        self,
        start_jsp_id: str,
        by_type_from: Dict[Tuple[str, str], List[Relation]],
        max_hops: int = 5,
    ) -> List[str]:
        """Follow JSP->JSP edges starting from start_jsp_id and return an ordered list of subsequent JSP ids.
        - Follows only includesView/embedsView/redirectsTo
        - Deterministic ordering by relation type priority (includes, embeds, redirects) then by to_id
        - Cycle protected and hop-limited
        """
        chain: List[str] = []
        visited: Set[str] = {start_jsp_id}
        frontier: List[str] = [start_jsp_id]
        hops = 0
        while frontier and hops < max_hops:
            curr = frontier.pop(0)
            hops += 1
            # Gather outgoing JSP edges in a stable order
            outgoing: List[Relation] = []
            for t in self.JSP_EDGE_TYPES:
                rels = by_type_from.get((t, curr), [])
                if rels:
                    # sort for determinism by target id
                    outgoing.extend(sorted(rels, key=lambda r: r.to_id))
            for rel in outgoing:
                to_id = rel.to_id
                if to_id in visited:
                    continue
                visited.add(to_id)
                chain.append(to_id)
                frontier.append(to_id)
        return chain

    def _collect_crud_for_node(self, node_id: str, by_from: Dict[str, List[Relation]]) -> Tuple[List[str], List[str], List[str]]:
        reads: List[str] = []
        writes: List[str] = []
        deletes: List[str] = []
        for rel in by_from.get(node_id, []):
            if rel.to_id.startswith("table_"):
                tname = rel.to_id[len("table_"):]
                if rel.type in self.READ:
                    reads.append(tname)
                elif rel.type in self.WRITE:
                    writes.append(tname)
                elif rel.type in self.DELETE:
                    deletes.append(tname)
        return reads, writes, deletes

    def build_traces(self, entities: Dict[str, Entity], relations: List[Relation]) -> List[Trace]:
        # Index relations
        by_from: Dict[str, List[Relation]] = defaultdict(list)
        by_type_from: Dict[Tuple[str, str], List[Relation]] = defaultdict(list)
        for r in relations:
            by_from[r.from_id].append(r)
            by_type_from[(r.type, r.from_id)].append(r)

        traces: List[Trace] = []

        # Identify routes
        route_ids = [eid for eid, e in entities.items() if e.type == "Route"]
        for rid in route_ids:
            # Find renders to JSP
            renders = by_type_from.get(("renders", rid), [])
            if not renders:
                continue
            # Choose first JSP
            jsp_rel = sorted(renders, key=lambda r: r.to_id)[0]
            screen_id = jsp_rel.to_id

            # Expand JSP chain (include/iframe/redirect)
            jsp_chain = self._expand_jsp_chain(screen_id, by_type_from)

            # Find handler methods
            handlers = by_type_from.get(("handlesRoute", rid), [])
            jsp_ids = [screen_id] + jsp_chain

            if not handlers:
                # Create a trace with route+screen(+chain) and include JSP-level CRUD
                reads: List[str] = []
                writes: List[str] = []
                deletes: List[str] = []
                for jsp_id in jsp_ids:
                    rds, wrs, dls = self._collect_crud_for_node(jsp_id, by_from)
                    reads.extend(rds)
                    writes.extend(wrs)
                    deletes.extend(dls)
                crud: Dict[str, List[str]] = {}
                if reads:
                    crud["reads"] = sorted(list(set(reads)))
                if writes:
                    crud["writes"] = sorted(list(set(writes)))
                if deletes:
                    crud["deletes"] = sorted(list(set(deletes)))
                tables = sorted(list(set(reads + writes + deletes)))

                path = [rid, screen_id] + jsp_chain
                tr = Trace(
                    id=f"trace_{rid}",
                    screen=screen_id,
                    route=rid,
                    path=path,
                    crud_summary=crud,
                    tables=tables,
                    evidence=[],
                    confidence=0.6,
                )
                traces.append(tr)
                continue

            # For each handler, collect DB ops from method and JSPs
            for h in handlers:
                method_id = h.to_id
                reads_m, writes_m, deletes_m = self._collect_crud_for_node(method_id, by_from)

                reads_j: List[str] = []
                writes_j: List[str] = []
                deletes_j: List[str] = []
                for jsp_id in jsp_ids:
                    rds, wrs, dls = self._collect_crud_for_node(jsp_id, by_from)
                    reads_j.extend(rds)
                    writes_j.extend(wrs)
                    deletes_j.extend(dls)

                reads = reads_m + reads_j
                writes = writes_m + writes_j
                deletes = deletes_m + deletes_j

                crud = {}
                if reads:
                    crud["reads"] = sorted(list(set(reads)))
                if writes:
                    crud["writes"] = sorted(list(set(writes)))
                if deletes:
                    crud["deletes"] = sorted(list(set(deletes)))

                path = [rid, method_id, screen_id] + jsp_chain
                tr = Trace(
                    id=f"trace_{rid}->{method_id}",
                    screen=screen_id,
                    route=rid,
                    path=path,
                    crud_summary=crud,
                    tables=sorted(list(set(reads + writes + deletes))),
                    evidence=[],
                    confidence=0.7 if (reads or writes or deletes) else 0.65,
                )
                traces.append(tr)

        return traces
