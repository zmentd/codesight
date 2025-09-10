"""
CodeSight Progress Manager

Central progress coordinator for the entire CodeSight pipeline.
Manages hierarchical progress tracking with support for single-threaded
and multi-threaded operations.

USAGE EXAMPLES:

# Single Step Usage (Step01 - File System Analysis):
# In FilesystemAnalyzer._exec_implementation():
# progress_manager = CodeSightProgressManager()
# with progress_manager.pipeline_context("CodeSight Analysis") as pipeline:
#     step_tracker = pipeline.create_step("step01", "📁 File System Analysis", total_files)
#     
#     # Scanning phase
#     for file in files:
#         # Process file
#         step_tracker.update(1, current_file=file.name)
#         
#     step_tracker.complete()

# Multi-threaded Usage (Step03 - Embeddings):
# In EmbeddingsAnalyzer._exec_implementation():
# progress_manager = CodeSightProgressManager()
# with progress_manager.pipeline_context("CodeSight Analysis") as pipeline:
#     step_tracker = pipeline.create_step("step03", "🧠 Embeddings Analysis", total_files)
#     
#     # Create batch trackers for threads
#     batch1 = step_tracker.create_batch("batch1", "📦 Batch 1 (Thread 1)", batch_size)
#     batch2 = step_tracker.create_batch("batch2", "📦 Batch 2 (Thread 2)", batch_size)
#     
#     # Thread 1
#     def process_batch1():
#         for item in batch1_items:
#             # Process embeddings
#             batch1.update(1, current_item=item.name)
#             
#     # Thread 2  
#     def process_batch2():
#         for item in batch2_items:
#             # Process embeddings
#             batch2.update(1, current_item=item.name)
#     
#     # Run threads
#     import threading
#     t1 = threading.Thread(target=process_batch1)
#     t2 = threading.Thread(target=process_batch2)
#     t1.start()
#     t2.start()
#     t1.join()
#     t2.join()
#     
#     step_tracker.complete()

# Multi-step Pipeline Usage:
# In CodeSightFlow.run_analysis():
# progress_manager = CodeSightProgressManager()
# with progress_manager.pipeline_context("CodeSight Analysis") as pipeline:
#     # Overall pipeline progress
#     pipeline_tracker = pipeline.create_overall_tracker(7)  # 7 steps total
#     
#     # Step 1
#     step1 = pipeline.create_step("step01", "📁 File System", file_count)
#     # ... run step01
#     step1.complete()
#     pipeline_tracker.update(1)
#     
#     # Step 3 (multi-threaded)
#     step3 = pipeline.create_step("step03", "🧠 Embeddings", embedding_count)
#     batch1 = step3.create_batch("batch1", "📦 Thread 1", batch_size)
#     batch2 = step3.create_batch("batch2", "📦 Thread 2", batch_size)
#     # ... run step03
#     step3.complete()
#     pipeline_tracker.update(1)
#     
#     # Continue with other steps...
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, Optional, Union

try:
    from pip._vendor.rich.console import Console, Group
    from pip._vendor.rich.live import Live
    from pip._vendor.rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


@dataclass
class ProgressStats:
    """Statistics for progress tracking."""
    start_time: float = field(default_factory=time.time)
    items_processed: int = 0
    total_items: int = 0
    errors: int = 0
    retries: int = 0
    current_item: Optional[str] = None
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.items_processed / self.total_items) * 100
    
    @property
    def processing_rate(self) -> float:
        """Calculate items per second."""
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return self.items_processed / elapsed
    
    @property
    def eta_seconds(self) -> float:
        """Estimate time to completion in seconds."""
        if self.processing_rate == 0 or self.items_processed == 0:
            return 0.0
        remaining_items = self.total_items - self.items_processed
        return remaining_items / self.processing_rate


class CodeSightProgressManager:
    """
    Central progress manager for CodeSight pipeline operations.
    
    Features:
    - Hierarchical progress tracking (Pipeline > Steps > Batches)
    - Thread-safe operations
    - Rich progress bars with fallback to basic output
    - Performance metrics and ETA calculations
    - Error and retry tracking
    """
    
    def __init__(self, use_rich: bool = True):
        """
        Initialize progress manager.
        
        Args:
            use_rich: Whether to use Rich progress bars (auto-detects if available)
        """
        self.use_rich = use_rich and RICH_AVAILABLE
        self._progress: Optional[Any] = None
        self._text_progress: Optional[Any] = None
        self._console = Console()
        self._live: Optional[Live] = None
        self._tasks: Dict[str, Any] = {}
        self._text_tasks: Dict[str, Any] = {}
        self._stats: Dict[str, ProgressStats] = {}
        self._lock = threading.Lock()
        
    @contextmanager
    def pipeline_context(self, title: str = "CodeSight Analysis") -> Generator['PipelineTracker', None, None]:
        """
        Create a pipeline-level progress context.
        
        Args:
            title: Title for the overall pipeline
            
        Yields:
            PipelineTracker: Pipeline-level progress tracker
        """
        if not self.use_rich:
            # Fallback to basic implementation
            tracker = PipelineTracker(self, title)
            yield tracker
            return
            
        # Main progress with bars for actual progress tracking
        main_progress = Progress(
            TextColumn("[bold]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self._console,
            refresh_per_second=10
        )
        
        # Text-only progress for analysis results (no progress bars)
        text_progress = Progress(
            TextColumn("[bold]{task.description}"),
            console=self._console,
            transient=False  # Keep messages visible
        )
        
        # Group them together
        progress_group = Group(
            main_progress,
            text_progress
        )
        
        with Live(progress_group, console=self._console, refresh_per_second=10) as live:
            self._progress = main_progress
            self._text_progress = text_progress
            self._live = live
            
            tracker = PipelineTracker(self, title)
            try:
                yield tracker
            finally:
                self._progress = None
                self._text_progress = None
                self._live = None
    
    def _create_task(self, task_id: str, description: str, total: Optional[int] = None) -> Any:
        """Create a new progress task."""
        with self._lock:
            if self._progress:
                task = self._progress.add_task(description, total=total)
                self._tasks[task_id] = task
                self._stats[task_id] = ProgressStats(total_items=total or 0)
                return task
            else:
                # Basic implementation
                self._stats[task_id] = ProgressStats(total_items=total or 0)
                print(f"📋 {description}")
                return task_id
    
    def _update_task(self, task_id: str, advance: int = 1, **kwargs: Any) -> None:
        """Update a progress task."""
        with self._lock:
            if task_id not in self._stats:
                return
                
            stats = self._stats[task_id]
            stats.items_processed += advance
            
            # Update additional stats
            if 'current_item' in kwargs:
                stats.current_item = kwargs['current_item']
            if 'errors' in kwargs:
                stats.errors += kwargs['errors']
            if 'retries' in kwargs:
                stats.retries += kwargs['retries']
            
            if self._progress and task_id in self._tasks:
                # Update Rich progress
                task = self._tasks[task_id]
                
                # Build description with current item
                description = kwargs.get('description', '')
                if stats.current_item:
                    description = f"{description}: {stats.current_item}"
                
                self._progress.update(
                    task, 
                    advance=advance,
                    description=description if description else None
                )
            else:
                # Basic progress update
                if stats.total_items > 0:
                    percent = stats.completion_percentage
                    rate = stats.processing_rate
                    print(f"\r  Progress: {percent:.1f}% ({stats.items_processed}/{stats.total_items}) "
                          f"[{rate:.1f} items/s]", end="", flush=True)
    
    def _complete_task(self, task_id: str) -> None:
        """Mark a task as completed."""
        with self._lock:
            if task_id in self._stats:
                stats = self._stats[task_id]
                if not self.use_rich:
                    print(f"\n✅ Completed: {stats.items_processed} items processed")

    def display_analysis_result(self, result_id: str, message: str, 
                              result_type: str = "info") -> None:
        """Display an analysis result message that completes immediately."""
        with self._lock:
            if self._text_progress:
                # Add styling based on result type
                if result_type == "success":
                    styled_message = f"✅ {message}"
                elif result_type == "warning":
                    styled_message = f"⚠️ {message}"
                elif result_type == "error":
                    styled_message = f"❌ {message}"
                else:
                    styled_message = f"📊 {message}"
                
                # Add task and immediately complete it with final message
                task_id = self._text_progress.add_task(styled_message, total=None)
                self._text_tasks[result_id] = task_id
                
                # Stop the task to keep it visible but not updating
                self._text_progress.stop_task(task_id)
            else:
                # Fallback to simple print
                print(f"📊 {message}")

    def _update_total(self, task_id: str, new_total: int) -> None:
        """Update the total count for a specific task."""
        with self._lock:
            if task_id in self._tasks and self._progress:
                task = self._tasks[task_id]
                self._progress.update(task, total=new_total)
            if task_id in self._stats:
                self._stats[task_id].total_items = new_total


class PipelineTracker:
    """Tracks progress for the entire CodeSight pipeline."""
    
    def __init__(self, manager: 'CodeSightProgressManager', title: str):
        self.manager = manager
        self.title = title
        self._steps: Dict[str, 'StepTracker'] = {}
        self._overall_task_id: Optional[str] = None
        
    def create_overall_tracker(self, total_steps: int) -> 'OverallTracker':
        """Create an overall pipeline progress tracker."""
        self._overall_task_id = f"pipeline_{id(self)}"
        self.manager._create_task(
            self._overall_task_id,
            f"🎯 {self.title}",
            total_steps
        )
        return OverallTracker(self.manager, self._overall_task_id)
    
    def create_step(self, step_id: str, description: str, total: Optional[int] = None) -> 'StepTracker':
        """Create a step-level progress tracker."""
        tracker = StepTracker(self.manager, step_id, description, total)
        self._steps[step_id] = tracker
        return tracker


class OverallTracker:
    """Tracks overall pipeline progress across all steps."""
    
    def __init__(self, manager: 'CodeSightProgressManager', task_id: str):
        self.manager = manager
        self.task_id = task_id
    
    def update(self, steps_completed: int = 1, current_step: Optional[str] = None) -> None:
        """Update overall pipeline progress."""
        self.manager._update_task(
            self.task_id, 
            advance=steps_completed,
            current_item=current_step
        )
    
    def complete(self) -> None:
        """Mark overall pipeline as completed."""
        self.manager._complete_task(self.task_id)


class StepTracker:
    """Tracks progress for a single pipeline step."""
    
    def __init__(self, manager: 'CodeSightProgressManager', step_id: str, 
                 description: str, total: Optional[int] = None):
        self.manager = manager
        self.step_id = step_id
        self.description = description
        self.total = total
        self._batches: Dict[str, 'BatchTracker'] = {}
        self._phases: Dict[str, str] = {}  # phase_name -> task_id mapping
        
        # Create the main step task
        self.task_id = f"step_{step_id}"
        self.manager._create_task(self.task_id, description, total)
    
    def update(self, advance: int = 1, **kwargs: Any) -> None:
        """Update step progress."""
        self.manager._update_task(self.task_id, advance, **kwargs)
    
    def create_batch(self, batch_id: str, description: str, total: int) -> 'BatchTracker':
        """Create a batch tracker for multi-threaded operations."""
        full_batch_id = f"{self.step_id}_{batch_id}"
        tracker = BatchTracker(self.manager, full_batch_id, description, total, self)
        self._batches[batch_id] = tracker
        return tracker
    
    def track_progress(self, total: Optional[int] = None) -> 'StepProgressContext':
        """Create context manager for phase-based progress tracking."""
        if total is not None:
            self.total = total
            # Update the task total if needed
        return StepProgressContext(self)
    
    def start_phase(self, phase_name: str, description: str, total: int) -> None:
        """Start a new phase within this step."""
        phase_task_id = f"{self.step_id}_{phase_name}"
        self.manager._create_task(phase_task_id, f"  {description}", total)
        self._phases[phase_name] = phase_task_id
    
    def update_phase(self, phase_name: str, advance: int = 1, **kwargs: Any) -> None:
        """Update progress for a specific phase."""
        if phase_name in self._phases:
            phase_task_id = self._phases[phase_name]
            self.manager._update_task(phase_task_id, advance, **kwargs)
    
    def update_phase_total(self, phase_name: str, new_total: int) -> None:
        """Update the total count for a specific phase."""
        if phase_name in self._phases:
            phase_task_id = self._phases[phase_name]
            # Update the task total in the progress manager
            if phase_task_id in self.manager._tasks:
                task = self.manager._tasks[phase_task_id]
                if self.manager.use_rich and self.manager._progress:
                    self.manager._progress.update(task, total=new_total)
            # Update the stats total
            if phase_task_id in self.manager._stats:
                self.manager._stats[phase_task_id].total_items = new_total
    
    def display_result(self, message: str, result_type: str = "info") -> None:
        """Display an analysis result through the progress manager."""
        result_id = f"{self.step_id}_result_{int(time.time())}"
        self.manager.display_analysis_result(result_id, message, result_type)
    
    def print_message(self, message: str) -> None:
        """Print a simple status message."""
        self.display_result(message, "info")
    
    def complete(self) -> None:
        """Mark step as completed."""
        self.manager._complete_task(self.task_id)
        
        # Complete all phases
        for phase_task_id in self._phases.values():
            self.manager._complete_task(phase_task_id)
        
        # Complete all batches
        for batch in self._batches.values():
            batch.complete()


class StepProgressContext:
    """Context manager for phase-based progress tracking within a step."""
    
    def __init__(self, step_tracker: StepTracker):
        self.step_tracker = step_tracker
        self._current_phase: Optional[str] = None
    
    def __enter__(self) -> 'StepProgressContext':
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Complete current phase if any
        if self._current_phase and self._current_phase in self.step_tracker._phases:
            phase_task_id = self.step_tracker._phases[self._current_phase]
            self.step_tracker.manager._complete_task(phase_task_id)
    
    def start_phase(self, phase_name: str, description: str, total: int) -> None:
        """Start a new phase within the step."""
        # Complete previous phase if any
        if self._current_phase and self._current_phase in self.step_tracker._phases:
            phase_task_id = self.step_tracker._phases[self._current_phase]
            self.step_tracker.manager._complete_task(phase_task_id)
        
        # Start new phase
        self.step_tracker.start_phase(phase_name, description, total)
        self._current_phase = phase_name
    
    def update(self, advance: int = 1, **kwargs: Any) -> None:
        """Update progress for current phase."""
        if self._current_phase:
            self.step_tracker.update_phase(self._current_phase, advance, **kwargs)
        else:
            # Fallback to step-level update
            self.step_tracker.update(advance, **kwargs)
    
    def update_total(self, new_total: int) -> None:
        """Update the total count for the current phase."""
        if self._current_phase and self._current_phase in self.step_tracker._phases:
            phase_task_id = self.step_tracker._phases[self._current_phase]
            # Update the task total in the progress manager
            if phase_task_id in self.step_tracker.manager._tasks:
                task = self.step_tracker.manager._tasks[phase_task_id]
                if self.step_tracker.manager.use_rich and self.step_tracker.manager._progress:
                    self.step_tracker.manager._progress.update(task, total=new_total)
            # Update the stats total
            if phase_task_id in self.step_tracker.manager._stats:
                self.step_tracker.manager._stats[phase_task_id].total_items = new_total
    
    def display_result(self, message: str, result_type: str = "info") -> None:
        """Display an analysis result through the progress manager."""
        self.step_tracker.display_result(message, result_type)
    
    def print_message(self, message: str) -> None:
        """Print a simple message without progress tracking."""
        self.display_result(message, "info")
    
    def create_subtask(self, subtask_id: str, description: str, total: int) -> 'SubtaskTracker':
        """Create a new subtask tracker that doesn't interfere with the current phase."""
        return SubtaskTracker(self.step_tracker.manager, subtask_id, description, total)


