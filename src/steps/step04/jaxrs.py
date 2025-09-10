from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple, Union

from domain.java_details import JavaAnnotation, JavaClass, JavaDetails, JavaMethod
from domain.step02_output import Step02AstExtractorOutput
from steps.step02.source_inventory_query import SourceInventoryQuery
from steps.step04.models import Entity, Evidence, Relation
from steps.step04.plugins import LinkerPlugin

JAXRS_PATH_NAMES = {"javax.ws.rs.Path", "jakarta.ws.rs.Path"}
HTTP_VERB_ANN = {
    "javax.ws.rs.GET": "GET",
    "javax.ws.rs.POST": "POST",
    "javax.ws.rs.PUT": "PUT",
    "javax.ws.rs.DELETE": "DELETE",
    "javax.ws.rs.HEAD": "HEAD",
    "javax.ws.rs.OPTIONS": "OPTIONS",
    "javax.ws.rs.PATCH": "PATCH",
    "jakarta.ws.rs.GET": "GET",
    "jakarta.ws.rs.POST": "POST",
    "jakarta.ws.rs.PUT": "PUT",
    "jakarta.ws.rs.DELETE": "DELETE",
    "jakarta.ws.rs.HEAD": "HEAD",
    "jakarta.ws.rs.OPTIONS": "OPTIONS",
    "jakarta.ws.rs.PATCH": "PATCH",
}
PRODUCES_ANN = {"javax.ws.rs.Produces", "jakarta.ws.rs.Produces"}
CONSUMES_ANN = {"javax.ws.rs.Consumes", "jakarta.ws.rs.Consumes"}
APPLICATION_PATH_ANN = {"javax.ws.rs.ApplicationPath", "jakarta.ws.rs.ApplicationPath"}


