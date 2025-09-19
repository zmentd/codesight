"""
Step05 Capability/Domain Assembly for CodeSight.

Consumes Step04 outputs only (no re-parsing) and assembles
Step05 capability artifacts using Step05Assembler.
Follows the BaseNode prep/exec/post pattern for PocketFlow integration.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from config.config import Config
from config.exceptions import ConfigurationError
from core.base_node import BaseNode, ValidationResult
from steps.step04.models import Entity, Step04Output
from steps.step05.assembler import Step05Assembler
from steps.step05.models import CapabilityOutput
from steps.step05.summary import build_summary
from utils.logging.logger_factory import LoggerFactory
from utils.progress.step_tracker import StepProgressTracker


class ProcessingError(Exception):
    """Processing error for Step05."""


class Step05CapabilityAssembly(BaseNode):
    """
    Step05 node that assembles capabilities/domains from Step04 graph outputs.
    Strictly uses Step04 models; no re-parsing or direct file access here.
    """

    def __init__(self, node_id: str = "step05_capability_assembly") -> None:
        super().__init__(node_id=node_id)

        try:
            self.config = Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"Failed to initialize Step05 node: {e}") from e

        self.logger = LoggerFactory.get_logger("steps.step05")
        # Pass step05 config to assembler for toggle awareness
        self.assembler = Step05Assembler(self.config.steps.step05)
        self.step05_config = self.config.steps.step05
        self.logger.info("Step05 capability assembly node initialized")

    def _prep_implementation(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare Step05 by loading Step04 (and Step03 if present) output from shared state."""
        self.logger.info("Preparing Step 05 capability assembly")

        step04_result = shared.get("step04_pattern_analysis")
        if not step04_result:
            raise ValueError("Step 04 output not found in shared state")

        step04_data = step04_result.get("output_data")
        if not step04_data:
            raise ValueError("Step 04 output_data not found in step04 result")

        if isinstance(step04_data, Step04Output):
            step04_output = step04_data
        elif isinstance(step04_data, dict):
            step04_output = Step04Output.from_dict(step04_data)
        else:
            raise ValueError("Invalid Step 04 output data type: expected dict or Step04Output")

        # Optionally get Step03 embeddings/cluster output if available
        step03_result = shared.get("step03_embeddings_processor")
        step03_output: Optional[Dict[str, Any]] = None
        if isinstance(step03_result, dict):
            so = step03_result.get("output_data")
            if isinstance(so, dict) and so.get("step03_results"):
                step03_output = so  # keep raw dict; assembler will parse

        return {
            "step04_output": step04_output,
            "step03_output": step03_output,
            "project_path": shared.get("project_path"),
            "project_name": shared.get("project_name"),
        }

    def _exec_implementation(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assemble Step05 capabilities from Step04 (+Step03 if present).
        Returns dict with PocketFlow-compatible structure.
        """
        try:
            project_name = prep_result["project_name"]
            step04_output: Step04Output = prep_result["step04_output"]
            step03_output: Optional[Dict[str, Any]] = prep_result.get("step03_output")

            self.logger.info("Starting Step05 capability assembly for project: %s", project_name)
            start_time = time.time()

            # Progress tracking using centralized utilities
            step_tracker = StepProgressTracker("step05", "🧩 Step05: Capability Assembly")
            with step_tracker.track_progress() as progress:
                # Define on_progress handler to bridge assembler events to tracker
                phase_started = {"groups": False}

                def on_progress(evt: Dict[str, Any]) -> None:
                    phase = evt.get("phase")
                    if phase == "init":
                        total_groups = int(evt.get("groups_total", 0) or 0)
                        if not phase_started["groups"]:
                            progress.start_phase("groups", "Grouping and Naming", total_groups)
                            phase_started["groups"] = True
                    elif phase == "naming_done":
                        # Advance one group completion
                        progress.update_phase("groups", 1, current_item=str(evt.get("route", "")))
                    # Other phases can be added here if we add UI for them later

                step05_output: CapabilityOutput = self.assembler.assemble(step04_output, step03_output, on_progress=on_progress)

            processing_time = time.time() - start_time
            return {
                "output_data": step05_output,
                "processing_time": processing_time,
                "stats": step05_output.stats,
            }
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Step05 capability assembly failed: %s", e, exc_info=True)
            raise ProcessingError(f"Step05 capability assembly failed: {e}") from e

    def _post_implementation(self, shared: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> None:
        """Validate and persist Step05 output JSON artifact."""
        self.logger.info("Post-processing Step 05 results")

        if not isinstance(exec_result, dict) or "output_data" not in exec_result:
            self.logger.warning("No output_data found in exec_result; skipping Step05 post-processing")
            return

        output_obj = exec_result["output_data"]
        # Validate via overridden validate_results
        validation = self.validate_results(output_obj)
        if not validation.is_valid:
            raise ValueError(f"Step 05 output validation failed: {validation.errors}")
        if validation.warnings:
            self.logger.warning("Step 05 validation warnings: %s", validation.warnings)

        # Persist using config path helper
        output_path = self.config.get_output_path_for_step("step05", default_filename="step05")
        self.logger.info("Writing Step 05 output to: %s", output_path)

        # Convert to dict for JSON
        out_dict: Dict[str, Any] = output_obj.to_dict() if isinstance(output_obj, CapabilityOutput) else output_obj
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(out_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to write Step 05 output: %s", str(e))
            raise

        exec_result["validation_result"] = validation
        exec_result["output_path"] = str(output_path)
        # Attach a small summary for UX (build_summary handles its own errors)
        exec_result["summary"] = build_summary(output_obj)

    def _compute_route_coverage(self, step05: CapabilityOutput, step04: Step04Output | None) -> float:
        """Compute coverage of routes represented by capabilities."""
        if step05 and step05.stats and isinstance(step05.stats.get("route_coverage_pct"), (int, float)):
            try:
                return float(step05.stats["route_coverage_pct"])  # computed by assembler
            except (TypeError, ValueError):  # pragma: no cover - best effort
                pass
        # Fallback: compute from Step04 entities
        if step04 is not None:
            total_routes = sum(1 for e in step04.entities if isinstance(e, Entity) and e.type == "Route")
            covered_routes = int(len(step05.capabilities or []))
            return (covered_routes / total_routes) if total_routes > 0 else 1.0
        return 0.0

    def validate_results(self, output_data: Any) -> ValidationResult:
        """Validate Step05 output, compute/require stats, and enforce gates."""
        errors: List[str] = []
        warnings: List[str] = []

        step04_output: Step04Output | None = None
        try:
            # Try to get Step04 from shared cache if available via base class
            shared = getattr(self, "_BaseNode__shared_state", None)
            if isinstance(shared, dict):
                s4 = shared.get("step04_pattern_analysis")
                if isinstance(s4, dict) and isinstance(s4.get("output_data"), dict):
                    step04_output = Step04Output.from_dict(s4["output_data"])  # best effort
        except (AttributeError, KeyError, TypeError, ValueError):  # pragma: no cover - optional context
            step04_output = None

        # Structural validation
        if isinstance(output_data, CapabilityOutput):
            caps = output_data.capabilities or []
            if not caps:
                warnings.append("No capabilities produced in Step05 output")
            # Compute coverage if missing - but trust assembler calculation if present
            stats = output_data.stats or {}
            if "route_coverage_pct" not in stats or stats.get("route_coverage_pct") is None:
                stats["route_coverage_pct"] = self._compute_route_coverage(output_data, step04_output)
                output_data.stats = stats

            # Enforce quality gates
            gates = self.config.quality_gates.step05
            min_cov = float(getattr(gates, 'min_capability_coverage_pct', 0.6))
            min_cites = int(getattr(gates, 'min_citations_per_capability', 1))
            
            print(f"DEBUG: Quality gates config: {gates}")
            print(f"DEBUG: min_capability_coverage_pct from config: {getattr(gates, 'min_capability_coverage_pct', 'NOT_FOUND')}")
            print(f"DEBUG: Calculated min_cov: {min_cov}")

            # Use the assembler's coverage calculation which accounts for business domain grouping
            coverage = float(output_data.stats.get("route_coverage_pct", 0.0) or 0.0)
            print(f"DEBUG: Validation coverage check: {coverage:.3f} vs minimum {min_cov:.3f}")
            print(f"DEBUG: Stats: {output_data.stats}")
            print(f"DEBUG: Capabilities count: {len(caps)}")
            if coverage < min_cov:
                errors.append(f"Capability coverage {coverage:.2f} below minimum {min_cov:.2f}")

            # Warn on low-citation capabilities
            low_cite = [c.id for c in caps if len(c.citations or []) < min_cites]
            if low_cite:
                warnings.append(f"{len(low_cite)} capabilities below citations threshold {min_cites}")
                output_data.stats["capabilities_below_citation_threshold"] = len(low_cite)
        elif isinstance(output_data, dict):
            for key in ("project_name", "capabilities", "relations", "stats"):
                if key not in output_data:
                    errors.append(f"Missing '{key}' in Step05 output")
            # Basic gates if stats present
            stats = output_data.get("stats", {}) or {}
            gates = self.config.quality_gates.step05
            min_cov = float(getattr(gates, 'min_capability_coverage_pct', 0.6))
            coverage = float(stats.get("route_coverage_pct", 0.0) or 0.0)
            if coverage < min_cov:
                errors.append(f"Capability coverage {coverage:.2f} below minimum {min_cov:.2f}")
        else:
            errors.append("Output must be CapabilityOutput or dict")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def create_step05_node() -> Step05CapabilityAssembly:
    """Factory to create Step05 node with configuration validation."""
    try:
        return Step05CapabilityAssembly()
    except Exception as e:  # pylint: disable=broad-except
        raise ConfigurationError(f"Failed to create Step05 node: {e}") from e
