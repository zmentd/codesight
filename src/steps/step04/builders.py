from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from domain.config_details import CodeMapping, ConfigurationDetails, DeterministicForward
from domain.java_details import JavaClass, JavaDetails, JavaMethod
from domain.jsp_details import JspDetails
from domain.sql_details import DatabaseObjectType, SQLDetails, SqlOperationType, TableOperation
from domain.step02_output import Step02AstExtractorOutput
from steps.step02.source_inventory_query import SourceInventoryQuery

# Use EvidenceUtils
from steps.step04.evidence import EvidenceUtils
from steps.step04.models import Entity as Step04Entity
from steps.step04.models import Evidence
from steps.step04.models import Relation as Step04Relation


@dataclass
class Route:
    namespace: Optional[str]
    action: str
    method: Optional[str]
    result_jsp: Optional[str]


class RouteBuilder:
    """Build Route entities and relations from Step02 ConfigurationDetails."""

    @staticmethod
    def _normalize_namespace(ns: Optional[str]) -> Optional[str]:
        if not ns:
            return None
        # Remove wildcards and trim slashes/spaces
        ns_clean = ns.strip().replace("*", "")
        ns_clean = ns_clean.strip()
        ns_clean = ns_clean.strip("/")
        return ns_clean or None

    @staticmethod
    def _normalize_action(action: str) -> str:
        a = (action or "").strip()
        # Remove any leading wildcard or slashes patterns like "/*", "//*"
        while a.startswith("/*") or a.startswith("//") or a.startswith("/") or a.startswith("*"):
            if a.startswith("/*"):
                a = a[2:]
            elif a.startswith("//"):
                a = a[2:]
            elif a.startswith("/") or a.startswith("*"):
                a = a[1:]
        return a

    @staticmethod
    def _clean_method(method: Optional[str]) -> Optional[str]:
        """Return a cleaned method name or None if unresolved/placeholder.

        Treat values like '{1}', '{actionMethod}', or any string containing braces as unresolved.
        """
        if method is None:
            return None
        m = str(method).strip()
        if not m:
            return None
        # Placeholder patterns like '{1}' or any value containing braces should be treated as unresolved
        if re.match(r"^\{\s*\d+\s*\}$", m) or ("{" in m or "}" in m):
            return None
        return m

    def build_routes(self, step02: Step02AstExtractorOutput) -> Dict[str, Step04Entity]:
        routes: Dict[str, Step04Entity] = {}

        for source in step02.source_inventory.source_locations:
            for sub in source.subdomains:
                for file in sub.file_inventory:
                    if not file.details or not isinstance(file.details, ConfigurationDetails):
                        continue
                    cfg: ConfigurationDetails = file.details

                    # Struts action mappings
                    if cfg.is_struts_config():
                        # Action mappings
                        for m in cfg.get_action_mappings():
                            # Use namespace if provided on the mapping (some struts configs set namespace per-action)
                            namespace = m.attributes.get("namespace") if getattr(m, 'attributes', None) else None
                            raw_action = m.from_reference
                            action = self._normalize_action(raw_action)
                            method = m.attributes.get("method") if m.attributes else None
                            # Clean method placeholders like '{1}'
                            final_method = "execute" if method is None else self._clean_method(method)
                            result_path = None
                            if m.forwards:
                                # pick primary 'success' or first
                                primary = next((f for f in m.forwards if f.name.lower() == "success"), m.forwards[0])
                                result_path = primary.path
                            ns_clean = self._normalize_namespace(namespace)
                            ns_id = (ns_clean or "").replace("/", "_") if ns_clean else None
                            action_id = action.replace("/", "_").replace("*", "STAR")
                            route_id = f"route_{ns_id}_{action_id}" if ns_id else f"route_{action_id}"
                            display_ns = f"/{ns_clean}" if ns_clean else ""
                            routes[route_id] = Step04Entity(
                                id=route_id,
                                type="Route",
                                name=f"{display_ns}/{action}",
                                attributes={
                                    "framework": cfg.detected_framework,
                                    "namespace": display_ns or None,
                                    "action": action,
                                    "action_raw": raw_action,
                                    "method_raw": method,
                                    "action_class": getattr(m, 'to_reference', None),
                                    "method": final_method,
                                    "result_jsp": result_path,
                                },
                                source_refs=[{"file": file.path}],
                            )

                        # Grouped mappings with namespace
                        for group in [m for m in cfg.code_mappings if hasattr(m, 'group_name')]:
                            try:
                                namespace = getattr(group, 'namespace', None)
                                ns_clean = self._normalize_namespace(namespace)
                                ns_id = (ns_clean or "").replace("/", "_") if ns_clean else None
                                display_ns = f"/{ns_clean}" if ns_clean else ""
                                for cm in getattr(group, 'mappings', []) or []:
                                    if not isinstance(cm, CodeMapping) or cm.mapping_type != "action":
                                        continue
                                    raw_action = cm.from_reference
                                    action = self._normalize_action(raw_action)
                                    method = cm.attributes.get("method") if cm.attributes else None
                                    # Clean method placeholders like '{1}'
                                    final_method = "execute" if method is None else self._clean_method(method)
                                    result_path = None
                                    if cm.forwards:
                                        primary = next((f for f in cm.forwards if f.name.lower() == "success"), cm.forwards[0])
                                        result_path = primary.path
                                    action_id = action.replace("/", "_").replace("*", "STAR")
                                    route_id = f"route_{ns_id}_{action_id}" if ns_id else f"route_{action_id}"
                                    routes[route_id] = Step04Entity(
                                        id=route_id,
                                        type="Route",
                                        name=f"{display_ns}/{action}",
                                        attributes={
                                            "framework": cfg.detected_framework,
                                            "namespace": display_ns or None,
                                            "action": action,
                                            "action_raw": raw_action,
                                            "method_raw": method,
                                            "action_class": getattr(cm, 'to_reference', None),
                                            "method": final_method,
                                            "result_jsp": result_path,
                                        },
                                        source_refs=[{"file": file.path}],
                                    )
                            except Exception:  # pylint: disable=broad-except
                                continue

                    # Servlet mappings from web.xml
                    servlet_mappings = cfg.get_servlet_mappings()
                    if servlet_mappings:
                        for sm in servlet_mappings:
                            try:
                                url_pattern = sm.from_reference or ""
                                servlet_class = sm.to_reference or ""
                                if not url_pattern or not servlet_class:
                                    continue
                                # Keep display name as the url-pattern; build a stable id
                                action = url_pattern.strip()
                                action_id = action.replace("/", "_").replace("*", "STAR")
                                route_id = f"route_{action_id}"
                                # Do not assume method; linker will resolve doGet/doPost/service
                                routes[route_id] = Step04Entity(
                                    id=route_id,
                                    type="Route",
                                    name=action,
                                    attributes={
                                        "framework": cfg.detected_framework or "web_xml",
                                        "namespace": None,
                                        "action": action,
                                        "action_class": servlet_class,
                                        "method": None,
                                        "result_jsp": None,
                                    },
                                    source_refs=[{"file": file.path}],
                                )
                            except Exception:  # pylint: disable=broad-except
                                continue
        return routes


