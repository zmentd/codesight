"""CodeSight pipeline using PocketFlow.
https://github.com/The-Pocket/PocketFlow
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from pocketflow import Flow  # type: ignore

from config.config import Config
from config.exceptions import ConfigurationError
from utils.logging.logger_factory import LoggerFactory
from utils.progress.progress_manager import CodeSightProgressManager


class CodeSightFlow:
    """
    PocketFlow-based pipeline for CodeSight reverse engineering.
    
    Replaces the complex CodeSightPipeline with a simple Flow-based approach.
    """
    
    def __init__(self) -> None:
        """Initialize CodeSight flow."""
        try:
            self.config = Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"Flow initialization failed: {e}") from e
            
        self.logger = LoggerFactory.get_logger("codesight")
        self._flow: Optional[Flow] = None
        
        # Initialize pipeline-level progress manager
        self.progress_manager = CodeSightProgressManager(use_rich=True)
    
    def create_flow(self) -> Flow:
        """
        Create the CodeSight analysis flow.
        
        Returns:
            Configured PocketFlow Flow instance
        """
        from steps.step01.step01_filesystem_analyzer import FilesystemAnalyzer
        from steps.step02.step02_ast_extractor import Step02ASTExtractor
        from steps.step03.step03_embeddings_processor import Step03EmbeddingsProcessor
        from steps.step04.step04_pattern_analysis import Step04PatternAnalysis
        from steps.step05.step05_capability_assembly import Step05CapabilityAssembly
        from steps.step06.step06_document_assembly import Step06DocumentAssembly

        # Create step nodes
        step01 = FilesystemAnalyzer("step01_filesystem_analyzer")
        step02 = Step02ASTExtractor("step02_ast_extractor")
        step03 = Step03EmbeddingsProcessor("step03_embeddings_processor")
        step04 = Step04PatternAnalysis("step04_pattern_analysis")
        step05 = Step05CapabilityAssembly("step05_capability_assembly")
        step06 = Step06DocumentAssembly("step06_document_assembly")

        # Chain
        step01 >> step02 >> step03 >> step04 >> step05 >> step06  # type: ignore[expression-value,unused-ignore] # pylint: disable=pointless-statement
        
        flow = Flow(start=step01)
        
        self._flow = flow
        return flow
    
    def run_analysis(self, project_path: str, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the complete CodeSight analysis with pipeline-level progress tracking.
        """
        if not project_name:
            project_name = Path(project_path).name
        
        self.logger.info("Starting CodeSight analysis for project: %s", project_name)
        self.logger.info("Target workspace: %s", project_path)
        
        shared_state: Dict[str, Any] = {
            "project_path": project_path,
            "project_name": project_name,
            "start_time": time.time(),
            "progress_manager": self.progress_manager
        }
        
        with self.progress_manager.pipeline_context(f"🔍 CodeSight Analysis: {project_name}") as pipeline:
            try:
                shared_state["pipeline_progress"] = pipeline
                if not self._flow:
                    self.create_flow()
                if self._flow is None:
                    raise RuntimeError("Failed to create flow")
                
                self.logger.info("🚀 Executing CodeSight pipeline...")
                self.logger.info("📋 Pipeline steps: Step01 → Step02 → Step03 → Step04 → Step05 → Step06")
                
                self._flow.run(shared_state)
                
                start_time = shared_state.get('start_time', time.time())
                execution_time = time.time() - start_time
                
                return {
                    "success": True,
                    "project_name": project_name,
                    "execution_time": execution_time,
                    "shared_state": shared_state
                }
                
            except (ConfigurationError, RuntimeError, ValueError) as e:
                self.logger.error("❌ CodeSight analysis failed: %s", e)
                start_time = shared_state.get('start_time', time.time())
                execution_time = time.time() - start_time
                return {
                    "success": False,
                    "project_name": project_name,
                    "error_message": str(e),
                    "execution_time": execution_time
                }

    def _preload_prior_outputs(self, shared_state: Dict[str, Any], steps_to_run: List[str]) -> None:
        """Load prior step outputs from disk into shared_state, for selected steps run.
        Uses config.get_output_path_for_step to locate artifacts and populates the
        expected shared_state keys with {"output_data": <json dict>}.
        """
        step_order = ["step01", "step02", "step03", "step04", "step05", "step06"]
        node_ids = {
            "step01": "step01_filesystem_analyzer",
            "step02": "step02_ast_extractor",
            "step03": "step03_embeddings_processor",
            "step04": "step04_pattern_analysis",
            "step05": "step05_capability_assembly",
            "step06": "step06_document_assembly",
        }

        # Compute all prerequisite steps for the requested selection
        requested = [s for s in steps_to_run if s in step_order]
        prereqs: List[str] = []
        for s in requested:
            idx = step_order.index(s)
            for p in step_order[:idx]:
                if p not in prereqs and p not in requested:
                    prereqs.append(p)

        # Resolve file paths for prior steps
        def path_for(step: str) -> Path:
            if step == "step01":
                return Path(self.config.get_output_path_for_step("step01", "step01_filesystem_analyzer"))
            return Path(self.config.get_output_path_for_step(step))

        for p in prereqs:
            try:
                out_path = path_for(p)
                if out_path.exists():
                    import json
                    with out_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    shared_state[node_ids[p]] = {"output_data": data}
                    self.logger.info("Preloaded %s from %s", p, out_path)
                else:
                    self.logger.warning("Expected prior output for %s not found at %s", p, out_path)
            except Exception as e:  # pylint: disable=broad-except
                self.logger.error("Failed to preload prior output for %s: %s", p, e)

    def run_selected_steps(self, project_path: str, project_name: Optional[str], steps_to_run: List[str]) -> Dict[str, Any]:
        """Run only the selected steps, assuming previous outputs exist for prerequisites.
        Steps can be any subset like ["step04"].
        """
        if not project_name:
            project_name = Path(project_path).name

        # Normalize step names
        steps_norm = [s.strip().lower() for s in steps_to_run if s and s.strip()]
        if not steps_norm:
            return {
                "success": False,
                "project_name": project_name,
                "error_message": "No steps provided",
                "execution_time": 0.0,
            }

        self.logger.info("Running selected steps: %s", ", ".join(steps_norm))

        # Lazy imports of nodes
        from steps.step01.step01_filesystem_analyzer import FilesystemAnalyzer
        from steps.step02.step02_ast_extractor import Step02ASTExtractor
        from steps.step03.step03_embeddings_processor import Step03EmbeddingsProcessor
        from steps.step04.step04_pattern_analysis import Step04PatternAnalysis
        from steps.step05.step05_capability_assembly import Step05CapabilityAssembly
        from steps.step06.step06_document_assembly import Step06DocumentAssembly

        registry = {
            "step01": lambda: FilesystemAnalyzer("step01_filesystem_analyzer"),
            "step02": lambda: Step02ASTExtractor("step02_ast_extractor"),
            "step03": lambda: Step03EmbeddingsProcessor("step03_embeddings_processor"),
            "step04": lambda: Step04PatternAnalysis("step04_pattern_analysis"),
            "step05": lambda: Step05CapabilityAssembly("step05_capability_assembly"),
            "step06": lambda: Step06DocumentAssembly("step06_document_assembly"),
        }

        # Initial shared state
        shared_state: Dict[str, Any] = {
            "project_path": project_path,
            "project_name": project_name,
            "start_time": time.time(),
            "progress_manager": self.progress_manager,
        }

        try:
            # Preload prior outputs needed by the selected steps
            self._preload_prior_outputs(shared_state, steps_norm)

            with self.progress_manager.pipeline_context(f"⚡ CodeSight Selected Steps: {project_name}") as pipeline:
                shared_state["pipeline_progress"] = pipeline
                for step_name in steps_norm:
                    factory = registry.get(step_name)
                    if not factory:
                        raise ValueError(f"Unknown step '{step_name}'")
                    node = factory()
                    self.logger.info("▶ Running %s", step_name)
                    node.run(shared_state)

            execution_time = time.time() - shared_state.get('start_time', time.time())
            return {
                "success": True,
                "project_name": project_name,
                "execution_time": execution_time,
                "shared_state": shared_state,
            }
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("❌ Selected steps run failed: %s", e)
            execution_time = time.time() - shared_state.get('start_time', time.time())
            return {
                "success": False,
                "project_name": project_name,
                "error_message": str(e),
                "execution_time": execution_time,
            }
    

def run_codesight_analysis(project_path: str, project_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to run CodeSight analysis.
    """
    flow = CodeSightFlow()
    results = flow.run_analysis(project_path, project_name)
    flow.logger.info("✅ CodeSight analysis completed successfully!")
    flow.logger.info("⏱️  Analysis took %.2f seconds", results["execution_time"])

    return results


def run_codesight_selected_steps(project_path: str, project_name: Optional[str], steps_to_run: List[str]) -> Dict[str, Any]:
    """Convenience function to run selected steps only."""
    flow = CodeSightFlow()
    results = flow.run_selected_steps(project_path, project_name, steps_to_run)
    status = "completed successfully" if results.get("success") else "failed"
    flow.logger.info("✅ CodeSight selected steps %s!", status)
    flow.logger.info("⏱️  Run took %.2f seconds", results.get("execution_time", 0.0))
    return results