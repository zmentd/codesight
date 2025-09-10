"""Console-based logging handler for CodeSight."""

import logging
import sys


class ConsoleHandler:
    """
    Console-based logging handler responsible for:
    - Console output formatting
    - Log level filtering for console
    - Colored output support
    - Progress indication
    """
    
    @staticmethod
    def create_console_handler(level: int = logging.INFO) -> logging.Handler:
        """
        Create a console handler.
        
        Args:
            level: Logging level for console output
            
        Returns:
            Configured console handler
        """
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        return handler
    
    @staticmethod
    def create_error_handler() -> logging.Handler:
        """
        Create a console handler for errors.
        
        Returns:
            Configured error console handler
        """
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.ERROR)
        
        # Create error formatter
        formatter = logging.Formatter(
            'ERROR - %(name)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        return handler
    
    @staticmethod
    def create_progress_handler() -> logging.Handler:
        """
        Create a console handler for progress messages.
        
        Returns:
            Configured progress console handler
        """
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # Create simple formatter for progress
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        return handler
