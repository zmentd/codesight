"""
Step 02: AST Structural Extraction Implementation

Main PocketFlow node for AST structural extraction that uses existing LEX utilities
and domain models without creating duplicate infrastructure.
"""

import time
from typing import Any, Dict, List

from core.base_node import BaseNode, ValidationResult
from domain.source_inventory import SourceInventory
from domain.step02_output import Step02AstExtractorOutput
from utils.logging.logger_factory import LoggerFactory

from .ast_parser_manager import ASTParserManager, EnumJSONEncoder


class Step02ASTExtractor(BaseNode):
    """
    Main PocketFlow node for AST structural extraction.
    
    Responsibilities:
    - Coordinate AST parsing across multiple file types
    - Use existing LEX utilities for preprocessing
    - Leverage existing FrameworkDetector for pattern detection
    - Generate Step 02 compliant output using existing domain models
    """
    
    def __init__(self, node_id: str = "step02_ast_extractor") -> None:
        """Initialize Step 02 AST extractor."""
        super().__init__(node_id)
        
        # Step 02 specific components - parser manager will be initialized in prep
        self.parser_manager: ASTParserManager
        
        self.logger = LoggerFactory.get_logger("steps.step02")
    
    def _prep_implementation(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data for AST extraction execution.
        
        Args:
            shared: Shared state dictionary from pipeline
            
        Returns:
            Prepared data for exec method
        """
        self.logger.info("Preparing Step 02 AST extraction")
        
        # Get Step 01 output from shared state (stored by BaseNode using node_id as key)
        step01_result = shared.get("step01_filesystem_analyzer")
        if not step01_result:
            raise ValueError("Step 01 output not found in shared state")
        
        # Extract the actual output data from the step01 result
        step01_data = step01_result.get("output_data")
        if not step01_data:
            raise ValueError("Step 01 output_data not found in step01 result")
        
        # Convert source_inventory to domain object
        source_inventory_data = step01_data.get("source_inventory", {})
        source_inventory = SourceInventory.from_dict(source_inventory_data)
        
        # Initialize AST parser manager with the source inventory
        self.parser_manager = ASTParserManager(self.config, source_inventory)
        
        return {
            "source_inventory": source_inventory,
            "project_path": shared.get("project_path"),
            "project_name": shared.get("project_name")
        }
    
    def _exec_implementation(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute AST structural extraction.
        
        Args:
            prep_result: Prepared data from prep method
            
        Returns:
            AST extraction results
        """
        self.logger.info("Executing Step 02 AST extraction")
        start_time = time.time()
        
        # Get progress context from pipeline step
        progress_context = self.create_progress_context(total=100)
        
        try:
            # Parse source inventory using AST parser manager
            step02_output = self.parser_manager.parse_source_inventory(progress_context)
            
            # Extract validation statistics like step01
            validation_stats = self._extract_validation_statistics(step02_output)
            
            processing_time = time.time() - start_time
            self.logger.info("Step 02 AST extraction completed in %.2f seconds", processing_time)
            
            return {
                "output_data": step02_output,
                "processing_time": processing_time,
                "validation_statistics": validation_stats
            }
            
        except Exception as e:
            self.logger.error("Step 02 execution failed: %s", str(e))
            raise
    
    def _extract_validation_statistics(self, step02_output: Step02AstExtractorOutput) -> Dict[str, Any]:
        """
        Extract validation statistics from AST parsing results, similar to step01.
        
        Args:
            step02_output: The parsed AST output
            
        Returns:
            Dictionary containing validation statistics
        """
        validation_stats = {
            "total_files_parsed": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "syntax_errors": 0,
            "parsing_warnings": 0,
            "java_files_processed": 0,
            "sql_files_processed": 0,
            "jsp_files_processed": 0,
            "config_files_processed": 0,
            "framework_detections": 0,
            "entity_relationships": 0,
            "sql_operations": 0
        }
        
        # Preferred: counts from project_metadata (schema alignment)
        try:
            pm = step02_output.project_metadata
            if pm:
                validation_stats["java_files_processed"] = int(pm.java_files_analyzed or 0)
                validation_stats["sql_files_processed"] = int(pm.sql_files_analyzed or 0)
                validation_stats["jsp_files_processed"] = int(pm.jsp_files_analyzed or 0)
                validation_stats["config_files_processed"] = int(pm.config_files_analyzed or 0)
                validation_stats["total_files_parsed"] = int(pm.total_files_analyzed or 0)
                validation_stats["framework_detections"] = len(pm.frameworks_detected or [])
        except Exception:  # pylint: disable=broad-except
            pass
        
        # Supplement from statistics.raw for parsing/error details
        if step02_output.statistics and step02_output.statistics.raw:
            stats_raw = step02_output.statistics.raw
            parsing = stats_raw.get("parsing_analysis", {})
            validation_stats["successful_parses"] = int(parsing.get("successful_parses", validation_stats["successful_parses"]))
            validation_stats["failed_parses"] = int(parsing.get("failed_parses", validation_stats["failed_parses"]))
            validation_stats["syntax_errors"] = int(parsing.get("syntax_errors", validation_stats["syntax_errors"]))
            validation_stats["parsing_warnings"] = int(parsing.get("parsing_warnings", validation_stats["parsing_warnings"]))
            # Optional additional stats
            validation_stats["entity_relationships"] = stats_raw.get("entity_relationships", validation_stats["entity_relationships"])
            validation_stats["sql_operations"] = stats_raw.get("sql_operations", validation_stats["sql_operations"])
        
        return validation_stats
    
    def _post_implementation(self, shared: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> None:
        """
        Post-process AST extraction results and write output file.
        
        Args:
            shared: Shared state dictionary
            prep_result: Preparation results  
            exec_result: Execution results
        """
        self.logger.info("Post-processing Step 02 results")
        
        step02_output = exec_result.get("output_data")
        if not step02_output:
            raise ValueError("No output data found in exec_result")
        
        # Validate step02 output
        validation_result = self._validate_step02_output(step02_output)
        if not validation_result.is_valid:
            raise ValueError(f"Step 02 output validation failed: {validation_result.errors}")
        
        if validation_result.warnings:
            self.logger.warning("Step 02 output validation warnings: %s", validation_result.warnings)
        
        # Write output file using config pattern like step01
        output_path = self.config.get_output_path_for_step("step02")
        self.logger.info("Writing Step 02 output to: %s", output_path)
        
        try:
            # Convert domain object to dict for JSON serialization
            output_dict = step02_output.to_dict()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(output_dict, f, indent=2, ensure_ascii=False, cls=EnumJSONEncoder)
                
            self.logger.info("Step 02 output written successfully")
            
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to write Step 02 output: %s", str(e))
            raise
        
        # Store validation results and statistics for pipeline use
        exec_result["validation_result"] = validation_result
        exec_result["output_path"] = str(output_path)
    
    def _validate_step02_output(self, step02_output: Step02AstExtractorOutput) -> ValidationResult:
        """
        Validate Step 02 output schema compliance.
        
        Args:
            step02_output: Generated Step 02 output domain object
            
        Returns:
            Validation result
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        # Basic schema validation for domain object
        if not step02_output.step_metadata:
            errors.append("Missing step_metadata in Step 02 output")
        
        if not step02_output.project_metadata:
            errors.append("Missing project_metadata in Step 02 output")
        
        if not step02_output.statistics:
            warnings.append("Missing statistics in Step 02 output")
        
        if not step02_output.source_inventory:
            errors.append("Missing source_inventory in Step 02 output")
        
        # Quality gates enforcement based on NEXT_STEPS
        try:
            stats = step02_output.statistics.to_dict() if step02_output.statistics else {}
            raw = stats or {}
            parsing = raw.get("parsing_analysis", {})
            linkage = raw.get("linkage_analysis", {})
            
            successful = float(parsing.get("successful_parses", 0))
            failed = float(parsing.get("failed_parses", 0))
            total = successful + failed if (successful + failed) > 0 else float(step02_output.step_metadata.files_processed or 0)
            parse_success_pct = (successful / total * 100.0) if total > 0 else 0.0
            route_resolution_rate = float(linkage.get("route_resolution_rate", 0.0))
            unresolved_refs_pct = float(linkage.get("unresolved_refs_pct", 0.0))
            
            gates = self.config.quality_gates.step02
            # min_parse_success_pct
            if parse_success_pct < (gates.min_parse_success_pct * 100.0):
                errors.append(
                    f"min_parse_success_pct gate failed: {parse_success_pct:.2f}% < {gates.min_parse_success_pct*100:.0f}%"
                )
            # min_route_handler_resolution_pct
            if route_resolution_rate < (gates.min_route_handler_resolution_pct * 100.0):
                errors.append(
                    f"min_route_handler_resolution_pct gate failed: {route_resolution_rate:.2f}% < {gates.min_route_handler_resolution_pct*100:.0f}%"
                )
            # max_unresolved_refs_pct
            if unresolved_refs_pct > (gates.max_unresolved_refs_pct * 100.0):
                errors.append(
                    f"max_unresolved_refs_pct gate failed: {unresolved_refs_pct:.2f}% > {gates.max_unresolved_refs_pct*100:.0f}%"
                )
        except Exception as e:  # pylint: disable=broad-except
            warnings.append(f"Gate evaluation warning: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
