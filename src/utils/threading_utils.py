"""Threading utilities copied from modernization-project-flow."""

import concurrent.futures
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union


class ThreadingUtils:
    """
    Threading utilities (copied from modernization-project-flow) responsible for:
    - Thread pool management
    - Parallel processing coordination
    - Thread-safe operations
    - Resource synchronization
    """
    
    @staticmethod
    def execute_parallel(
        tasks: List[Callable],
        max_workers: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> List[Union[Any, Exception]]:
        """
        Execute tasks in parallel using ThreadPoolExecutor.
        
        Args:
            tasks: List of callable tasks
            max_workers: Maximum number of worker threads
            timeout: Timeout for all tasks
            
        Returns:
            List of results in same order as tasks (results or exceptions)
        """
        if not tasks:
            return []
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_task = {executor.submit(task): i for i, task in enumerate(tasks)}
            
            # Collect results in order
            task_results: List[Union[Any, Exception]] = [None] * len(tasks)
            
            for future in concurrent.futures.as_completed(future_to_task, timeout=timeout):
                task_index = future_to_task[future]
                try:
                    result = future.result()
                    task_results[task_index] = result
                except Exception as e:  # pylint: disable=broad-except
                    task_results[task_index] = e
            
            results = task_results
        
        return results
    
    @staticmethod
    def execute_with_timeout(func: Callable[..., Any], timeout: float, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with timeout.
        
        Args:
            func: Function to execute
            timeout: Timeout in seconds
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            TimeoutError: If function exceeds timeout
        """
        result: List[Optional[Any]] = [None]
        exception: List[Optional[Exception]] = [None]
        
        def target() -> None:
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:  # pylint: disable=broad-except
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Function execution exceeded {timeout} seconds")
        
        stored_exception = exception[0]
        if stored_exception is not None:
            raise stored_exception
        
        return result[0]
    
    @staticmethod
    def create_thread_safe_counter() -> 'ThreadSafeCounter':
        """Create a thread-safe counter."""
        return ThreadSafeCounter()


class ThreadSafeCounter:
    """Thread-safe counter for tracking progress across threads."""
    
    def __init__(self, initial_value: int = 0):
        self._value = initial_value
        self._lock = threading.Lock()
    
    def increment(self, amount: int = 1) -> int:
        """Increment counter and return new value."""
        with self._lock:
            self._value += amount
            return self._value
    
    def decrement(self, amount: int = 1) -> int:
        """Decrement counter and return new value."""
        with self._lock:
            self._value -= amount
            return self._value
    
    @property
    def value(self) -> int:
        """Get current counter value."""
        with self._lock:
            return self._value
    
    def reset(self, value: int = 0) -> None:
        """Reset counter to specified value."""
        with self._lock:
            self._value = value
