from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from domain.java_details import JavaClass, JavaDetails, JavaMethod
from domain.step02_output import Step02AstExtractorOutput
from steps.step02.source_inventory_query import SourceInventoryQuery
from steps.step04.models import Entity, Relation


class ActionLinker:
    """Link Routes to Java methods that handle them using Step02 inventory query."""

    def _index_java(self, step02: Step02AstExtractorOutput) -> Dict[str, Tuple[JavaDetails, JavaClass]]:
        index: Dict[str, Tuple[JavaDetails, JavaClass]] = {}
        java_files = SourceInventoryQuery(step02.source_inventory).files().detail_type("java").execute().items
        for f in java_files:
            details = f.details
            if not isinstance(details, JavaDetails):
                continue
            for jc in details.classes:
                fqn = f"{jc.package_name}.{jc.class_name}" if jc.package_name else jc.class_name
                index.setdefault(jc.class_name, (details, jc))
                index.setdefault(fqn, (details, jc))
        return index

    def link_routes_to_methods(self, routes: Dict[str, Entity], step02: Step02AstExtractorOutput) -> Tuple[Dict[str, Entity], List[Relation]]:
        method_entities: Dict[str, Entity] = {}
        relations: List[Relation] = []

        class_index = self._index_java(step02)
        seen_rel_ids = set()

        for route in routes.values():
            attrs = route.attributes or {}
            action_class_name: Optional[str] = attrs.get("action_class") or attrs.get("action")
            method_name: Optional[str] = attrs.get("method")
            framework = (attrs.get("framework") or "").lower()
            if not action_class_name:
                continue

            match = class_index.get(action_class_name) or class_index.get(action_class_name.split(".")[-1])
            if not match:
                continue
            details, jc = match

            # Resolve method including Struts wildcard patterns like "{1}"; for servlets choose doGet/doPost/service
            jm: Optional[JavaMethod] = None
            if framework in ("web_xml", "servlet_container", "servlet") or (method_name is None):
                jm = self._resolve_servlet_method(jc)
                if jm is None and method_name:  # fallback to explicit if provided
                    jm = self._resolve_method(jc, method_name)
            else:
                jm = self._resolve_method(jc, method_name or "execute")

            if jm is None:
                # last resort: pick a single non-trivial method
                jm = self._select_fallback_method(jc)
                if jm is None:
                    continue

            fqn = f"{jc.package_name}.{jc.class_name}" if jc.package_name else jc.class_name
            method_id = f"method_{fqn}#{jm.name}"
            if method_id not in method_entities:
                # Find a representative file path from the java file inventory
                file_path = None
                java_files = SourceInventoryQuery(step02.source_inventory).files().detail_type("java").execute().items
                for f in java_files:
                    if isinstance(f.details, JavaDetails):
                        for c2 in f.details.classes:
                            if c2 is jc:
                                file_path = f.path
                                break
                        if file_path:
                            break
                method_entities[method_id] = Entity(
                    id=method_id,
                    type="JavaMethod",
                    name=f"{jc.class_name}#{jm.name}",
                    attributes={
                        "package": jc.package_name,
                        "class": jc.class_name,
                        "method": jm.name,
                    },
                    source_refs=[{"file": file_path}] if file_path else [],
                )
            rel_id = f"rel_{route.id}->handlesRoute:{method_id}"
            if rel_id in seen_rel_ids:
                continue
            seen_rel_ids.add(rel_id)
            relations.append(
                Relation(
                    id=rel_id,
                    from_id=route.id,
                    to_id=method_id,
                    type="handlesRoute",
                    confidence=0.9,
                    rationale="Matched action/servlet class and method from Step02 JavaDetails",
                )
            )
        return method_entities, relations

    @staticmethod
    def _find_method(java_class: JavaClass, name: str) -> Optional[JavaMethod]:
        for m in java_class.methods:
            if m.name == name:
                return m
        return None

    def _select_fallback_method(self, java_class: JavaClass) -> Optional[JavaMethod]:
        """Choose a likely handler method when explicit resolution fails.
        Heuristics:
        - prefer 'execute'
        - then known verbs common in actions (incl. 'excel', 'process', 'run', 'view', 'export')
        - if still none, choose a single non-trivial method if unique (exclude getters/setters/is/to/hash/equals/compare/clone/main/saveCriteria)
        """
        # 1) execute
        jm = self._find_method(java_class, "execute")
        if jm:
            return jm
        # 2) common verbs
        candidates = (
            "display", "read", "list", "show", "index", "add", "update", "delete",
            "excel", "search", "process", "run", "view", "export", "print", "report", "download",
        )
        for name in candidates:
            jm = self._find_method(java_class, name)
            if jm:
                return jm
        # 3) a single non-trivial method

        def is_trivial(n: str) -> bool:
            return n.startswith(("get", "set", "is", "to", "hash", "equals", "compare", "clone", "main")) or n == "saveCriteria"

        non_trivial = [m for m in java_class.methods if not is_trivial(m.name)]
        if len(non_trivial) == 1:
            return non_trivial[0]
        return None

    def _resolve_method(self, java_class: JavaClass, method_name: str) -> Optional[JavaMethod]:
        """Resolve the concrete Java method for a route. If the mapping uses a wildcard
        like "{1}", choose a likely handler method.
        """
        # Direct match first
        jm = self._find_method(java_class, method_name)
        if jm:
            return jm
        # If explicit method not found, try execute
        if method_name != "execute":
            jm = self._find_method(java_class, "execute")
            if jm:
                return jm
        # Handle Struts patterns like "{1}", "{2}", etc. -> try common verbs
        if "{" in (method_name or ""):
            jm = self._select_fallback_method(java_class)
            if jm:
                return jm
        return None

    def _resolve_servlet_method(self, java_class: JavaClass) -> Optional[JavaMethod]:
        """Resolve typical servlet entry methods in order: service, doGet, doPost."""
        for name in ("service", "doGet", "doPost"):
            jm = self._find_method(java_class, name)
            if jm:
                return jm
        return None
