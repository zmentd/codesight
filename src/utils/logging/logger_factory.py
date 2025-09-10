"""Logger factory and configuration for CodeSight."""

import logging
import logging.config
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from config import Config
from config.exceptions import ConfigurationError


class LoggerFactory:
    """
    Logger factory responsible for:
    - Logger initialization and configuration
    - Consistent logging format across modules
    - File and console handler management
    - Log level configuration
    """
    
    _initialized: bool = False
    _config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def initialize(cls, config_path: Optional[str] = None) -> None:
        """
        Initialize logging configuration.
        
        Args:
            config_path: Optional path to logging configuration file
        """
        if cls._initialized:
            return
        
        try:
            config_file = Path(config_path) if config_path else None
            if config_file and config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    cls._config = yaml.safe_load(f)
                
                # Update log file paths to use project directory
                if cls._config:
                    cls._update_log_file_paths(cls._config)
                    
                    # Apply logging configuration
                    logging.config.dictConfig(cls._config)
                else:
                    cls._setup_default_logging()
            else:
                # Use default configuration if file not found
                cls._setup_default_logging()
            
            cls._initialized = True
            
        except (OSError, IOError, yaml.YAMLError, ValueError) as e:
            print(f"Failed to initialize logging: {e}")
            cls._setup_default_logging()
            cls._initialized = True
    
    @classmethod
    def _update_log_file_paths(cls, config: Dict[str, Any]) -> None:
        """
        Update log file paths in configuration to use project directory.
        Extracts filename from any specified path and places it in project directory.
        
        Args:
            config: Logging configuration dictionary
        """
        try:
            # Get project directory from Config class attributes
            project_dir = Path(Config.project_name_path) if Config.project_name_path else Path.cwd()
            
            # Check if truncation is enabled in logging config
            truncate_enabled = config.get('truncate_on_execution', False)
            
            # Update handlers that have filenames
            handlers = config.get('handlers', {})
            for handler_name, handler_config in handlers.items():
                if isinstance(handler_config, dict) and 'filename' in handler_config:
                    original_path = handler_config['filename']
                    # Extract just the filename, ignore any path
                    filename = Path(original_path).name
                    # Set new path in project directory
                    handler_config['filename'] = str(project_dir / filename)
                    
                    # Conditionally set truncation mode based on logging config
                    if truncate_enabled:
                        handler_config['mode'] = 'w'  # Truncate on each run
                    else:
                        handler_config['mode'] = 'a'  # Append to existing logs
                    
        except (ConfigurationError, AttributeError):
            # If Config not available, use current working directory
            project_dir = Path.cwd()
            truncate_enabled = config.get('truncate_on_execution', False)
            handlers = config.get('handlers', {})
            for handler_name, handler_config in handlers.items():
                if isinstance(handler_config, dict) and 'filename' in handler_config:
                    original_path = handler_config['filename']
                    filename = Path(original_path).name
                    handler_config['filename'] = str(project_dir / filename)
                    # Set mode based on truncation setting
                    handler_config['mode'] = 'w' if truncate_enabled else 'a'
    
    @classmethod
    def _setup_default_logging(cls) -> None:
        """Setup default logging configuration using project directory."""
        try:
            # Get project directory from Config class attributes
            project_dir = Path(Config.project_name_path) if Config.project_name_path else Path.cwd()
            log_mode = 'a'  # Default to append
                
        except (ConfigurationError, AttributeError):
            # Fallback to current working directory
            project_dir = Path.cwd()
            log_mode = 'a'  # Default to append when config not available
        
        log_file = project_dir / 'codesight.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file, mode=log_mode, encoding='utf-8')
            ]
        )
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance.
        
        Args:
            name: Logger name (typically __name__ of calling module)
            
        Returns:
            Configured logger instance
        """
        if not cls._initialized:
            cls._setup_default_logging()
            cls._initialized = True
        
        return logging.getLogger(name)
