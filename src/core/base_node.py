"""Base node implementation for CodeSight pipeline using PocketFlow."""

import abc
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from pocketflow import Node  # type: ignore

from config.config import Config
from config.exceptions import ConfigurationError
from utils.logging.logger_factory import LoggerFactory
from utils.progress.progress_manager import CodeSightProgressManager


class NodeStatus(Enum):
    """Node execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class NodeResult:
    """Result of node execution."""
    success: bool
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Validation result information."""
    is_valid: bool
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    
    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class BaseNode(Node):
    """
    Base class for all CodeSight pipeline nodes using PocketFlow pattern.
    
    Provides:
    - PocketFlow's prep/exec/post execution model
    - Automatic validation after execution
    - Progress tracking and reporting
    - Setup and cleanup lifecycle
    - Unified configuration access via Config
    """
    
    def __init__(self, node_id: str, max_retries: int = 1, wait: int = 0):
        """Initialize base node with PocketFlow parameters."""
        super().__init__(max_retries=max_retries, wait=wait)
        self.node_id = node_id
        try:
            self.config = Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"Failed to initialize node {node_id}: {e}") from e
        
        self.logger = LoggerFactory.get_logger("core")
        
        # Progress tracking will be initialized in prep() using shared state
        self._progress_manager: Optional[CodeSightProgressManager] = None
        
        self._start_time: Optional[float] = None
        self._pipeline_step: Optional[Any] = None  # Will be set in prep() if pipeline context available
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data for execution (PocketFlow pattern).
        
        Args:
            shared: Shared state dictionary from pipeline
            
        Returns:
            Prepared data for exec method
        """
        self.logger.debug("Preparing node: %s", self.node_id)
        self._start_time = time.time()
        
        # Get progress manager from shared state
        self._progress_manager = shared.get("progress_manager")
        if self._progress_manager is None:
            raise ValueError(f"Node {self.node_id}: progress_manager not found in shared state. This indicates a flow configuration error.")
        
        # Connect to pipeline progress if available
        pipeline_progress = shared.get("pipeline_progress")
        if pipeline_progress:
            # Create step within pipeline context
            self._pipeline_step = pipeline_progress.create_step(
                self.node_id, 
                f"Processing {self.node_id}",
                total=1  # Will be set when progress context is created
            )
        else:
            raise ValueError(f"Node {self.node_id}: pipeline_progress not found in shared state. This indicates a flow configuration error.")
        
        # Setup phase
        self.setup()
        
        # Extract input data - subclasses can override _prep_implementation
        return self._prep_implementation(shared)
    
    def exec(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:  # pylint: disable=arguments-renamed
        """
        Execute the main node logic (PocketFlow pattern).
        
        Args:
            prep_result: Result from prep method
            
        Returns:
            Execution result
        """
        self.logger.debug("Executing node: %s", self.node_id)
        
        try:
            # Call the subclass implementation
            result = self._exec_implementation(prep_result)
            
            return result
            
        except Exception as e:
            self.logger.error("Node execution failed: %s", e)
            raise
    
    def post(self, shared: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> None:  # pylint: disable=arguments-renamed
        """
        Post-processing after execution (PocketFlow pattern).
        
        Args:
            shared: Shared state dictionary
            prep_result: Result from prep method
            exec_result: Result from exec method
        """
        try:
            self.logger.debug("Post-processing node: %s", self.node_id)
            
            # Update execution time
            if self._start_time:
                execution_time = time.time() - self._start_time
                exec_result["execution_time"] = execution_time
            
            # Store result in shared state
            shared[self.node_id] = exec_result
            
            # Call subclass post-processing
            self._post_implementation(shared, prep_result, exec_result)
                        
            # Automatic validation if result contains output_data
            if isinstance(exec_result, dict) and "output_data" in exec_result:
                self.logger.debug("🔍 Running automatic validation...")
                validation = self.validate_results(exec_result["output_data"])
                
                if not validation.is_valid:
                    error_msg = f"Validation failed: {validation.errors}"
                    self.logger.error("❌ %s", error_msg)
                    raise ValueError(error_msg)
                
                # Add validation metadata
                exec_result["validation"] = {
                    "is_valid": validation.is_valid,
                    "warnings": validation.warnings,
                    "timestamp": time.time()
                }
                
                if validation.warnings:
                    self.logger.warning("⚠️ Validation warnings: %s", validation.warnings)

            if self._pipeline_step:
                self._pipeline_step.complete()
            self.logger.debug("Node completed successfully: %s", self.node_id)
            
        except Exception as e:
            self.logger.error("Post-processing failed: %s", e)
            raise
        finally:
            # Complete pipeline step if connected
            if hasattr(self, '_pipeline_step') and self._pipeline_step:
                self._pipeline_step.complete()
            
            # Cleanup phase
            self.cleanup()
    
    @abc.abstractmethod
    def _prep_implementation(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement data preparation logic in subclasses.
        
        Args:
            shared: Shared state dictionary
            
        Returns:
            Prepared input data for execution
        """
        raise NotImplementedError("Subclasses must implement _prep_implementation")
    
    @abc.abstractmethod
    def _exec_implementation(self, prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement the main execution logic in subclasses.
        
        Args:
            prep_result: Prepared data from prep phase
            
        Returns:
            Execution result with output_data key
        """
        raise NotImplementedError("Subclasses must implement _exec_implementation")
    
    def _post_implementation(self, shared: Dict[str, Any], prep_result: Dict[str, Any], exec_result: Dict[str, Any]) -> None:
        """
        Optional post-processing implementation in subclasses.
        
        Args:
            shared: Shared state dictionary
            prep_result: Result from prep method
            exec_result: Result from exec method
        """
        # Default implementation does nothing - subclasses can override
    
    def validate_results(self, output_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate node output data.
        
        Args:
            output_data: Data produced by this node
            
        Returns:
            ValidationResult indicating validation status
        """
        # Default validation - subclasses should override
        return ValidationResult(is_valid=True)
    
    def create_progress_context(self, total: Optional[int] = None) -> Any:
        """
        Create a progress tracking context for subclasses.
        
        Usage in subclass _exec_implementation:
        ```python
        with self.create_progress_context(total_files) as progress:
            progress.start_phase("scanning", "Scanning files", scan_count) 
            for file in files:
                # Process file
                progress.update(1, current_item=file.name)
        ```
        
        Args:
            total: Total number of items to process
            
        Returns:
            Progress tracking context manager
        """
        # Use pipeline step (should always be available if flow is configured correctly)
        assert self._pipeline_step is not None, f"Node {self.node_id}: pipeline step not initialized"
        
        if total is not None:
            self._pipeline_step.total = total
        return self._pipeline_step.track_progress(total)
    
    def setup(self) -> None:
        """Initialize node before execution."""
        self.logger.debug("Setting up node: %s", self.node_id)
    
    def cleanup(self) -> None:
        """Cleanup after node execution."""
        self.logger.debug("Cleaning up node: %s", self.node_id)
