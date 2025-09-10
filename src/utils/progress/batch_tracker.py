"""
Batch Progress Tracker

Specialized progress tracking for multi-threaded batch operations in CodeSight.
Handles concurrent processing with thread-safe progress updates.

USAGE EXAMPLES:

# Step03 - Embeddings Analysis (Multi-threaded batches):
```python
from utils.progress import BatchProgressTracker
import threading

# In EmbeddingsAnalyzer._exec_implementation():
batch_tracker = BatchProgressTracker("step03", "🧠 Embeddings Analysis")

with batch_tracker.track_batches(total_files) as tracker:
    # Create batches for concurrent processing
    batch_size = 32
    batches = tracker.create_batches([
        ("batch1", "📦 Batch 1 (Thread 1)", batch_size),
        ("batch2", "📦 Batch 2 (Thread 2)", batch_size)
    ])
    
    def process_batch1():
        batch1 = batches["batch1"]
        for item in batch1_items:
            try:
                # Generate embeddings
                embeddings = generate_embeddings(item)
                batch1.update(1, current_item=item.name, status="embedding")
                
                # Save embeddings  
                save_embeddings(embeddings)
                batch1.update_status(current_item=item.name, status="saved")
                
            except Exception as e:
                batch1.report_error(item.name, str(e))
    
    def process_batch2():
        batch2 = batches["batch2"]
        for item in batch2_items:
            try:
                # Generate embeddings
                embeddings = generate_embeddings(item)
                batch2.update(1, current_item=item.name)
            except Exception as e:
                batch2.report_error(item.name, str(e))
    
    # Start threads
    threads = [
        threading.Thread(target=process_batch1),
        threading.Thread(target=process_batch2)
    ]
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
```

# Step05 - LLM Analysis (Batched with retries):
```python
# In LLMAnalyzer._exec_implementation():
batch_tracker = BatchProgressTracker("step05", "🧠 LLM Analysis")

with batch_tracker.track_batches(total_files) as tracker:
    batches = tracker.create_batches([
        ("batch1", "🤖 GPT-4 Batch 1", 5),
        ("batch2", "🤖 GPT-4 Batch 2", 5),
        ("batch3", "🤖 GPT-4 Batch 3", 5)
    ])
    
    def process_llm_batch(batch_id: str, items: List[Any]):
        batch = batches[batch_id]
        
        for item in items:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Call LLM with timeout
                    batch.update_status(current_item=item.name, status="calling_llm")
                    
                    result = call_llm_with_timeout(item)
                    batch.update(1, current_item=item.name, status="completed")
                    break
                    
                except TimeoutError:
                    retry_count += 1
                    batch.report_retry(item.name, retry_count)
                    if retry_count >= max_retries:
                        batch.report_error(item.name, "Max retries exceeded")
                        break
                        
                except Exception as e:
                    batch.report_error(item.name, str(e))
                    break
    
    # Process batches concurrently
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(process_llm_batch, "batch1", batch1_items),
            executor.submit(process_llm_batch, "batch2", batch2_items), 
            executor.submit(process_llm_batch, "batch3", batch3_items)
        ]
        
        for future in futures:
            future.result()
```

# Step06 - Relationship Mapping (Parallel analysis):
```python
# In RelationshipMapper._exec_implementation():
batch_tracker = BatchProgressTracker("step06", "🔗 Relationship Mapping")

with batch_tracker.track_batches() as tracker:
    # Create trackers for different relationship types
    trackers = tracker.create_batches([
        ("service_interactions", "🔄 Service Interactions", service_count),
        ("data_flows", "📊 Data Flow Analysis", flow_count),
        ("dependencies", "🔍 Dependency Analysis", dependency_count)
    ])
    
    def analyze_service_interactions():
        tracker = trackers["service_interactions"]
        for service in services:
            # Analyze service interactions
            interactions = find_service_interactions(service)
            tracker.update(1, current_item=service.name)
    
    def analyze_data_flows():
        tracker = trackers["data_flows"]
        for component in components:
            # Analyze data flows
            flows = analyze_data_flows(component)
            tracker.update(1, current_item=component.name)
    
    def analyze_dependencies():
        tracker = trackers["dependencies"]
        for module in modules:
            # Analyze dependencies
            deps = find_dependencies(module)
            tracker.update(1, current_item=module.name)
    
    # Run analysis in parallel
    import threading
    threads = [
        threading.Thread(target=analyze_service_interactions),
        threading.Thread(target=analyze_data_flows),
        threading.Thread(target=analyze_dependencies)
    ]
    
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
```
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from .progress_manager import CodeSightProgressManager


class BatchStatus(Enum):
    """Status values for batch operations."""
    PENDING = "pending"
    PROCESSING = "processing"
    CALLING_LLM = "calling_llm"
    WAITING_RESPONSE = "waiting_response"
    SAVING = "saving"
    COMPLETED = "completed"
    ERROR = "error"
    RETRYING = "retrying"


@dataclass
class BatchStats:
    """Statistics for batch processing."""
    batch_id: str
    description: str
    total_items: int
    processed_items: int = 0
    successful_items: int = 0
    error_items: int = 0
    retry_attempts: int = 0
    start_time: float = field(default_factory=time.time)
    current_item: Optional[str] = None
    status: BatchStatus = BatchStatus.PENDING
    
    @property
    def completion_percentage(self) -> float:
        """Calculate batch completion percentage."""
        if self.total_items == 0:
            return 100.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.processed_items == 0:
            return 0.0
        return (self.successful_items / self.processed_items) * 100
    
    @property
    def processing_rate(self) -> float:
        """Calculate items per second."""
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return self.processed_items / elapsed


class BatchProgressTracker:
    """
    Progress tracker for multi-threaded batch operations.
    
    Features:
    - Thread-safe batch progress tracking
    - Concurrent batch execution monitoring
    - Error and retry reporting per batch
    - Performance metrics and success rates
    - Integration with main progress manager
    """
    
    def __init__(self, step_id: str, description: str, use_rich: bool = True):
        """
        Initialize batch progress tracker.
        
        Args:
            step_id: Unique identifier for the step
            description: Human-readable step description  
            use_rich: Whether to use Rich progress bars
        """
        self.step_id = step_id
        self.description = description
        self.use_rich = use_rich
        self._manager: Optional[CodeSightProgressManager] = None
        self._batch_stats: Dict[str, BatchStats] = {}
        self._lock = threading.Lock()
        
    @contextmanager
    def track_batches(self, total: Optional[int] = None) -> Any:
        """
        Create a batch tracking context.
        
        Args:
            total: Total number of items across all batches
            
        Yields:
            BatchTrackingContext: Batch tracking context
        """
        self._manager = CodeSightProgressManager(use_rich=self.use_rich)
        
        with self._manager.pipeline_context(f"Step: {self.description}") as pipeline:
            step_tracker = pipeline.create_step(self.step_id, self.description, total)
            context = BatchTrackingContext(self, step_tracker)
            try:
                yield context
            finally:
                step_tracker.complete()
                self._manager = None
    
    def _create_batch_tracker(self, batch_id: str, description: str, total: int) -> Union['BatchTracker', 'BasicBatchTracker']:
        """Create a tracker for a specific batch."""
        with self._lock:
            stats = BatchStats(
                batch_id=batch_id,
                description=description,
                total_items=total
            )
            self._batch_stats[batch_id] = stats
            
            if self._manager and self._manager.use_rich:
                task_id = f"{self.step_id}_{batch_id}"
                self._manager._create_task(task_id, f"  {description}", total)
                return BatchTracker(self._manager, task_id, stats, self)
            else:
                return BasicBatchTracker(stats, self)
    
    def get_batch_summary(self) -> Dict[str, Any]:
        """Get summary of all batch operations."""
        with self._lock:
            total_items = sum(stats.total_items for stats in self._batch_stats.values())
            processed_items = sum(stats.processed_items for stats in self._batch_stats.values())
            successful_items = sum(stats.successful_items for stats in self._batch_stats.values())
            error_items = sum(stats.error_items for stats in self._batch_stats.values())
            retry_attempts = sum(stats.retry_attempts for stats in self._batch_stats.values())
            
            return {
                'step_id': self.step_id,
                'description': self.description,
                'total_batches': len(self._batch_stats),
                'total_items': total_items,
                'processed_items': processed_items,
                'successful_items': successful_items,
                'error_items': error_items,
                'retry_attempts': retry_attempts,
                'overall_success_rate': (successful_items / processed_items * 100) if processed_items > 0 else 0,
                'batch_details': {
                    batch_id: {
                        'description': stats.description,
                        'total': stats.total_items,
                        'processed': stats.processed_items,
                        'successful': stats.successful_items,
                        'errors': stats.error_items,
                        'retries': stats.retry_attempts,
                        'completion_percentage': stats.completion_percentage,
                        'success_rate': stats.success_rate,
                        'processing_rate': stats.processing_rate,
                        'status': stats.status.value
                    }
                    for batch_id, stats in self._batch_stats.items()
                }
            }


class BatchTrackingContext:
    """Context for batch tracking operations."""
    
    def __init__(self, batch_tracker: BatchProgressTracker, main_tracker: Any):
        self.batch_tracker = batch_tracker
        self.main_tracker = main_tracker
        self._batch_trackers: Dict[str, Union['BatchTracker', 'BasicBatchTracker']] = {}
    
    def create_batch(self, batch_id: str, description: str, total: int) -> Union['BatchTracker', 'BasicBatchTracker']:
        """Create a single batch tracker."""
        tracker = self.batch_tracker._create_batch_tracker(batch_id, description, total)
        self._batch_trackers[batch_id] = tracker
        return tracker
    
    def create_batches(self, batch_configs: List[Tuple[str, str, int]]) -> Dict[str, Union['BatchTracker', 'BasicBatchTracker']]:
        """
        Create multiple batch trackers.
        
        Args:
            batch_configs: List of (batch_id, description, total) tuples
            
        Returns:
            Dictionary mapping batch_id to BatchTracker
        """
        trackers = {}
        for batch_id, description, total in batch_configs:
            trackers[batch_id] = self.create_batch(batch_id, description, total)
        return trackers
    
    def wait_for_batches(self, batch_trackers: List[Union['BatchTracker', 'BasicBatchTracker']], timeout: Optional[float] = None) -> bool:
        """
        Wait for multiple batches to complete.
        
        Args:
            batch_trackers: List of batch trackers to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all batches completed, False if timeout
        """
        start_time = time.time()
        
        while True:
            all_complete = all(tracker.is_complete() for tracker in batch_trackers)
            if all_complete:
                return True
                
            if timeout and (time.time() - start_time) > timeout:
                return False
                
            time.sleep(0.1)  # Short sleep to avoid busy waiting
    
    def get_summary(self) -> Dict[str, Any]:
        """Get batch execution summary."""
        return self.batch_tracker.get_batch_summary()


class BatchTracker:
    """Tracker for individual batch operations with Rich progress."""
    
    def __init__(self, manager: CodeSightProgressManager, task_id: str, 
                 stats: BatchStats, parent: BatchProgressTracker):
        self.manager = manager
        self.task_id = task_id
        self.stats = stats
        self.parent = parent
        self._complete = False
        self._lock = threading.Lock()
    
    def update(self, advance: int = 1, **kwargs: Any) -> None:
        """Update batch progress."""
        with self._lock:
            self.stats.processed_items += advance
            
            if 'current_item' in kwargs:
                self.stats.current_item = kwargs['current_item']
            if 'status' in kwargs:
                self.stats.status = BatchStatus(kwargs['status'])
            
            # Count successful items (items that completed without error)
            if kwargs.get('status') == 'completed':
                self.stats.successful_items += 1
            
            self.manager._update_task(self.task_id, advance, **kwargs)
    
    def update_status(self, **kwargs: Any) -> None:
        """Update batch status without advancing progress."""
        with self._lock:
            if 'current_item' in kwargs:
                self.stats.current_item = kwargs['current_item']
            if 'status' in kwargs:
                self.stats.status = BatchStatus(kwargs['status'])
                
            self.manager._update_task(self.task_id, 0, **kwargs)
    
    def report_error(self, item_name: str, error_message: str) -> None:
        """Report an error in batch processing."""
        with self._lock:
            self.stats.error_items += 1
            self.stats.processed_items += 1  # Count as processed even if failed
            
            self.manager._update_task(
                self.task_id,
                advance=1,
                errors=1,
                current_item=f"❌ Error: {item_name}",
                status="error"
            )
    
    def report_retry(self, item_name: str, retry_count: int) -> None:
        """Report a retry attempt in batch processing."""
        with self._lock:
            self.stats.retry_attempts += 1
            self.stats.status = BatchStatus.RETRYING
            
            self.manager._update_task(
                self.task_id,
                advance=0,
                retries=1,
                current_item=f"🔄 Retry {retry_count}: {item_name}",
                status="retrying"
            )
    
    def complete(self) -> None:
        """Mark batch as completed."""
        with self._lock:
            self._complete = True
            self.stats.status = BatchStatus.COMPLETED
            self.manager._complete_task(self.task_id)
    
    def is_complete(self) -> bool:
        """Check if batch is completed."""
        with self._lock:
            return self._complete or self.stats.processed_items >= self.stats.total_items


class BasicBatchTracker:
    """Basic fallback batch tracker when Rich is not available."""
    
    def __init__(self, stats: BatchStats, parent: BatchProgressTracker):
        self.stats = stats
        self.parent = parent
        self._complete = False
        self._lock = threading.Lock()
    
    def update(self, advance: int = 1, **kwargs: Any) -> None:
        """Update progress with basic output."""
        with self._lock:
            self.stats.processed_items += advance
            
            if 'current_item' in kwargs:
                self.stats.current_item = kwargs['current_item']
                
            percentage = self.stats.completion_percentage
            rate = self.stats.processing_rate
            current_item = self.stats.current_item or ""
            
            print(f"\r  {self.stats.description}: {percentage:.1f}% "
                  f"({self.stats.processed_items}/{self.stats.total_items}) "
                  f"[{rate:.1f} items/s] {current_item}", end="", flush=True)
    
    def update_status(self, **kwargs: Any) -> None:
        """Update status without advancing progress."""
        self.update(0, **kwargs)
    
    def report_error(self, item_name: str, error_message: str) -> None:
        """Report error with basic output."""
        with self._lock:
            self.stats.error_items += 1
            self.stats.processed_items += 1
            print(f"\n    ❌ Error in {item_name}: {error_message}")
    
    def report_retry(self, item_name: str, retry_count: int) -> None:
        """Report retry with basic output."""
        with self._lock:
            self.stats.retry_attempts += 1
            print(f"\n    🔄 Retry {retry_count} for {item_name}")
    
    def complete(self) -> None:
        """Mark as completed."""
        with self._lock:
            self._complete = True
            print(f"\n  ✅ {self.stats.description} completed: "
                  f"{self.stats.successful_items}/{self.stats.total_items} successful")
    
    def is_complete(self) -> bool:
        """Check if completed."""
        with self._lock:
            return self._complete or self.stats.processed_items >= self.stats.total_items
