"""
Step06 Document Assembly for CodeSight.

Consumes Step05 output and renders Confluence-ready Markdown for:
- BRD (Business Requirements Document)
- Technical Specification

Follows the BaseNode prep/exec/post pattern.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from config.config import Config
from config.exceptions import ConfigurationError
from core.base_node import BaseNode, ValidationResult
from steps.step05.models import CapabilityOutput
from steps.step06.renderer import render_documents
from utils.logging.logger_factory import LoggerFactory


class ProcessingError(Exception):
    """Processing error for Step06."""


class Step06DocumentAssembly(BaseNode):
    def __init__(self, node_id: str = "step06_document_assembly") -> None:
        super().__init__(node_id=node_id)
        try:
            self.config = Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"Failed to initialize Step06 node: {e}") from e
        self.logger = LoggerFactory.get_logger("steps.step06")

    def _prep_implementation(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        step05_result = shared.get("step05_capability_assembly")
        if not step05_result:
            raise ValueError("Step 05 output not found in shared state")
        step05_data = step05_result.get("output_data")
        if isinstance(step05_data, CapabilityOutput):
            step05_output = step05_data
        elif isinstance(step05_data, dict):
            # Step05 CapabilityOutput.to_dict is used when persisted; accept dict form too
            step05_output = CapabilityOutput(
                project_name=str(step05_data.get("project_name")),
                capabilities=[],  # not reconstructing full dataclasses for now
                relations=step05_data.get("relations", []),
                stats=step05_data.get("stats", {}),
            )
            # If full capabilities dicts provided, keep as-is for rendering by duck-typing
            step05_output.capabilities = step05_data.get("capabilities", [])
        else:
            raise ValueError("Invalid Step 05 output data type")
        return {"step05_output": step05_output}

    def _exec_implementation(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            start = time.time()
            step05: CapabilityOutput = prep_result["step05_output"]
            bundle = render_documents(step05)
            elapsed = time.time() - start
            return {"output_data": bundle, "processing_time": elapsed}
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Step06 document assembly failed: %s", e, exc_info=True)
            raise ProcessingError(f"Step06 document assembly failed: {e}") from e

    def _post_implementation(self, shared: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> None:
        if not isinstance(exec_result, dict) or "output_data" not in exec_result:
            self.logger.warning("No output_data found in exec_result; skipping Step06 post-processing")
            return
        bundle = exec_result["output_data"]
        # Persist two Markdown files for easy Confluence paste
        out_dir = self.config.get_output_dir_for_step("step06")
        brd_path = f"{out_dir}/step06_brd.md"
        tech_path = f"{out_dir}/step06_tech_spec.md"
        try:
            # Ensure directory exists (best-effort)
            import os
            os.makedirs(out_dir, exist_ok=True)
            with open(brd_path, "w", encoding="utf-8") as f:
                f.write(bundle.brd_markdown)
            with open(tech_path, "w", encoding="utf-8") as f:
                f.write(bundle.tech_spec_markdown)
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to write Step06 markdown outputs: %s", e)
            raise

        # Also write a JSON descriptor for the bundle
        json_path = self.config.get_output_path_for_step("step06", default_filename="step06")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(bundle.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to write Step06 JSON output: %s", e)
            raise

        exec_result["output_path_brd"] = brd_path
        exec_result["output_path_tech"] = tech_path
        exec_result["output_path"] = json_path

    def validate_results(self, output_data: Any) -> ValidationResult:  # minimal for Step06 bundle
        # For now, Step06 validates presence of two markdown strings
        errors: List[str] = []
        warnings: List[str] = []
        try:
            if not getattr(output_data, 'brd_markdown', None):
                errors.append("Missing BRD content")
            if not getattr(output_data, 'tech_spec_markdown', None):
                errors.append("Missing Technical Spec content")
        except (AttributeError, TypeError, ValueError):
            errors.append("Invalid Step06 bundle")
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def create_step06_node() -> Step06DocumentAssembly:
    try:
        return Step06DocumentAssembly()
    except Exception as e:  # pylint: disable=broad-except
        raise ConfigurationError(f"Failed to create Step06 node: {e}") from e
