"""
Step Progress Tracker

Specialized progress tracking for individual CodeSight pipeline steps.
Provides step-specific functionality and integrates with the main progress manager.

USAGE EXAMPLES:

# Step01 - File System Analysis (Single-threaded):
```python
from utils.progress import StepProgressTracker

# In FilesystemAnalyzer._exec_implementation():
step_tracker = StepProgressTracker("step01", "📁 File System Analysis")

with step_tracker.track_progress(total_files) as progress:
    # Phase 1: Directory scanning
    progress.start_phase("scanning", "Scanning directories", scan_count)
    for directory in directories:
        # Scan directory
        progress.update_phase("scanning", 1, current_item=directory.name)
    
    # Phase 2: File classification  
    progress.start_phase("classifying", "Classifying files", file_count)
    for file in files:
        # Classify file
        progress.update_phase("classifying", 1, current_item=file.name)
    
    # Phase 3: Metadata extraction
    progress.start_phase("metadata", "Extracting metadata", build_files_count)
    for build_file in build_files:
        # Extract metadata
        progress.update_phase("metadata", 1, current_item=build_file.name)
```

# Step02 - AST Parsing (Single-threaded with timeout handling):
```python
# In ASTAnalyzer._exec_implementation():
step_tracker = StepProgressTracker("step02", "🔍 AST Parsing")

with step_tracker.track_progress(total_files) as progress:
    for file in files:
        try:
            # Parse file with timeout
            progress.update(1, current_item=file.name, status="parsing")
            ast_result = parse_with_timeout(file)
            progress.update_status(current_item=file.name, status="completed")
        except TimeoutError:
            progress.report_timeout(file.name)
        except Exception as e:
            progress.report_error(file.name, str(e))
```

# Step04 - Pattern Analysis (Multi-framework):
```python
# In PatternAnalyzer._exec_implementation():
step_tracker = StepProgressTracker("step04", "⚙️ Pattern Analysis")

with step_tracker.track_progress() as progress:
    # Spring framework analysis
    spring_progress = progress.create_sub_tracker("spring", "🌱 Spring Analysis", spring_configs)
    for config in spring_configs:
        # Analyze Spring config
        spring_progress.update(1, current_item=config.name)
    
    # Hibernate framework analysis  
    hibernate_progress = progress.create_sub_tracker("hibernate", "🔍 Hibernate Analysis", hibernate_configs)
    for config in hibernate_configs:
        # Analyze Hibernate config
        hibernate_progress.update(1, current_item=config.name)
        
    # Struts framework analysis
    struts_progress = progress.create_sub_tracker("struts", "📋 Struts Analysis", struts_configs)
    for config in struts_configs:
        # Analyze Struts config
        struts_progress.update(1, current_item=config.name)
```
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Union

from .progress_manager import CodeSightProgressManager, ProgressStats


class StepStatus(Enum):
    """Status values for step operations."""
    NOT_STARTED = "not_started"
    SCANNING = "scanning"
    PARSING = "parsing" 
    ANALYZING = "analyzing"
    PROCESSING = "processing"
    SAVING = "saving"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


@dataclass
class PhaseInfo:
    """Information about a step phase."""
    name: str
    description: str
    total: int
    completed: int = 0
    status: StepStatus = StepStatus.NOT_STARTED
    current_item: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    
    @property
    def completion_percentage(self) -> float:
        """Calculate phase completion percentage."""
        if self.total == 0:
            return 100.0
        return (self.completed / self.total) * 100


class StepProgressTracker:
    """
    Progress tracker for individual pipeline steps.
    
    Features:
    - Multi-phase progress tracking within a step
    - Sub-tracker creation for framework-specific analysis
    - Error and timeout reporting
    - Status tracking with meaningful messages
    - Integration with main progress manager
    """
    
    def __init__(self, step_id: str, description: str, use_rich: bool = True):
        """
        Initialize step progress tracker.
        
        Args:
            step_id: Unique identifier for the step
            description: Human-readable step description
            use_rich: Whether to use Rich progress bars
        """
        self.step_id = step_id
        self.description = description
        self.use_rich = use_rich
        self._manager: Optional[CodeSightProgressManager] = None
        self._phases: Dict[str, PhaseInfo] = {}
        self._sub_trackers: Dict[str, 'StepProgressTracker'] = {}
        self._errors: List[Dict[str, Any]] = []
        self._timeouts: List[str] = []
        self._lock = threading.Lock()
        
    @contextmanager 
    def track_progress(self, total: Optional[int] = None) -> Generator['StepProgressContext', None, None]:
        """
        Create a progress tracking context for this step.
        
        Args:
            total: Total number of items to process (optional for multi-phase)
            
        Yields:
            StepProgressContext: Progress tracking context
        """
        self._manager = CodeSightProgressManager(use_rich=self.use_rich)
        
        with self._manager.pipeline_context(f"Step: {self.description}") as pipeline:
            step_tracker = pipeline.create_step(self.step_id, self.description, total)
            context = StepProgressContext(self, step_tracker)
            try:
                yield context
            finally:
                step_tracker.complete()
                self._manager = None
    
    def start_phase(self, phase_name: str, description: str, total: int) -> None:
        """Start a new phase within the step."""
        with self._lock:
            self._phases[phase_name] = PhaseInfo(
                name=phase_name,
                description=description,
                total=total,
                status=StepStatus.NOT_STARTED
            )
            
            if self._manager and self._manager.use_rich:
                # Create a task for this phase
                task_id = f"{self.step_id}_{phase_name}"
                self._manager._create_task(task_id, f"  {description}", total)
    
    def update_phase(self, phase_name: str, advance: int = 1, **kwargs: Any) -> None:
        """Update progress for a specific phase."""
        with self._lock:
            if phase_name not in self._phases:
                return
                
            phase = self._phases[phase_name]
            phase.completed += advance
            
            if 'current_item' in kwargs:
                phase.current_item = kwargs['current_item']
            if 'status' in kwargs:
                phase.status = kwargs['status']
                
            if self._manager and self._manager.use_rich:
                task_id = f"{self.step_id}_{phase_name}"
                self._manager._update_task(task_id, advance, **kwargs)
    
    def report_error(self, item_name: str, error_message: str) -> None:
        """Report an error during step processing."""
        with self._lock:
            error_info = {
                'item': item_name,
                'error': error_message,
                'timestamp': time.time()
            }
            self._errors.append(error_info)
            
            if self._manager:
                self._manager._update_task(
                    f"step_{self.step_id}",
                    advance=0,
                    errors=1,
                    current_item=f"❌ Error in {item_name}"
                )
    
    def report_timeout(self, item_name: str) -> None:
        """Report a timeout during step processing."""
        with self._lock:
            self._timeouts.append(item_name)
            
            if self._manager:
                self._manager._update_task(
                    f"step_{self.step_id}",
                    advance=0,
                    current_item=f"⏱️ Timeout: {item_name}"
                )
    
    def get_step_summary(self) -> Dict[str, Any]:
        """Get a summary of step execution."""
        with self._lock:
            total_processed = sum(phase.completed for phase in self._phases.values())
            total_items = sum(phase.total for phase in self._phases.values())
            
            return {
                'step_id': self.step_id,
                'description': self.description,
                'phases': len(self._phases),
                'total_items': total_items,
                'processed_items': total_processed,
                'errors': len(self._errors),
                'timeouts': len(self._timeouts),
                'completion_percentage': (total_processed / total_items * 100) if total_items > 0 else 0,
                'phase_details': {
                    name: {
                        'description': phase.description,
                        'completed': phase.completed,
                        'total': phase.total,
                        'percentage': phase.completion_percentage,
                        'status': phase.status.value
                    }
                    for name, phase in self._phases.items()
                }
            }


class StepProgressContext:
    """Context for step progress tracking operations."""
    
    def __init__(self, step_tracker: StepProgressTracker, main_tracker: Any):
        self.step_tracker = step_tracker
        self.main_tracker = main_tracker
        self._sub_trackers: Dict[str, Any] = {}
    
    def update(self, advance: int = 1, **kwargs: Any) -> None:
        """Update main step progress."""
        self.main_tracker.update(advance, **kwargs)
    
    def update_status(self, **kwargs: Any) -> None:
        """Update step status without advancing progress."""
        self.main_tracker.update(0, **kwargs)
    
    def start_phase(self, phase_name: str, description: str, total: int) -> None:
        """Start a new phase within the step."""
        self.step_tracker.start_phase(phase_name, description, total)
    
    def update_phase(self, phase_name: str, advance: int = 1, **kwargs: Any) -> None:
        """Update progress for a specific phase."""
        self.step_tracker.update_phase(phase_name, advance, **kwargs)
    
    def create_sub_tracker(self, sub_id: str, description: str, total: int) -> Union['SubTracker', 'BasicSubTracker']:
        """Create a sub-tracker for framework-specific analysis."""
        if self.step_tracker._manager and self.step_tracker._manager.use_rich:
            task_id = f"{self.step_tracker.step_id}_{sub_id}"
            task = self.step_tracker._manager._create_task(task_id, f"  {description}", total)
            sub_tracker = SubTracker(self.step_tracker._manager, task_id, description, total)
            self._sub_trackers[sub_id] = sub_tracker
            return sub_tracker
        else:
            # Basic fallback
            print(f"  📋 {description}")
            return BasicSubTracker(description, total)
    
    def report_error(self, item_name: str, error_message: str) -> None:
        """Report an error during step processing."""
        self.step_tracker.report_error(item_name, error_message)
    
    def report_timeout(self, item_name: str) -> None:
        """Report a timeout during step processing."""
        self.step_tracker.report_timeout(item_name)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get step execution summary."""
        return self.step_tracker.get_step_summary()