class DataAccessBuilder:
    """Build data-access relations from JavaDetails and SQLDetails already parsed in Step02."""

    READ_OPS = {SqlOperationType.SELECT}
    WRITE_OPS = {SqlOperationType.INSERT, SqlOperationType.UPDATE}
    DELETE_OPS = {SqlOperationType.DELETE}

    def __init__(self) -> None:
        # Map of normalized procedure name -> list of table operations aggregated from Step02 SQLDetails
        self.proc_table_ops: Dict[str, List[TableOperation]] = {}
        # Index of known DB objects from Step02 for precision filtering
        self._known_tables_lc: set[str] = set()
        self._known_procs_lc: set[str] = set()
        # Tie-breaker indexes: unqualified name -> set of distinct (db,schema,name)
        self._table_by_unqualified: Dict[str, set[str]] = {}
        self._proc_by_unqualified: Dict[str, set[str]] = {}
        # Evidence utils instance
        self.evidence = EvidenceUtils()

    @staticmethod
    def _normalize_proc_name(schema: Optional[str], name: str) -> str:
        base = name.strip() if name else ""
        if schema and schema.strip():
            return f"{schema.strip()}.{base}"
        return base

    @staticmethod
    def _normalize_object_token(name: Optional[str]) -> str:
        """Normalize object token to compare against indexes: strip [], schema, lower-case."""
        if not name:
            return ""
        n = name.strip().strip(';').strip()
        n = n.replace('[', '').replace(']', '')
        # Remove trailing parentheses if any
        n = re.sub(r"\(.*$", "", n)
        # Use unqualified name for table index comparisons
        if '.' in n:
            n = n.split('.')[-1]
        return n.lower()

    def build_procedure_map(self, step02: Step02AstExtractorOutput) -> None:
        """Populate self.proc_table_ops from Step02 SQLDetails and index known tables/procs for filtering.
        Strategy priority:
        1) If SQLDetails.database_objects contains PROCEDUREs, attribute file-level table_operations to each procedure (best-effort aggregation across files).
        2) Else, detect procedure declarations from SQLDetails.statements. If the file declares exactly one procedure, attribute its table_operations to that procedure.
        Skip multi-procedure files when we cannot disambiguate per-procedure operations.
        """
        self.proc_table_ops.clear()
        self._known_tables_lc.clear()
        self._known_procs_lc.clear()
        self._table_by_unqualified.clear()
        self._proc_by_unqualified.clear()
        sql_files = SourceInventoryQuery(step02.source_inventory).files().detail_type("sql").execute().items
        for f in sql_files:
            if not isinstance(f.details, SQLDetails):
                continue
            sql: SQLDetails = f.details

            # Index known DB objects for precision filtering and tie-breakers
            for obj in getattr(sql, 'database_objects', []) or []:
                obj_type = getattr(obj, 'object_type', None)
                obj_name = getattr(obj, 'object_name', None)
                schema_name = getattr(obj, 'schema_name', None)
                logical_db = getattr(obj, 'logical_database', None)
                unq = self._normalize_object_token(obj_name)
                if obj_type in (DatabaseObjectType.TABLE, DatabaseObjectType.VIEW) and obj_name:
                    self._known_tables_lc.add(unq)
                    key = f"{(logical_db or '').strip().lower()}::{(schema_name or '').strip().lower()}::{unq}"
                    self._table_by_unqualified.setdefault(unq, set()).add(key)
                elif obj_type == DatabaseObjectType.PROCEDURE and obj_name:
                    pn = unq
                    if pn:
                        self._known_procs_lc.add(pn)
                        if schema_name and str(schema_name).strip():
                            self._known_procs_lc.add(f"{str(schema_name).strip().lower()}.{pn}")
                        pkey = f"{(logical_db or '').strip().lower()}::{(schema_name or '').strip().lower()}::{pn}"
                        self._proc_by_unqualified.setdefault(pn, set()).add(pkey)

            ops_in_file = list(sql.table_operations or [])
            if not ops_in_file:
                continue

            proc_names: List[str] = []
            # First, try database_objects
            if sql.database_objects:
                for obj in sql.database_objects:
                    if obj.object_type == DatabaseObjectType.PROCEDURE and obj.object_name:
                        # Add both name and schema.name variants for robust lookup
                        name_only = obj.object_name.strip()
                        proc_names.append(name_only)
                        if obj.schema_name and obj.schema_name.strip():
                            proc_names.append(f"{obj.schema_name.strip()}.{name_only}")
            # Fallback: detect from statements via enums if present
            if not proc_names and sql.statements:
                stm_proc_names = []
                for s in sql.statements:
                    if s.object_type == DatabaseObjectType.PROCEDURE and s.object_name:
                        name_only = s.object_name.strip()
                        schema = (s.schema_name or "").strip() or None
                        stm_proc_names.append((schema, name_only))
                # If not found, use regex on statement_text
                if not stm_proc_names:
                    name_hits: List[tuple[Optional[str], str]] = []
                    pat = re.compile(r"\b(?:CREATE|ALTER)\s+(?:PROC|PROCEDURE)\s+(?:\[?([A-Za-z0-9_]+)\]?\.)?\[?([A-Za-z0-9_]+)\]?", re.IGNORECASE)
                    for s in sql.statements:
                        m = pat.search(s.statement_text or "")
                        if m:
                            schema = m.group(1)
                            name_only = m.group(2)
                            name_hits.append((schema, name_only))
                    # de-dup
                    unique = list({(schema or None, name) for schema, name in name_hits})
                else:
                    unique = list({(schema or None, name) for schema, name in stm_proc_names})

                # If any procedures detected in this file, attribute ops to all of them (best-effort)
                if len(unique) >= 1:
                    for schema, name_only in unique:
                        proc_names.append(name_only)
                        if schema:
                            proc_names.append(f"{schema}.{name_only}")

            if not proc_names:
                continue

            # Aggregate operations (union by table and op) for each identified proc name
            for pname in proc_names:
                if pname not in self.proc_table_ops:
                    self.proc_table_ops[pname] = []
                existing = {f"{op.operation.value}|{op.table_name}" for op in self.proc_table_ops[pname]}
                for t_op in ops_in_file:
                    key = f"{t_op.operation.value}|{t_op.table_name}"
                    if key not in existing:
                        self.proc_table_ops[pname].append(t_op)
                        existing.add(key)

    def _rel_type_for_op(self, op: SqlOperationType) -> str:
        if op in self.READ_OPS:
            return "readsFrom"
        if op in self.DELETE_OPS:
            return "deletesFrom"
        # default to write for INSERT/UPDATE and others
        return "writesTo"

    def build_method_table_edges(self, java: JavaDetails, source_file: Optional[str] = None) -> List[Step04Relation]:
        rels: List[Step04Relation] = []
        for cls in java.classes:
            for m in cls.methods:
                method_entity_id = f"method_{cls.package_name}.{cls.class_name}#{m.name}"
                # Inline SQL statements detected in Step02
                for stmt in m.sql_statements:
                    if stmt.object_name and stmt.statement_type in (self.READ_OPS | self.WRITE_OPS | self.DELETE_OPS):
                        table = stmt.object_name
                        op_type = stmt.statement_type
                        rel_type = self._rel_type_for_op(op_type)
                        rels.append(
                            Step04Relation(
                                id=f"rel_{method_entity_id}->{rel_type}:{table}",
                                from_id=method_entity_id,
                                to_id=f"table_{table}",
                                type=rel_type,
                                confidence=0.85,
                                evidence=[self.evidence.build_evidence_from_file(source_file)] if source_file else [],
                                rationale=f"Derived from inline SQL {op_type.value} on {table}",
                            )
                        )
                # Stored procedure calls -> expand to table operations via proc map when available
                for sp in m.sql_stored_procedures:
                    proc_norm = self._normalize_proc_name(sp.schema_name, sp.procedure_name)
                    # Always keep an invokesProcedure link for navigation
                    rels.append(
                        Step04Relation(
                            id=f"rel_{method_entity_id}->proc:{proc_norm}",
                            from_id=method_entity_id,
                            to_id=f"proc_{proc_norm}",
                            type="invokesProcedure",
                            confidence=0.8,
                            evidence=[self.evidence.build_evidence_from_file(source_file)] if source_file else [],
                            rationale="Detected stored procedure execution",
                        )
                    )
                    # Expand to table operations via proc map; allow duplicates across schemas/DBs (same-type)
                    found = self.proc_table_ops.get(proc_norm)
                    if not found and "." in proc_norm:
                        name_only = proc_norm.split(".", 1)[1]
                        found = self.proc_table_ops.get(name_only)
                    if not found:
                        found = self.proc_table_ops.get(sp.procedure_name)
                    if found:
                        for t_op in list(found):
                            rel_type = self._rel_type_for_op(t_op.operation)
                            rels.append(
                                Step04Relation(
                                    id=f"rel_{method_entity_id}->{rel_type}:{t_op.table_name}",
                                    from_id=method_entity_id,
                                    to_id=f"table_{t_op.table_name}",
                                    type=rel_type,
                                    confidence=0.8,
                                    evidence=[self.evidence.build_evidence_from_file(source_file)] if source_file else [],
                                    rationale=f"From stored procedure {proc_norm}",
                                )
                            )
        return rels

    def build_sql_file_table_edges(self, sql: SQLDetails) -> List[Step04Relation]:
        rels: List[Step04Relation] = []
        for t_op in sql.table_operations:
            rel_type = self._rel_type_for_op(t_op.operation)
            # We don't know the Java method here; create relations at SQLStatement level
            sql_entity = f"sqlfile_{sql.file_path}"
            rels.append(
                Step04Relation(
                    id=f"rel_{sql_entity}->{rel_type}:{t_op.table_name}",
                    from_id=sql_entity,
                    to_id=f"table_{t_op.table_name}",
                    type=rel_type,
                    confidence=0.9,
                    evidence=[self.evidence.build_evidence_from_file(getattr(sql, 'file_path', None))] if getattr(sql, 'file_path', None) else [],
                    rationale="Extracted by Step02 table_operations",
                )
            )
        return rels

    def _jsp_entity_id(self, file_path: str) -> str:
        stem = os.path.splitext(os.path.basename(file_path or ""))[0]
        return f"jsp_{stem}"

    def build_jsp_table_edges(self, jsp: JspDetails, file_path: str) -> List[Step04Relation]:
        rels: List[Step04Relation] = []
        jsp_id = self._jsp_entity_id(file_path)
        blocks = getattr(jsp, "embedded_java", []) or []
        if not blocks:
            return rels

        # Simple regex patterns for CRUD table detection
        pat_select = re.compile(r"\bSELECT\b[\s\S]*?\bFROM\s+([^\s\(\);,]+)", re.IGNORECASE)
        pat_insert = re.compile(r"\bINSERT\s+INTO\s+([^\s\(\);,]+)", re.IGNORECASE)
        pat_update = re.compile(r"\bUPDATE\s+([^\s\(\);,]+)\s+SET\b", re.IGNORECASE)
        pat_delete = re.compile(r"\bDELETE\s+FROM\s+([^\s\(\);,]+)", re.IGNORECASE)
        # Procedure detection (EXEC proc or JDBC { call proc })
        pat_exec = re.compile(r"\bEXEC(?:UTE)?\s+([A-Za-z0-9_\.\[\]]+)", re.IGNORECASE)
        pat_call = re.compile(r"\{\s*call\s+([A-Za-z0-9_\.\[\]]+)\s*\}", re.IGNORECASE)

        def normalize_table(name: str) -> str:
            if not name:
                return name
            n = name.strip()
            # Strip brackets and schema if provided
            n = n.replace('[', '').replace(']', '')
            if '.' in n:
                n = n.split('.')[-1]
            return n

        def is_known_table(name: Optional[str]) -> bool:
            """Return True if the token matches a Step02-known table/view. If index is empty, allow by default."""
            if not name:
                return False
            if not self._known_tables_lc:
                return True
            return self._normalize_object_token(name) in self._known_tables_lc

        def is_likely_proc_token(name: Optional[str]) -> bool:
            """Heuristic: treat as procedure if it appears in the known procs index or matches verb-like proc naming."""
            if not name:
                return False
            token_lc = self._normalize_object_token(name)
            if token_lc in self._known_procs_lc:
                return True
            # Heuristic verbs common in proc names
            return re.match(r"^(get|load|update|delete|insert|create|save|report|validate|check|analyze|export)[a-z0-9_]*$", token_lc) is not None

        def parse_proc(token: str) -> tuple[Optional[str], str]:
            if not token:
                return None, ''
            t = token.strip().strip(';').strip()
            t = t.replace('[', '').replace(']', '')
            # Remove trailing parentheses if mistakenly captured
            t = re.sub(r"\(.*$", "", t)
            if '.' in t:
                parts = t.split('.')
                # assume last is name, previous is schema
                return (parts[-2] if len(parts) >= 2 else None), parts[-1]
            return None, t

        def is_ambiguous_table(raw: Optional[str], unq: Optional[str]) -> bool:
            # Relax ambiguity: allow duplicates across schemas/DBs when same type. Cross-type handled by is_likely_proc_token.
            return False

        # Process each embedded Java block
        for b in blocks:
            code = getattr(b, 'code', '') or ''
            if not code:
                continue
            # CRUD detections
            for m in pat_select.finditer(code):
                raw = m.group(1)
                table = normalize_table(raw)
                if not table or not is_known_table(table) or is_likely_proc_token(table):
                    continue
                rels.append(
                    Step04Relation(
                        id=f"rel_{jsp_id}->readsFrom:{table}",
                        from_id=jsp_id,
                        to_id=f"table_{table}",
                        type="readsFrom",
                        confidence=0.7,
                        evidence=[self.evidence.build_evidence_from_file(file_path)],
                        rationale="Derived from JSP inline SQL SELECT",
                    )
                )
            for m in pat_insert.finditer(code):
                raw = m.group(1)
                table = normalize_table(raw)
                if not table or not is_known_table(table) or is_likely_proc_token(table):
                    continue
                rels.append(
                    Step04Relation(
                        id=f"rel_{jsp_id}->writesTo:{table}",
                        from_id=jsp_id,
                        to_id=f"table_{table}",
                        type="writesTo",
                        confidence=0.7,
                        evidence=[self.evidence.build_evidence_from_file(file_path)],
                        rationale="Derived from JSP inline SQL INSERT",
                    )
                )
            for m in pat_update.finditer(code):
                raw = m.group(1)
                table = normalize_table(raw)
                if not table or not is_known_table(table) or is_likely_proc_token(table):
                    continue
                rels.append(
                    Step04Relation(
                        id=f"rel_{jsp_id}->writesTo:{table}",
                        from_id=jsp_id,
                        to_id=f"table_{table}",
                        type="writesTo",
                        confidence=0.7,
                        evidence=[self.evidence.build_evidence_from_file(file_path)],
                        rationale="Derived from JSP inline SQL UPDATE",
                    )
                )
            for m in pat_delete.finditer(code):
                raw = m.group(1)
                table = normalize_table(raw)
                if not table or not is_known_table(table) or is_likely_proc_token(table):
                    continue
                rels.append(
                    Step04Relation(
                        id=f"rel_{jsp_id}->deletesFrom:{table}",
                        from_id=jsp_id,
                        to_id=f"table_{table}",
                        type="deletesFrom",
                        confidence=0.7,
                        evidence=[self.evidence.build_evidence_from_file(file_path)],
                        rationale="Derived from JSP inline SQL DELETE",
                    )
                )
            # Procedure invocations
            proc_hits: List[tuple[Optional[str], str]] = []
            for m in pat_exec.finditer(code):
                schema, name = parse_proc(m.group(1))
                proc_hits.append((schema, name))
            for m in pat_call.finditer(code):
                schema, name = parse_proc(m.group(1))
                proc_hits.append((schema, name))
            for schema, name in proc_hits:
                name_only = (name or '').strip()
                schema_clean = (schema or '').strip() or None
                if not name_only:
                    continue
                proc_norm = self._normalize_proc_name(schema_clean, name_only)
                # Always add invokesProcedure for navigation
                rels.append(
                    Step04Relation(
                        id=f"rel_{jsp_id}->proc:{proc_norm}",
                        from_id=jsp_id,
                        to_id=f"proc_{proc_norm}",
                        type="invokesProcedure",
                        confidence=0.7,
                        evidence=[self.evidence.build_evidence_from_file(file_path)],
                        rationale="Detected stored procedure execution in JSP",
                    )
                )
                # Expand to table operations via proc map; allow duplicates across schemas/DBs (same-type)
                ops = self.proc_table_ops.get(proc_norm) or self.proc_table_ops.get(name_only)
                if ops:
                    for t_op in ops:
                        rel_type = self._rel_type_for_op(t_op.operation)
                        rels.append(
                            Step04Relation(
                                id=f"rel_{jsp_id}->{rel_type}:{t_op.table_name}",
                                from_id=jsp_id,
                                to_id=f"table_{t_op.table_name}",
                                type=rel_type,
                                confidence=0.7,
                                evidence=[self.evidence.build_evidence_from_file(file_path)],
                                rationale=f"From stored procedure {proc_norm} in JSP",
                            )
                        )
        return rels