class JaxRsLinkerPlugin(LinkerPlugin):
    """Build JAX-RS endpoint Route entities and link them to Java methods.

    - Prefers Step02 rest_endpoints mappings; if absent per file, falls back to
      consuming annotations for only that file/classes.
    - Also consumes CodeMappings of mapping_type='rest_endpoint' when present.
    - Creates one Route entity per concrete HTTP endpoint.
    - Links Route -handlesRoute-> JavaMethod.
    - Optionally adds mountedUnder relation to parent servlet route when found.
    """

    def apply(
        self,
        routes: Dict[str, Entity],
        step02: Step02AstExtractorOutput,
    ) -> Tuple[Dict[str, Entity], List[Relation], Dict[str, Entity]]:
        new_routes: Dict[str, Entity] = {}
        new_methods: Dict[str, Entity] = {}
        new_relations: List[Relation] = []

        # Find servlet mounts (e.g., /rest/*) among existing routes
        servlet_mounts = self._find_servlet_mounts(routes)
        app_paths = self._find_application_paths(step02)

        # Scan Java files; use rest_endpoints if present, otherwise per-file annotation fallback
        java_files = SourceInventoryQuery(step02.source_inventory).files().detail_type("java").execute().items
        for f in java_files:
            details = f.details
            if not isinstance(details, JavaDetails):
                continue

            produced_for_file = 0
            # 1) Prefer Step02-provided REST endpoints for this file
            if details.rest_endpoints:
                for ep in details.rest_endpoints:
                    # Flexible field names depending on extractor
                    path = ep.get("path") or ep.get("full_path")
                    class_path = ep.get("class_path")
                    method_path = ep.get("method_path")
                    verb = (ep.get("http_method") or ep.get("verb") or "").upper()
                    produces = ep.get("produces") or []
                    consumes = ep.get("consumes") or []
                    controller_fqn = ep.get("controller") or ep.get("class") or ep.get("class_fqn")
                    method_name = ep.get("method_name") or ep.get("java_method") or ep.get("method")

                    base = self._select_base(servlet_mounts, app_paths)
                    if not path:
                        path = self._compose_path(base, class_path, method_path)
                    else:
                        path = self._norm_path(path)

                    if not path or not verb:
                        continue

                    route_id = self._route_id(path, verb)
                    if route_id not in routes and route_id not in new_routes:
                        new_routes[route_id] = Entity(
                            id=route_id,
                            type="Route",
                            name=f"{verb} {path}",
                            attributes={
                                "framework": "jax-rs",
                                "http_method": verb,
                                "path": path,
                                "path_template": path,
                                "produces": produces,
                                "consumes": consumes,
                                "controller": controller_fqn,
                                "method": method_name,
                            },
                            source_refs=[{"file": f.path}],
                        )
                        produced_for_file += 1

                    # Link to Java method entity when controller+method known
                    if controller_fqn and method_name:
                        method_id = f"method_{controller_fqn}#{method_name}"
                        if method_id not in new_methods:
                            # Split package/class for attributes
                            pkg, cls = self._split_fqn(controller_fqn)
                            new_methods[method_id] = Entity(
                                id=method_id,
                                type="JavaMethod",
                                name=f"{cls}#{method_name}",
                                attributes={
                                    "package": pkg,
                                    "class": cls,
                                    "method": method_name,
                                },
                                source_refs=[{"file": f.path}],
                            )
                        new_relations.append(
                            Relation(
                                id=f"rel_{route_id}->handlesRoute:{method_id}",
                                from_id=route_id,
                                to_id=method_id,
                                type="handlesRoute",
                                confidence=0.9,
                                evidence=[Evidence(file=f.path)] if getattr(f, 'path', None) else [],
                                rationale="Step02 rest_endpoints mapping",
                            )
                        )

                    parent = servlet_mounts.get("/rest/*") or self._match_mount_for_path(servlet_mounts, path)
                    if parent:
                        new_relations.append(
                            Relation(
                                id=f"rel_{route_id}->mountedUnder:{parent.id}",
                                from_id=route_id,
                                to_id=parent.id,
                                type="mountedUnder",
                                confidence=0.8,
                                evidence=[Evidence(file=f.path)] if getattr(f, 'path', None) else [],
                                rationale="web.xml servlet url-pattern mount",
                            )
                        )

            # 1b) Also consume CodeMappings with mapping_type='rest_endpoint'
            try:
                for cm in getattr(details, "code_mappings", []) or []:
                    mapping_type = getattr(cm, "mapping_type", "") or cm.__dict__.get("mapping_type")
                    framework = (getattr(cm, "framework", "") or "").lower()
                    if mapping_type != "rest_endpoint" or (framework and framework not in ("jaxrs", "jax-rs")):
                        continue

                    path = getattr(cm, "from_reference", "") or cm.__dict__.get("from_reference", "")
                    attrs = getattr(cm, "attributes", {}) or {}
                    verb = (attrs.get("http_method", "") or "").upper()
                    produces_val = attrs.get("produces")
                    consumes_val = attrs.get("consumes")
                    produces = [p for p in (produces_val.split(",") if isinstance(produces_val, str) else (produces_val or [])) if p]
                    consumes = [c for c in (consumes_val.split(",") if isinstance(consumes_val, str) else (consumes_val or [])) if c]

                    to_ref = getattr(cm, "to_reference", "") or cm.__dict__.get("to_reference", "")
                    controller_fqn = None
                    method_name = None
                    if to_ref:
                        # Expect format like package.Class.method; fall back if no method
                        if "." in to_ref:
                            controller_fqn, method_name = to_ref.rsplit(".", 1)
                        else:
                            controller_fqn = to_ref

                    base = self._select_base(servlet_mounts, app_paths)
                    if not path:
                        # Cannot compose without class/method paths here; skip
                        continue
                    path = self._norm_path(path)
                    if not verb:
                        continue

                    route_id = self._route_id(path, verb)
                    if route_id not in routes and route_id not in new_routes:
                        new_routes[route_id] = Entity(
                            id=route_id,
                            type="Route",
                            name=f"{verb} {path}",
                            attributes={
                                "framework": "jax-rs",
                                "http_method": verb,
                                "path": path,
                                "path_template": path,
                                "produces": produces,
                                "consumes": consumes,
                                "controller": controller_fqn,
                                "method": method_name,
                            },
                            source_refs=[{"file": f.path}],
                        )
                        produced_for_file += 1

                    if controller_fqn and method_name:
                        method_id = f"method_{controller_fqn}#{method_name}"
                        if method_id not in new_methods:
                            pkg, cls = self._split_fqn(controller_fqn)
                            new_methods[method_id] = Entity(
                                id=method_id,
                                type="JavaMethod",
                                name=f"{cls}#{method_name}",
                                attributes={
                                    "package": pkg,
                                    "class": cls,
                                    "method": method_name,
                                },
                                source_refs=[{"file": f.path}],
                            )
                        new_relations.append(
                            Relation(
                                id=f"rel_{route_id}->handlesRoute:{method_id}",
                                from_id=route_id,
                                to_id=method_id,
                                type="handlesRoute",
                                confidence=0.9,
                                rationale="Step02 code_mappings rest_endpoint",
                                evidence=[Evidence(file=f.path)] if getattr(f, 'path', None) else [],
                            )
                        )

                    parent = servlet_mounts.get("/rest/*") or self._match_mount_for_path(servlet_mounts, path)
                    if parent:
                        new_relations.append(
                            Relation(
                                id=f"rel_{route_id}->mountedUnder:{parent.id}",
                                from_id=route_id,
                                to_id=parent.id,
                                type="mountedUnder",
                                confidence=0.8,
                                rationale="web.xml servlet url-pattern mount",
                                evidence=[Evidence(file=f.path)] if getattr(f, 'path', None) else [],
                            )
                        )
            except Exception:  # pylint: disable=broad-except
                # Be robust to unexpected mapping shapes
                pass

            # 2) If nothing produced for this file, fall back to annotations for its classes only
            if produced_for_file == 0:
                for jc in details.classes:
                    class_path = self._get_annotation_value(jc.annotations, JAXRS_PATH_NAMES)
                    class_produces = self._as_list(self._get_annotation_value(jc.annotations, PRODUCES_ANN))
                    class_consumes = self._as_list(self._get_annotation_value(jc.annotations, CONSUMES_ANN))

                    for jm in jc.methods:
                        verb = self._detect_http_verb(jm.annotations)
                        if not verb:
                            continue
                        method_path = self._get_annotation_value(jm.annotations, JAXRS_PATH_NAMES)
                        produces = self._as_list(self._get_annotation_value(jm.annotations, PRODUCES_ANN)) or class_produces
                        consumes = self._as_list(self._get_annotation_value(jm.annotations, CONSUMES_ANN)) or class_consumes

                        base = self._select_base(servlet_mounts, app_paths)
                        full_path = self._compose_path(base, class_path, method_path)
                        if not full_path:
                            continue

                        route_id = self._route_id(full_path, verb)
                        if route_id in routes or route_id in new_routes:
                            continue
                        new_routes[route_id] = Entity(
                            id=route_id,
                            type="Route",
                            name=f"{verb} {full_path}",
                            attributes={
                                "framework": "jax-rs",
                                "http_method": verb,
                                "path": full_path,
                                "path_template": full_path,
                                "produces": produces,
                                "consumes": consumes,
                                "controller": f"{jc.package_name}.{jc.class_name}" if jc.package_name else jc.class_name,
                                "method": jm.name,
                            },
                            source_refs=[{"file": f.path}],
                        )

                        method_id = f"method_{jc.package_name}.{jc.class_name}#{jm.name}" if jc.package_name else f"method_{jc.class_name}#{jm.name}"
                        if method_id not in new_methods:
                            new_methods[method_id] = Entity(
                                id=method_id,
                                type="JavaMethod",
                                name=f"{jc.class_name}#{jm.name}",
                                attributes={
                                    "package": jc.package_name,
                                    "class": jc.class_name,
                                    "method": jm.name,
                                },
                                source_refs=[{"file": f.path}],
                            )

                        new_relations.append(
                            Relation(
                                id=f"rel_{route_id}->handlesRoute:{method_id}",
                                from_id=route_id,
                                to_id=method_id,
                                type="handlesRoute",
                                confidence=0.9,
                                rationale="JAX-RS annotations (@Path + HTTP verb)",
                                evidence=[Evidence(file=f.path)] if getattr(f, 'path', None) else [],
                            )
                        )

                        parent = servlet_mounts.get("/rest/*") or self._match_mount_for_path(servlet_mounts, full_path)
                        if parent:
                            new_relations.append(
                                Relation(
                                    id=f"rel_{route_id}->mountedUnder:{parent.id}",
                                    from_id=route_id,
                                    to_id=parent.id,
                                    type="mountedUnder",
                                    confidence=0.8,
                                    rationale="web.xml servlet url-pattern mount",
                                    evidence=[Evidence(file=f.path)] if getattr(f, 'path', None) else [],
                                )
                            )

        return new_routes, new_relations, new_methods

    # ---------- helpers ----------
    def _find_servlet_mounts(self, routes: Dict[str, Entity]) -> Dict[str, Entity]:
        mounts: Dict[str, Entity] = {}
        for r in routes.values():
            attrs = r.attributes or {}
            action_val = attrs.get("action")
            if isinstance(action_val, str) and (attrs.get("framework") in ("servlet", "web_xml", "servlet_container")):
                action: str = action_val
                if action.endswith("/*"):
                    mounts[action] = r
        return mounts

    def _find_application_paths(self, step02: Step02AstExtractorOutput) -> List[str]:
        paths: List[str] = []
        java_files = SourceInventoryQuery(step02.source_inventory).files().detail_type("java").execute().items
        for f in java_files:
            details = f.details
            if not isinstance(details, JavaDetails):
                continue
            for jc in details.classes:
                val = self._get_annotation_value(jc.annotations, APPLICATION_PATH_ANN)
                if val:
                    paths.append(val)
        return paths

    def _get_annotation_value(self, anns: List[JavaAnnotation], names: set) -> Optional[str]:
        for ann in anns:
            if ann.name in names:
                v = ann.attributes.get("value")
                if isinstance(v, list) and v:
                    return str(v[0])
                if isinstance(v, str):
                    return v
                # Some parsers might store single unnamed attribute under key '"
                # Fallback: try first attribute value
                if ann.attributes:
                    first = next(iter(ann.attributes.values()))
                    if isinstance(first, list) and first:
                        return str(first[0])
                    if isinstance(first, str):
                        return first
        return None

    def _as_list(self, v: Optional[Union[str, List[str]]]) -> List[str]:
        if not v:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        return [str(v)]

    def _select_base(self, mounts: Dict[str, Entity], app_paths: List[str]) -> str:
        # Prefer servlet mount if present (e.g., /rest/*)
        if mounts:
            # Choose the shortest mount (most generic) and trim /*
            m = sorted(mounts.keys(), key=len)[0]
            return m[:-2] if m.endswith("/*") else m
        # Else use @ApplicationPath if present
        if app_paths:
            base = sorted(app_paths, key=len)[0]
            return self._norm_path(base)
        return ""

    def _match_mount_for_path(self, mounts: Dict[str, Entity], full_path: str) -> Optional[Entity]:
        for pat, ent in mounts.items():
            base = pat[:-2] if pat.endswith("/*") else pat
            if full_path.startswith(base.rstrip("/")):
                return ent
        return None

    def _compose_path(self, base: Optional[str], class_path: Optional[str], method_path: Optional[str]) -> str:
        parts = [p for p in [base, class_path, method_path] if p]
        if not parts:
            return ""
        path = "/".join([self._strip_slashes(p) for p in parts])
        path = "/" + path if not path.startswith("/") else path
        while "//" in path:
            path = path.replace("//", "/")
        return path

    @staticmethod
    def _strip_slashes(p: str) -> str:
        return p.strip().strip("/")

    @staticmethod
    def _norm_path(p: str) -> str:
        s = "/" + JaxRsLinkerPlugin._strip_slashes(p)
        while "//" in s:
            s = s.replace("//", "/")
        return s

    @staticmethod
    def _detect_http_verb(anns: List[JavaAnnotation]) -> Optional[str]:
        for ann in anns:
            if ann.name in HTTP_VERB_ANN:
                return HTTP_VERB_ANN[ann.name]
        return None

    @staticmethod
    def _route_id(full_path: str, verb: str) -> str:
        # Stable, filesystem-friendly id: replace non-alnum with underscore
        safe = "".join(ch if ch.isalnum() else "_" for ch in full_path)
        safe = safe.strip("_")
        return f"route_{safe}_{verb}"

    @staticmethod
    def _split_fqn(fqn: str) -> Tuple[Optional[str], str]:
        if not fqn:
            return None, ""
        if "." not in fqn:
            return None, fqn
        idx = fqn.rfind(".")
        return fqn[:idx], fqn[idx+1:]
