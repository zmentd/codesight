"""
Step04 Pattern & Configuration Analysis for CodeSight.

Consumes Step02 outputs only (no file re-parsing) and assembles
Step04 graph artifacts (entities, relations, traces) using Step04Assembler.
Follows the BaseNode prep/exec/post pattern for PocketFlow integration.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from config.config import Config
from config.exceptions import ConfigurationError
from core.base_node import BaseNode, ValidationResult
from domain.step02_output import Step02AstExtractorOutput
from steps.step04.assembly import Step04Assembler
from steps.step04.models import Relation, Step04Output
from utils.logging.logger_factory import LoggerFactory


class ProcessingError(Exception):
    """Processing error for Step04."""


class Step04PatternAnalysis(BaseNode):
    """
    Step04 node that assembles routes, handlers, views, data-access and security edges,
    and derives traces. Strictly uses Step02 models and inventory; no re-parsing.
    """

    def __init__(self, node_id: str = "step04_pattern_analysis") -> None:
        super().__init__(node_id=node_id)

        try:
            self.config = Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"Failed to initialize Step04 node: {e}") from e

        self.logger = LoggerFactory.get_logger("steps.step04")
        # Pass step04 config to assembler for toggle awareness
        self.assembler = Step04Assembler(self.config.steps.step04)
        self.step04_config = self.config.steps.step04
        self.logger.info("Step04 pattern analysis node initialized")

    def _prep_implementation(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare Step04 by loading Step02 output from shared state."""
        self.logger.info("Preparing Step 04 pattern analysis")

        step02_result = shared.get("step02_ast_extractor")
        if not step02_result:
            raise ValueError("Step 02 output not found in shared state")

        step02_data = step02_result.get("output_data")
        if not step02_data:
            raise ValueError("Step 02 output_data not found in step02 result")

        if isinstance(step02_data, Step02AstExtractorOutput):
            step02_output = step02_data
        elif isinstance(step02_data, dict):
            step02_output = Step02AstExtractorOutput.from_dict(step02_data)
        else:
            raise ValueError("Invalid Step 02 output data type: expected dict or Step02AstExtractorOutput")

        return {
            "step02_output": step02_output,
            "project_path": shared.get("project_path"),
            "project_name": shared.get("project_name"),
        }

    def _exec_implementation(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assemble Step04 artifacts from Step02 output.
        Returns dict with PocketFlow-compatible structure.
        """
        try:
            project_name = prep_result["project_name"]
            step02_output: Step02AstExtractorOutput = prep_result["step02_output"]

            self.logger.info("Starting Step04 assembly for project: %s", project_name)
            start_time = time.time()

            step04_output: Step04Output = self.assembler.assemble(step02_output, project_name)

            processing_time = time.time() - start_time
            return {
                "output_data": step04_output,
                "processing_time": processing_time,
                "stats": step04_output.stats,
            }
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Step04 assembly failed: %s", e, exc_info=True)
            raise ProcessingError(f"Step04 pattern analysis failed: {e}") from e

    def _post_implementation(self, shared: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> None:
        """Validate and persist Step04 output JSON artifact."""
        self.logger.info("Post-processing Step 04 results")

        if not isinstance(exec_result, dict) or "output_data" not in exec_result:
            self.logger.warning("No output_data found in exec_result; skipping Step04 post-processing")
            return

        output_obj = exec_result["output_data"]
        # Validate via overridden validate_results
        validation = self.validate_results(output_obj)
        if not validation.is_valid:
            raise ValueError(f"Step 04 output validation failed: {validation.errors}")
        if validation.warnings:
            self.logger.warning("Step 04 validation warnings: %s", validation.warnings)

        # Persist using config path helper, similar to Step03
        output_path = self.config.get_output_path_for_step("step04", default_filename="step04")
        self.logger.info("Writing Step 04 output to: %s", output_path)

        # Convert to dict for JSON
        out_dict: Dict[str, Any] = output_obj.to_dict() if isinstance(output_obj, Step04Output) else output_obj
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(out_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to write Step 04 output: %s", str(e))
            raise

        exec_result["validation_result"] = validation
        exec_result["output_path"] = str(output_path)

    def _calc_config_parse_success_pct(self, output_data: Step04Output | Dict[str, Any]) -> float:
        """Heuristic: percentage of Route entities that either render a view or have a handler relation."""
        routes_total = 0
        with_view = 0
        with_handler = 0
        if isinstance(output_data, Step04Output):
            stats = output_data.stats or {}
            routes_total = int(stats.get("routes_total", 0))
            with_view = int(stats.get("routes_with_view", 0))
            with_handler = int(stats.get("routes_with_handler", 0))
        elif isinstance(output_data, dict):
            stats = output_data.get("stats", {}) or {}
            routes_total = int(stats.get("routes_total", 0))
            with_view = int(stats.get("routes_with_view", 0))
            with_handler = int(stats.get("routes_with_handler", 0))
            # If stats are missing or zero, compute from entities/relations
            if routes_total == 0 and isinstance(output_data.get("entities"), list) and isinstance(output_data.get("relations"), list):
                routes_total = sum(1 for e in output_data["entities"] if isinstance(e, dict) and e.get("type") == "Route")
                # tolerant relation parsing: accept different key names and type casings
                handles = set()
                renders = set()
                for r in output_data["relations"]:
                    if not isinstance(r, dict):
                        continue
                    rtype = str(r.get("type") or "").strip().lower()
                    # Normalize origin field - handle several common variants
                    origin = r.get("from") or r.get("from_id") or r.get("fromId") or r.get("origin")
                    if not origin:
                        origin = r.get("fromEntity") or r.get("source") or r.get("source_id")
                    if not origin:
                        # last resort: try 'from' inside nested structures
                        try:
                            if isinstance(r.get("payload"), dict):
                                origin = r["payload"].get("from") or r["payload"].get("from_id")
                        except (AttributeError, KeyError, TypeError):
                            pass
                    if not origin:
                        continue
                    if rtype == "handlesroute":
                        handles.add(origin)
                    elif rtype == "renders":
                        renders.add(origin)
                with_view = len(renders)
                with_handler = len(handles)
        if routes_total <= 0:
            return 1.0  # nothing to parse, consider pass
        satisfied = max(with_view, with_handler)
        return satisfied / routes_total

    def _apply_confidence_filter(self, rels: List[Relation], threshold: float) -> List[Relation]:
        return [r for r in rels if (getattr(r, 'confidence', 0.0) or 0.0) >= threshold]

    def validate_results(self, output_data: Any) -> ValidationResult:
        """Validate Step04 output, compute/require stats, enforce gates and confidence filtering."""
        errors: list[str] = []
        warnings: list[str] = []

        # Basic structural validation
        if isinstance(output_data, Step04Output):
            if not output_data.entities:
                warnings.append("No entities in Step04 output")
            if not output_data.relations:
                warnings.append("No relations in Step04 output")
            # Stats should exist; if not, assemble minimums
            stats = output_data.stats or {}
            if "routes_total" not in stats:
                # best-effort reconstruct from entities/relations
                try:
                    routes_total = sum(1 for e in output_data.entities if e.type == "Route")
                    handles = {r.from_id for r in output_data.relations if r.type == "handlesRoute"}
                    renders = {r.from_id for r in output_data.relations if r.type == "renders"}
                    output_data.stats.update({
                        "routes_total": routes_total,
                        "routes_with_view": len(renders),
                        "routes_with_handler": len(handles),
                        "route_resolution_rate": (len(handles) / routes_total) if routes_total else 0.0,
                        "jsp_link_coverage": (len(renders) / routes_total) if routes_total else 0.0,
                    })
                except Exception:  # pylint: disable=broad-except
                    pass
        elif isinstance(output_data, dict):
            for key in ("version", "project_name", "generated_at", "entities", "relations"):
                if key not in output_data:
                    errors.append(f"Missing '{key}' in Step04 output")
            ents = output_data.get("entities", [])
            rels = output_data.get("relations", [])
            if not isinstance(ents, list):
                errors.append("'entities' must be a list")
            if not isinstance(rels, list):
                errors.append("'relations' must be a list")
        else:
            errors.append("Output must be Step04Output or dict")

        # Enforce quality gates and confidence filtering
        try:
            gates = self.config.quality_gates.step04
            threshold = getattr(gates, 'min_pattern_confidence', 0.8) or getattr(self.step04_config, 'pattern_confidence_threshold', 0.8)

            # Diagnostics: compute how many relations would be filtered and by type
            def _rel_list(obj: Any) -> List[Relation] | List[dict]:
                if isinstance(obj, Step04Output):
                    return obj.relations or []
                if isinstance(obj, dict):
                    return obj.get("relations", []) or []
                return []

            rels_before = _rel_list(output_data)
            filtered_count = 0
            filtered_by_type: dict[str, int] = {}
            try:
                for rr in rels_before:
                    if isinstance(rr, Relation):
                        conf = float(getattr(rr, 'confidence', 0.0) or 0.0)
                        rtype = str(getattr(rr, 'type', '') or '')
                        if conf < float(threshold):
                            filtered_count += 1
                            filtered_by_type[rtype] = filtered_by_type.get(rtype, 0) + 1
                    elif isinstance(rr, dict):
                        conf = float(rr.get('confidence', 0.0) or 0.0)
                        rtype = str(rr.get('type', '') or '')
                        if conf < float(threshold):
                            filtered_count += 1
                            filtered_by_type[rtype] = filtered_by_type.get(rtype, 0) + 1
            except (AttributeError, TypeError, ValueError):
                # Best-effort only; ignore diagnostics failure
                pass

            # Filter relations below min confidence (only warn here; assemblers should aim above threshold)
            if isinstance(output_data, Step04Output):
                before = len(output_data.relations)
                output_data.relations = self._apply_confidence_filter(output_data.relations, threshold)
                after = len(output_data.relations)
                if after < before:
                    warnings.append(f"Filtered {before - after} relations below confidence threshold {threshold}")
                # Ensure stats exists and record diagnostics
                output_data.stats = dict(output_data.stats or {})
                output_data.stats["filtered_relations_below_confidence"] = filtered_count
                output_data.stats["filtered_relations_by_type"] = dict(sorted(filtered_by_type.items(), key=lambda kv: kv[1], reverse=True))
            elif isinstance(output_data, dict) and isinstance(output_data.get("relations"), list):
                before = len(output_data["relations"])
                output_data["relations"] = [
                    r for r in output_data["relations"]
                    if isinstance(r, dict) and float(r.get("confidence", 0.0)) >= threshold
                ]
                after = len(output_data["relations"])
                if after < before:
                    warnings.append(f"Filtered {before - after} relations below confidence threshold {threshold}")
                # Ensure stats exists and record diagnostics
                stats = output_data.setdefault("stats", {})
                stats["filtered_relations_below_confidence"] = filtered_count
                stats["filtered_relations_by_type"] = dict(sorted(filtered_by_type.items(), key=lambda kv: kv[1], reverse=True))

            # Compute config parse success pct and compare to gate
            cfg_pct = self._calc_config_parse_success_pct(output_data)
            min_pct = float(getattr(gates, 'min_config_parse_success_pct', 0.8))
            if cfg_pct < min_pct:
                errors.append(
                    f"Config parse success {cfg_pct:.2f} below minimum {min_pct:.2f}"
                )
        except (AttributeError, TypeError, ValueError) as e:
            warnings.append(f"Gate evaluation error: {e}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def create_step04_node() -> Step04PatternAnalysis:
    """Factory to create Step04 node with configuration validation."""
    try:
        return Step04PatternAnalysis()
    except Exception as e:  # pylint: disable=broad-except
        raise ConfigurationError(f"Failed to create Step04 node: {e}") from e