class SubtaskTracker:
    """Independent progress tracker for sub-operations that doesn't interfere with parent context."""
    
    def __init__(self, manager: 'CodeSightProgressManager', subtask_id: str, 
                 description: str, total: int):
        self.manager = manager
        self.subtask_id = subtask_id
        self.description = description
        self.total = total
        
        # Create the subtask progress task
        self.task_id = f"subtask_{subtask_id}"
        self.manager._create_task(self.task_id, description, total)
    
    def update(self, advance: int = 1, **kwargs: Any) -> None:
        """Update subtask progress."""
        self.manager._update_task(self.task_id, advance, **kwargs)
    
    def complete(self) -> None:
        """Mark subtask as completed."""
        self.manager._complete_task(self.task_id)
    
    def __enter__(self) -> 'SubtaskTracker':
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.complete()


class BatchTracker:
    """Tracks progress for a batch operation (typically multi-threaded)."""
    
    def __init__(self, manager: 'CodeSightProgressManager', batch_id: str,
                 description: str, total: int, parent_step: StepTracker):
        self.manager = manager
        self.batch_id = batch_id
        self.description = description
        self.total = total
        self.parent_step = parent_step
        
        # Create the batch task
        self.task_id = f"batch_{batch_id}"
        self.manager._create_task(self.task_id, description, total)
    
    def update(self, advance: int = 1, **kwargs: Any) -> None:
        """Update batch progress."""
        self.manager._update_task(self.task_id, advance, **kwargs)
        
        # Also update parent step
        self.parent_step.update(advance, **kwargs)
    
    def complete(self) -> None:
        """Mark batch as completed."""
        self.manager._complete_task(self.task_id)
    
    def report_error(self, error_count: int = 1) -> None:
        """Report errors in batch processing."""
        self.manager._update_task(self.task_id, advance=0, errors=error_count)
    
    def report_retry(self, retry_count: int = 1) -> None:
        """Report retries in batch processing."""
        self.manager._update_task(self.task_id, advance=0, retries=retry_count)


# Convenience function for simple single-step progress
@contextmanager
def simple_progress(description: str, total: int, use_rich: bool = True) -> Generator['StepTracker', None, None]:
    """
    Simple progress context for basic operations.
    
    USAGE:
    with simple_progress("Processing files", len(files)) as progress:
        for file in files:
            # Process file
            progress.update(1, current_item=file.name)
    """
    manager = CodeSightProgressManager(use_rich=use_rich)
    with manager.pipeline_context() as pipeline:
        tracker = pipeline.create_step("simple", description, total)
        yield tracker
        tracker.complete()