class SubTracker:
    """Sub-tracker for framework-specific or sub-component analysis."""
    
    def __init__(self, manager: CodeSightProgressManager, task_id: str, 
                 description: str, total: int):
        self.manager = manager
        self.task_id = task_id
        self.description = description
        self.total = total
        self.completed = 0
    
    def update(self, advance: int = 1, **kwargs: Any) -> None:
        """Update sub-tracker progress."""
        self.completed += advance
        self.manager._update_task(self.task_id, advance, **kwargs)
    
    def complete(self) -> None:
        """Mark sub-tracker as completed."""
        self.manager._complete_task(self.task_id)


class BasicSubTracker:
    """Basic fallback sub-tracker when Rich is not available."""
    
    def __init__(self, description: str, total: int):
        self.description = description
        self.total = total
        self.completed = 0
    
    def update(self, advance: int = 1, **kwargs: Any) -> None:
        """Update progress with basic output."""
        self.completed += advance
        percentage = (self.completed / self.total) * 100
        current_item = kwargs.get('current_item', '')
        print(f"\r    {self.description}: {percentage:.1f}% ({self.completed}/{self.total}) {current_item}", 
              end="", flush=True)
    
    def complete(self) -> None:
        """Mark as completed."""
        print(f"\n    ✅ {self.description} completed: {self.completed}/{self.total}")
