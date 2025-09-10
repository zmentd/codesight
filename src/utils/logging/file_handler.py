"""File-based logging handler for CodeSight."""

import logging
import logging.handlers
from pathlib import Path


class FileHandler:
    """
    File-based logging handler responsible for:
    - Log file management and rotation
    - Project-specific log files
    - Log file formatting
    - Log file cleanup
    - Log file truncation on execution
    """
    
    @staticmethod
    def truncate_log_file(log_file_path: str) -> bool:
        """
        Truncate (clear) an existing log file.
        
        Args:
            log_file_path: Path to the log file to truncate
            
        Returns:
            True if truncation was successful, False otherwise
        """
        try:
            log_path = Path(log_file_path)
            if log_path.exists():
                # Open in write mode to truncate the file
                with open(log_file_path, 'w', encoding='utf-8'):
                    pass  # Opening in 'w' mode truncates the file
                return True
            return False
        except OSError:
            return False

    @staticmethod
    def create_file_handler(
        log_file_path: str,
        level: int = logging.INFO,
        max_bytes: int = 10485760,  # 10MB
        backup_count: int = 5,
        truncate_on_creation: bool = False
    ) -> logging.Handler:
        """
        Create a rotating file handler.
        
        Args:
            log_file_path: Path to log file
            level: Logging level
            max_bytes: Maximum file size before rotation
            backup_count: Number of backup files to keep
            truncate_on_creation: Whether to truncate the log file before creating handler
            
        Returns:
            Configured file handler
        """
        # Ensure log directory exists
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Truncate log file if requested
        if truncate_on_creation:
            FileHandler.truncate_log_file(log_file_path)
        
        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            filename=log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        # Set level and formatter
        handler.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        return handler
    
    @staticmethod
    def create_project_handler(project_name: str, level: int = logging.INFO) -> logging.Handler:
        """
        Create a project-specific file handler.
        
        Args:
            project_name: Name of the project
            level: Logging level
            
        Returns:
            Configured project file handler
        """
        log_file_path = f"projects/{project_name}/output/{project_name}.log"
        return FileHandler.create_file_handler(log_file_path, level)
    
    @staticmethod
    def create_step_handler(
        project_name: str, 
        step_name: str, 
        level: int = logging.DEBUG
    ) -> logging.Handler:
        """
        Create a step-specific file handler.
        
        Args:
            project_name: Name of the project
            step_name: Name of the step
            level: Logging level
            
        Returns:
            Configured step file handler
        """
        log_file_path = f"projects/{project_name}/output/logs/{step_name}.log"
        return FileHandler.create_file_handler(log_file_path, level, max_bytes=5242880)  # 5MB
    
